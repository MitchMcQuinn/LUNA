"""
Core workflow execution engine for Neo4j-based graph workflows.
"""

import json
from .session_manager import get_session_manager
from .utility_registry import get_utility_registry
from .variable_resolver import resolve_inputs
import logging
import re
import time
import threading

# Global lock for ensuring sequential execution across all sessions
sequential_execution_lock = threading.RLock()

class GraphWorkflowEngine:
    def __init__(self, session_manager=None, utility_registry=None):
        self.session_manager = session_manager or get_session_manager()
        self.utility_registry = utility_registry or get_utility_registry()
        self._recursion_depth = 0
        self._max_recursion = 5
        
        # Import variable resolver
        from .variable_resolver import resolve_variable, resolve_inputs
        self.variable_resolver = type('VariableResolver', (), {
            'resolve_variable': resolve_variable,
            'resolve_variables': resolve_inputs
        })
        
    def _parse_condition_string(self, condition_string):
        """
        Parse a condition string that might be a JSON array.
        
        Args:
            condition_string: String that might be a JSON array of conditions
            
        Returns:
            List of conditions (either strings or dicts)
        """
        logger = logging.getLogger(__name__)
        
        if not isinstance(condition_string, str):
            return condition_string if isinstance(condition_string, list) else [condition_string]
            
        try:
            # Check if it looks like a JSON array
            if condition_string.strip().startswith('[') and condition_string.strip().endswith(']'):
                parsed_condition = json.loads(condition_string)
                if isinstance(parsed_condition, list):
                    logger.info(f"Successfully parsed JSON condition: {parsed_condition}")
                    return parsed_condition
                else:
                    logger.warning(f"Parsed JSON condition is not a list: {parsed_condition}")
                    return [condition_string]  # Treat as a single string condition
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse condition as JSON: {e}")
        
        # If it's not valid JSON or doesn't look like a JSON array, 
        # treat the whole string as a single condition
        return [condition_string]
    
    def process_workflow(self, session_id):
        """Process workflow steps until completion or waiting for input"""
        logger = logging.getLogger(__name__)
        
        # Use the sequential execution lock to prevent race conditions
        with sequential_execution_lock:
            logger.info(f"Acquired sequential lock for processing workflow: {session_id}")
            
            MAX_ITERATIONS = 20  # Safety limit
            iterations = 0
            
            while iterations < MAX_ITERATIONS:
                iterations += 1
                logger.info(f"Processing workflow iteration {iterations} for session {session_id}")
                
                # Get current session state
                state = self.session_manager.get_session_state(session_id)
                if not state:
                    logger.error(f"Session {session_id} not found")
                    return "error"
                
                # Find all active steps
                active_steps = []
                for step_id, info in state["workflow"].items():
                    if info["status"] == "active":
                        active_steps.append(step_id)
                
                logger.info(f"Found {len(active_steps)} active steps: {active_steps}")
                
                # If no active steps, check if we need to activate the root step
                if not active_steps:
                    # Update execution paths to see if any completed steps should activate new ones
                    # This is crucial for continuing the workflow after user input
                    self._update_execution_paths(session_id)
                    
                    # Check again for active steps after updating paths
                    updated_state = self.session_manager.get_session_state(session_id)
                    has_active_steps = False
                    for step_id, info in updated_state["workflow"].items():
                        if info["status"] == "active":
                            has_active_steps = True
                            break
                    
                    # If still no active steps after path evaluation, we need to decide if the conversation should end
                    if not has_active_steps:
                        # Check if any reply function step is complete
                        reply_is_complete = False
                        
                        # Get functions for completed steps
                        completed_steps = [step_id for step_id, info in updated_state["workflow"].items() 
                                         if info["status"] == "complete"]
                        
                        if completed_steps:
                            with self.session_manager.driver.get_session() as session:
                                for step_id in completed_steps:
                                    result = session.run(
                                        """
                                        MATCH (s:STEP {id: $id})
                                        RETURN s.utility as utility, s.function as function
                                        """,
                                        id=step_id
                                    )
                                    record = result.single()
                                    if record:
                                        # Use function if available, otherwise utility for compatibility
                                        function_value = record["function"]
                                        if function_value is None:
                                            function_value = record["utility"]
                                        if function_value and "reply" in function_value.lower():
                                            reply_is_complete = True
                                            break
                        
                        # If reply is complete, the conversation has likely ended naturally
                        if reply_is_complete:
                            logger.info(f"Workflow for session {session_id} is complete (reply function step is complete and no active steps)")
                            return "complete"
                            
                        # If reply isn't complete, we might need to activate root
                        elif "root" in updated_state["workflow"] and updated_state["workflow"]["root"]["status"] != "complete":
                            # Activate the root step if it's in error or inactive
                            if updated_state["workflow"]["root"]["status"] in ["error", "pending"]:
                                logger.info("Activating root step")
                                def activate_root(current_state):
                                    current_state["workflow"]["root"]["status"] = "active"
                                    return current_state
                                
                                self.session_manager.update_session_state(session_id, activate_root)
                                continue  # Continue to next iteration to process the root step
                        
                        # If no active steps and no good reason to continue, the workflow is complete
                        logger.info(f"Workflow for session {session_id} is complete (no active steps after path evaluation)")
                        return "complete"
                    else:
                        logger.info(f"Found new active steps after path evaluation, continuing workflow")
                        continue  # Continue to next iteration with the newly activated steps
                
                # Process each active step
                all_steps_pending = True
                status = "active"
                
                for step_id in active_steps:
                    logger.info(f"Processing step {step_id}")
                    
                    # Process the step
                    step_status = self._process_step(session_id, step_id)
                    logger.info(f"Step {step_id} processed with status: {step_status}")
                    
                    # Update overall status
                    if step_status == "error":
                        logger.error(f"Error processing step {step_id}")
                        status = "error"
                    elif step_status == "awaiting_input":
                        status = "awaiting_input"
                        logger.info(f"Step {step_id} is awaiting input")
                        break  # No need to process further steps when waiting for input
                    elif step_status == "complete":
                        all_steps_pending = False
                
                # If all steps are pending, we need to wait for dependencies
                if status == "active" and all_steps_pending and active_steps:
                    logger.info("All active steps are pending dependencies, pausing workflow")
                    return "pending"
                
                # If a step is awaiting input, pause the workflow
                if status == "awaiting_input":
                    logger.info("Workflow is awaiting input")
                    # Add a brief delay to ensure UI can sync properly before polling again
                    time.sleep(0.5)
                    return "awaiting_input"
                
                # Update execution paths based on completed steps
                # This must happen before we check for more active steps to avoid missing state changes
                self._update_execution_paths(session_id)
                
                # Check if any steps are now active
                updated_state = self.session_manager.get_session_state(session_id)
                still_active = False
                for step_id, info in updated_state["workflow"].items():
                    if info["status"] == "active":
                        still_active = True
                        break
                
                # If no more active steps, continue to next iteration which will check for completion
                if not still_active:
                    logger.info("No more active steps after processing, checking if workflow is complete")
                    # Add a brief delay to ensure UI can sync properly before polling again
                    time.sleep(0.5)
                    
                    # If no active steps and we've found a completed request step, return awaiting_input
                    # to prevent the UI from showing "complete" when we're still expecting input
                    for step_id, info in updated_state["workflow"].items():
                        if info["status"] == "awaiting_input":
                            logger.info(f"Found awaiting_input step {step_id}, returning awaiting_input status")
                            return "awaiting_input"
                
                # Log detailed state for debugging
                logger.info(f"Current workflow step statuses: {[(s, updated_state['workflow'][s]['status']) for s in updated_state['workflow']]}")
                
                # Log step outputs
                if "data" in updated_state and "outputs" in updated_state["data"]:
                    for step_id, outputs in updated_state["data"]["outputs"].items():
                        logger.info(f"Step {step_id} outputs: {json.dumps(outputs, default=str)[:500]}")
            
            # If we've reached the maximum number of iterations, something might be wrong
            logger.warning(f"Reached maximum iterations ({MAX_ITERATIONS}) for session {session_id}")
            return "active"

    def _get_active_steps(self, state):
        """Find steps with 'active' status in workflow state"""
        active_steps = []
        for step_id, step_info in state["workflow"].items():
            if step_info["status"] == "active":
                active_steps.append(step_id)
        return active_steps
    
    def _process_step(self, session_id, step_id):
        """Process a single workflow step"""
        logger = logging.getLogger(__name__)
        
        # Get current time for execution timestamp
        current_time = int(time.time())
        
        # Get step details from Neo4j
        step_details = self._get_step_details(step_id)
        if not step_details:
            # Handle missing step
            logger.error(f"Step {step_id} not found in Neo4j")
            self._mark_step_error(session_id, step_id, "Step not found")
            return "error"
        
        # Get function name (might be in 'function' or 'utility' key)
        function_name = step_details.get("function")
        if not function_name:
            # Step with no function is valid, treat as successful execution
            logger.info(f"Step {step_id} has no function defined, marking as complete")
            
            def mark_complete_empty(state):
                if step_id not in state["workflow"]:
                    state["workflow"][step_id] = {}
                state["workflow"][step_id]["status"] = "complete"
                state["workflow"][step_id]["error"] = ""
                state["workflow"][step_id]["last_executed"] = current_time
                return state
            
            self.session_manager.update_session_state(session_id, mark_complete_empty)
            return "complete"
        
        # Get current session state
        state = self.session_manager.get_session_state(session_id)
        if not state:
            logger.error(f"Session {session_id} not found")
            return "error"
        
        # Handle request step (user input) differently
        if function_name.startswith('utils.request.'):
            logger.info(f"Step {step_id} is a request step, marking as awaiting input")
            
            # Get input data
            input_data = step_details.get("input", {})
            
            # Resolve any variables in the input
            from .variable_resolver import resolve_inputs
            input_data = resolve_inputs(input_data, state) or {}
            
            # Check previous user responses to help debug path issues
            if "data" in state and "outputs" in state["data"]:
                # Look for request steps with responses
                for prev_step_id, outputs in state["data"]["outputs"].items():
                    if "request" in prev_step_id:
                        if isinstance(outputs, list) and outputs:
                            last_output = outputs[-1]
                            if isinstance(last_output, dict) and "response" in last_output:
                                logger.info(f"DEBUG: Found previous request response in {prev_step_id}: {last_output.get('response')}")
                                
                                # Check if this is a negative response
                                if isinstance(last_output.get("response"), str) and last_output.get("response").lower().strip() in ["no", "nope", "no way", "no thanks", "not interested"]:
                                    logger.info(f"DEBUG: Previous response was NEGATIVE - this might affect path conditions")
            
            # Store the resolved input as step output
            def set_awaiting_input(current_state):
                # Initialize data structure if needed
                if "data" not in current_state:
                    current_state["data"] = {}
                if "outputs" not in current_state["data"]:
                    current_state["data"]["outputs"] = {}
                
                # Initialize step outputs as array if needed
                if step_id not in current_state["data"]["outputs"]:
                    current_state["data"]["outputs"][step_id] = []
                elif not isinstance(current_state["data"]["outputs"][step_id], list):
                    # Convert existing output to array for backward compatibility
                    current_state["data"]["outputs"][step_id] = [current_state["data"]["outputs"][step_id]]
                
                # Add new output to the array, limiting to 5 items
                current_state["data"]["outputs"][step_id].append(input_data)
                if len(current_state["data"]["outputs"][step_id]) > 5:
                    current_state["data"]["outputs"][step_id] = current_state["data"]["outputs"][step_id][-5:]
                
                # Set status to awaiting_input
                if step_id not in current_state["workflow"]:
                    current_state["workflow"][step_id] = {}
                current_state["workflow"][step_id]["status"] = "awaiting_input"
                current_state["workflow"][step_id]["error"] = ""
                
                logger.info(f"Set step {step_id} to awaiting_input with input: {input_data}")
                return current_state
            
            self.session_manager.update_session_state(session_id, set_awaiting_input)
            return "awaiting_input"
        
        # For all other steps, resolve inputs and execute the function
        try:
            # Get the input parameters
            input_data = step_details.get("input", {})
            
            # Ensure input_data is a dictionary
            if not isinstance(input_data, dict):
                logger.error(f"Input for step {step_id} is not a dict: {type(input_data)}. Setting to empty dict.")
                input_data = {}
            
            # Resolve variables in the input
            from .variable_resolver import resolve_inputs
            resolved_inputs = resolve_inputs(input_data, state)
            
            if resolved_inputs is None:
                logger.warning(f"Unable to resolve required inputs for step {step_id}, marking as pending")
                
                # Mark step as pending until inputs are available
                def mark_pending(current_state):
                    if step_id not in current_state["workflow"]:
                        current_state["workflow"][step_id] = {}
                    current_state["workflow"][step_id]["status"] = "pending"
                    current_state["workflow"][step_id]["error"] = ""
                    return current_state
                
                self.session_manager.update_session_state(session_id, mark_pending)
                return "pending"
            
            # Check if this step needs conversation history
            if resolved_inputs.get('include_history', False):
                logger.info(f"Adding conversation history for step {step_id}")
                
                # Add message history from session state if it exists
                if "data" in state and "messages" in state["data"]:
                    history = state["data"]["messages"]
                    # Add conversation history directly to resolved inputs
                    resolved_inputs['history'] = history
                    logger.info(f"Added {len(history)} messages from session history")
                else:
                    logger.warning(f"No messages found in session state for history")
                    resolved_inputs['history'] = []
            
            # Get utility function
            utility_func = self.utility_registry.get_utility(function_name)
            if not utility_func:
                error_msg = f"Function not found: {function_name}"
                logger.error(error_msg)
                self._mark_step_error(session_id, step_id, error_msg)
                return "error"
            
            # Execute the utility function
            logger.info(f"Executing function {function_name} for step {step_id}")
            result = utility_func(**resolved_inputs)
            logger.info(f"Function {function_name} execution completed")
            
            # Store result in session state
            def update_with_result(current_state):
                # Initialize data structure if needed
                if "data" not in current_state:
                    current_state["data"] = {}
                if "outputs" not in current_state["data"]:
                    current_state["data"]["outputs"] = {}
                
                # Initialize step outputs as array if needed
                if step_id not in current_state["data"]["outputs"]:
                    current_state["data"]["outputs"][step_id] = []
                elif not isinstance(current_state["data"]["outputs"][step_id], list):
                    # Convert existing output to array for backward compatibility
                    current_state["data"]["outputs"][step_id] = [current_state["data"]["outputs"][step_id]]
                
                # Add new output to the array, limiting to 5 items
                current_state["data"]["outputs"][step_id].append(result)
                if len(current_state["data"]["outputs"][step_id]) > 5:
                    current_state["data"]["outputs"][step_id] = current_state["data"]["outputs"][step_id][-5:]
                
                # Mark step as complete
                if step_id not in current_state["workflow"]:
                    current_state["workflow"][step_id] = {}
                current_state["workflow"][step_id]["status"] = "complete"
                current_state["workflow"][step_id]["error"] = ""
                current_state["workflow"][step_id]["last_executed"] = current_time
                
                logger.info(f"DEBUG: Completed step {step_id} with function {function_name} and result: {json.dumps(result, default=str)[:500]}")
                return current_state
            
            self.session_manager.update_session_state(session_id, update_with_result)
            return "complete"
            
        except Exception as e:
            # Handle execution errors
            error_msg = f"Error executing step {step_id}: {str(e)}"
            logger.exception(error_msg)
            self._mark_step_error(session_id, step_id, error_msg)
            return "error"
    
    def _get_step_details(self, step_id):
        """Get step details from Neo4j"""
        logger = logging.getLogger(__name__)
        with self.session_manager.driver.get_session() as session:
            # Try with both utility and function property names to handle different schema versions
            result = session.run(
                """
                MATCH (s:STEP {id: $id})
                RETURN s.utility as utility, s.function as function, s.input as input
                """,
                id=step_id
            )
            record = result.single()
            if record:
                # Check which property is available - prefer function over utility for consistency
                function_value = record["function"]
                if function_value is None:
                    function_value = record["utility"]
                
                input_data = record["input"]
                
                # Try to parse input as JSON if it's a string
                if isinstance(input_data, str):
                    try:
                        input_data = json.loads(input_data)
                        logger.debug(f"Successfully parsed input JSON for step {step_id}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse input as JSON for step {step_id}: {e}")
                        logger.error(f"Invalid JSON: {input_data}")
                        # Return empty dict instead of invalid string to prevent errors
                        input_data = {}
                elif input_data is None:
                    # Ensure we return an empty dict for None
                    input_data = {}
                elif not isinstance(input_data, dict):
                    # Ensure non-dict values are converted to empty dict
                    logger.warning(f"Input for step {step_id} is not a string or dict: {type(input_data)}")
                    input_data = {}
                
                return {
                    "function": function_value,  # Use function as the key consistently
                    "input": input_data
                }
            return None
    
    def _update_execution_paths(self, session_id):
        """Update workflow execution paths based on completed steps"""
        logger = logging.getLogger(__name__)
        
        # Get current time for timestamp update
        current_time = int(time.time())
        
        # Create a local reference to the session state for consistent evaluation
        # This ensures all condition evaluations use the same snapshot
        state = self.session_manager.get_session_state(session_id)
        if not state:
            logger.error(f"Session {session_id} not found")
            return
        
        # Get last evaluation timestamp, default to 0 if not set
        last_evaluated = state.get("last_evaluated", 0)
        logger.info(f"Last path evaluation timestamp: {last_evaluated}")
        
        # Find steps that were completed since the last evaluation
        recently_completed_steps = []
        # Track all new activations to apply in a single atomic update
        steps_to_activate = []
        
        for step_id, info in state["workflow"].items():
            if info["status"] == "complete":
                # Check if step has a last_executed timestamp and was completed after last_evaluated
                step_executed = info.get("last_executed", 0)
                if step_executed > last_evaluated:
                    recently_completed_steps.append(step_id)
                    logger.info(f"Found recently completed step: {step_id} (executed at {step_executed})")
        
        # If no recently completed steps, try using all completed steps, but more cautiously
        if not recently_completed_steps:
            logger.info("No recently completed steps, checking all completed steps as fallback")
            
            # Get all completed steps
            all_completed_steps = [step_id for step_id, info in state["workflow"].items() 
                                  if info["status"] == "complete"]
            logger.info(f"Found {len(all_completed_steps)} completed steps as fallback")
            
            # Check for any active steps before assuming conversation should end
            active_steps = [step_id for step_id, info in state["workflow"].items() 
                           if info["status"] in ["active", "awaiting_input"]]
            
            # Only if we have no active steps AND we have at least one completed step, we might consider ending
            if not active_steps and all_completed_steps:
                logger.info("No active steps found, checking if this is a natural end or needs continuation")
                
                # Get the most recently completed step
                latest_step = None
                latest_time = 0
                
                for step_id, info in state["workflow"].items():
                    if info["status"] == "complete" and info.get("last_executed", 0) > latest_time:
                        latest_time = info.get("last_executed", 0)
                        latest_step = step_id
                
                if latest_step:
                    logger.info(f"Most recently completed step: {latest_step}")
                    recently_completed_steps = [latest_step]
                else:
                    # If we can't determine a latest step, use the default logic
                    logger.info("Using all completed steps to evaluate paths")
                    recently_completed_steps = all_completed_steps
            else:
                # Either we have active steps or no completed steps - use all completed
                recently_completed_steps = all_completed_steps
        
        # If still no steps to process, return
        if not recently_completed_steps:
            logger.info("No completed steps to evaluate paths for")
            return
        
        logger.info(f"DEBUG: Found {len(recently_completed_steps)} completed steps to evaluate: {recently_completed_steps}")
        
        # Check for special information in the current state
        # Look for specific values that might affect path decisions
        logger.info("===== DEBUG: CRITICAL PATH VALUES =====")
        try:
            # Look for request steps with responses - especially "no" responses
            request_responses = []
            for step_id, outputs in state.get("data", {}).get("outputs", {}).items():
                if "request" in step_id:
                    if isinstance(outputs, list) and outputs:
                        last_output = outputs[-1]
                        if isinstance(last_output, dict) and "response" in last_output:
                            request_responses.append((step_id, last_output.get("response")))
            if request_responses:
                logger.info(f"Found request responses: {request_responses}")
            
            # Look for merits_followup values
            generate_steps = []
            for step_id, outputs in state.get("data", {}).get("outputs", {}).items():
                if "generate" in step_id:
                    if isinstance(outputs, list) and outputs:
                        last_output = outputs[-1]
                        if isinstance(last_output, dict) and "merits_followup" in last_output:
                            generate_steps.append((step_id, last_output.get("merits_followup")))
            if generate_steps:
                logger.info(f"Found generate steps with merits_followup values: {generate_steps}")
                
            # Check for path conflicts
            # If we have a "no" in request but merits_followup is true, that could explain issues
            has_no_response = any(resp and isinstance(resp, str) and resp.lower().strip() in ["no", "nope", "no way"] 
                                for _, resp in request_responses)
            has_true_followup = any(followup for _, followup in generate_steps)
            
            if has_no_response and has_true_followup:
                logger.warning("CONFLICT DETECTED: 'No' response from user but merits_followup is True")
                logger.warning("This may explain why mutually exclusive paths are not being followed correctly")
                
        except Exception as e:
            logger.error(f"Error checking for critical path values: {e}")
        logger.info("=======================================")
        
        # Find all outgoing paths from recently completed steps
        with self.session_manager.driver.get_session() as session:
            for step_id in recently_completed_steps:
                # Check relevant step outputs for debugging
                if step_id in state.get("data", {}).get("outputs", {}):
                    step_outputs = state["data"]["outputs"][step_id]
                    if isinstance(step_outputs, list) and step_outputs:
                        latest_output = step_outputs[-1]
                        logger.info(f"DEBUG: Latest output from step {step_id}: {json.dumps(latest_output, default=str)[:200]}")
                        # Look for key fields that might be used in conditions
                        if isinstance(latest_output, dict):
                            for key in ['merits_followup', 'response', 'is_movie_question']:
                                if key in latest_output:
                                    logger.info(f"DEBUG: Key field in {step_id}: {key}={latest_output[key]}")
                
                # Use a simpler query that doesn't rely on optional properties
                try:
                    # Query outgoing paths with more resilient approach
                    result = session.run(
                        """
                        MATCH (s:STEP {id: $step_id})-[r:NEXT]->(target:STEP)
                        RETURN target.id as target_id,
                               r.condition as condition,
                               r.operator as operator
                        """,
                        step_id=step_id
                    )
                    
                    # Process each outgoing path
                    for record in result:
                        target_id = record["target_id"]
                        condition = record.get("condition") or []
                        operator = record.get("operator") or "AND"
                        
                        logger.info(f"Found path from {step_id} to {target_id}")
                        logger.info(f"DEBUG: Path condition: {condition}")
                        
                        # Skip if target step is already active or awaiting input
                        # BUT allow reactivation of completed steps for loop support
                        if (target_id in state["workflow"] and 
                            state["workflow"][target_id]["status"] in ["active", "awaiting_input"]):
                            logger.info(f"Target step {target_id} is already {state['workflow'][target_id]['status']}, skipping")
                            continue
                        
                        # Check if target step is in error state
                        if (target_id in state["workflow"] and 
                            state["workflow"][target_id]["status"] == "error"):
                            logger.warning(f"Target step {target_id} is in error state, skipping activation")
                            continue
                        
                        # Evaluate condition (if any)
                        should_activate = True
                        if condition:
                            condition_results = []
                            
                            # Parse condition using the helper method
                            condition = self._parse_condition_string(condition)
                            logger.info(f"DEBUG: Parsed condition: {condition}")
                            
                            # Evaluate each condition
                            for cond in condition:
                                # Handle string condition (backward compatibility)
                                if isinstance(cond, str):
                                    try:
                                        # Check if condition has a default value
                                        if '@{SESSION_ID}' in cond and '|' not in cond:
                                            # Add a default value of 'false' to prevent failures
                                            logger.debug(f"Adding default value to condition: {cond}")
                                            cond = f"{cond}|false"
                                        
                                        result = self.variable_resolver.resolve_variable(cond, state)
                                        condition_result = bool(result)
                                        condition_results.append(condition_result)
                                        logger.info(f"Evaluated string condition '{cond}' to {condition_result}, raw value: {result}")
                                    except Exception as e:
                                        logger.error(f"Error evaluating string condition '{cond}': {e}")
                                        condition_results.append(False)
                                
                                # Handle JSON object conditions
                                elif isinstance(cond, dict):
                                    try:
                                        condition_operation_result = None
                                        condition_operator = cond.get("operator", "AND")
                                        
                                        # Process "true" references (variables that should be true)
                                        if "true" in cond:
                                            true_var = cond["true"]
                                            # Add default value if missing
                                            if '@{SESSION_ID}' in true_var and '|' not in true_var:
                                                # Add a default value of 'false' to prevent failures
                                                logger.debug(f"Adding default value to 'true' condition: {true_var}")
                                                true_var = f"{true_var}|false"
                                            
                                            true_result = self.variable_resolver.resolve_variable(true_var, state)
                                            true_condition = bool(true_result)
                                            logger.info(f"Evaluated 'true' condition '{true_var}' to {true_condition}, raw value: {true_result}")
                                            
                                            if condition_operation_result is None:
                                                condition_operation_result = true_condition
                                            elif condition_operator == "AND":
                                                condition_operation_result = condition_operation_result and true_condition
                                            elif condition_operator == "OR":
                                                condition_operation_result = condition_operation_result or true_condition
                                        
                                        # Process "false" references (variables that should be false)
                                        if "false" in cond:
                                            false_var = cond["false"]
                                            # Add default value if missing
                                            if '@{SESSION_ID}' in false_var and '|' not in false_var:
                                                # Add a default value of 'true' to prevent failures
                                                logger.debug(f"Adding default value to 'false' condition: {false_var}")
                                                false_var = f"{false_var}|true"
                                            
                                            false_result = self.variable_resolver.resolve_variable(false_var, state)
                                            false_condition = not bool(false_result)
                                            logger.info(f"Evaluated 'false' condition '{false_var}' to {false_condition}, raw value: {false_result}")
                                            
                                            if condition_operation_result is None:
                                                condition_operation_result = false_condition
                                            elif condition_operator == "AND":
                                                condition_operation_result = condition_operation_result and false_condition
                                            elif condition_operator == "OR":
                                                condition_operation_result = condition_operation_result or false_condition
                                        
                                        if condition_operation_result is not None:
                                            condition_results.append(condition_operation_result)
                                            logger.info(f"Evaluated JSON condition to {condition_operation_result} with operator {condition_operator}")
                                        else:
                                            logger.warning(f"JSON condition had no 'true' or 'false' keys: {cond}")
                                            condition_results.append(False)
                                    except Exception as e:
                                        logger.error(f"Error evaluating JSON condition: {e}")
                                        condition_results.append(False)
                                else:
                                    logger.warning(f"Invalid condition type: {type(cond)}")
                                    condition_results.append(False)
                            
                            # Apply operator logic
                            if operator.upper() == "AND":
                                should_activate = all(condition_results)
                            elif operator.upper() == "OR":
                                should_activate = any(condition_results)
                            else:
                                logger.warning(f"Unknown operator '{operator}', defaulting to AND")
                                should_activate = all(condition_results)
                            
                            logger.info(f"DEBUG: Path activation decision for {step_id} -> {target_id}: condition_results={condition_results}, operator={operator}, should_activate={should_activate}")
                        
                        # If conditions pass, queue this step for activation
                        if should_activate:
                            logger.info(f"Queueing step {target_id} for activation from {step_id}")
                            steps_to_activate.append(target_id)
                except Exception as e:
                    logger.error(f"Error evaluating paths from step {step_id}: {e}")
        
        # Now apply all activations in a single atomic update
        if steps_to_activate:
            def activate_multiple_steps(current_state):
                logger.info(f"DEBUG: Step status before activation {[f'{s}: {current_state['workflow'].get(s, {}).get('status', 'unknown')}' for s in steps_to_activate]}")
                
                for target_id in steps_to_activate:
                    if target_id not in current_state["workflow"]:
                        current_state["workflow"][target_id] = {}
                    
                    # Only activate if not already active/awaiting_input (additional safety check)
                    if current_state["workflow"][target_id].get("status") not in ["active", "awaiting_input"]:
                        current_state["workflow"][target_id]["status"] = "active"
                        current_state["workflow"][target_id]["error"] = ""
                
                # Update the last_evaluated timestamp
                current_state["last_evaluated"] = current_time
                
                logger.info(f"DEBUG: Step status after activation {[f'{s}: {current_state['workflow'].get(s, {}).get('status', 'unknown')}' for s in steps_to_activate]}")
                return current_state
                
            self.session_manager.update_session_state(session_id, activate_multiple_steps)
            logger.info(f"Activated {len(steps_to_activate)} steps in a single atomic update: {steps_to_activate}")
        else:
            # Just update the timestamp if no steps were activated
            def update_timestamp(current_state):
                current_state["last_evaluated"] = current_time
                return current_state
            
            self.session_manager.update_session_state(session_id, update_timestamp)
            logger.info(f"Updated last_evaluated timestamp to {current_time}")
            
        # Get updated state and check status for critical debugging
        updated_state = self.session_manager.get_session_state(session_id)
        logger.info(f"DEBUG: Final workflow status after path evaluation: {[(s, updated_state['workflow'][s]['status']) for s in updated_state['workflow']]}")
    
    def _get_outgoing_relationships(self, step_id):
        """Get outgoing NEXT relationships from a step"""
        with self.session_manager.driver.get_session() as session:
            try:
                # Only use necessary properties, remove priority
                result = session.run(
                    """
                    MATCH (s:STEP {id: $id})-[r:NEXT]->(target:STEP)
                    RETURN target.id as target_id, 
                           r.condition as condition,
                           r.operator as operator
                    """,
                    id=step_id
                )
            except Exception:
                # Fall back to simpler query if properties are missing
                result = session.run(
                    """
                    MATCH (s:STEP {id: $id})-[r:NEXT]->(target:STEP)
                    RETURN target.id as target_id
                    """,
                    id=step_id
                )
                
            relationships = []
            for record in result:
                # Get the condition and parse if it's a JSON string
                condition = record["condition"] if "condition" in record else []
                condition = self._parse_condition_string(condition)
                
                relationships.append({
                    "target_step": record["target_id"],
                    "condition": condition,
                    "operator": record["operator"] or "AND"
                })
            return relationships
    
    def _update_step_status(self, session_id, step_id, status, timestamp=None):
        """Update a step's status in session state with optional timestamp"""
        if timestamp is None:
            timestamp = int(time.time())
        
        def update_state(current_state):
            if step_id in current_state["workflow"]:
                current_state["workflow"][step_id]["status"] = status
                if status == "complete":
                    current_state["workflow"][step_id]["last_executed"] = timestamp
            else:
                current_state["workflow"][step_id] = {
                    "status": status,
                    "error": "",
                    "last_executed": timestamp if status == "complete" else 0
                }
            return current_state
            
        self.session_manager.update_session_state(session_id, update_state)
    
    def _mark_step_error(self, session_id, step_id, error_message):
        """Mark a step as having an error"""
        def update_state(current_state):
            if step_id in current_state["workflow"]:
                current_state["workflow"][step_id]["status"] = "error"
                current_state["workflow"][step_id]["error"] = error_message
            else:
                current_state["workflow"][step_id] = {
                    "status": "error",
                    "error": error_message
                }
            return current_state
            
        self.session_manager.update_session_state(session_id, update_state)
    
    def handle_user_input(self, session_id, user_input):
        """Handle user input for the workflow"""
        logger = logging.getLogger(__name__)
        
        # Use the sequential execution lock to prevent race conditions
        with sequential_execution_lock:
            logger.info(f"Acquired sequential lock for handling user input: {session_id}")
            
            # Get current time for timestamps
            current_time = int(time.time())
            
            # Get current state
            state = self.session_manager.get_session_state(session_id)
            if not state:
                logger.error(f"Session {session_id} not found")
                return "error"
            
            # Find step awaiting input
            awaiting_step_id = None
            for step_id, info in state["workflow"].items():
                if info["status"] == "awaiting_input":
                    awaiting_step_id = step_id
                    break
            
            if not awaiting_step_id:
                logger.warning(f"No step is awaiting input in session {session_id}")
                return "error"
            
            logger.info(f"Handling user input for step {awaiting_step_id}: {user_input}")
            
            # Store user input and mark step as complete
            def update_with_user_input(current_state):
                # Initialize outputs array if needed
                if "data" not in current_state:
                    current_state["data"] = {}
                if "outputs" not in current_state["data"]:
                    current_state["data"]["outputs"] = {}
                if awaiting_step_id not in current_state["data"]["outputs"]:
                    current_state["data"]["outputs"][awaiting_step_id] = []
                elif not isinstance(current_state["data"]["outputs"][awaiting_step_id], list):
                    # Convert to array for backwards compatibility
                    current_state["data"]["outputs"][awaiting_step_id] = [current_state["data"]["outputs"][awaiting_step_id]]
                
                # Get the most recent output
                output = None
                if current_state["data"]["outputs"][awaiting_step_id]:
                    output = dict(current_state["data"]["outputs"][awaiting_step_id][-1])
                else:
                    output = {}
                
                # Update output with user response
                output["response"] = user_input
                # Set waiting_for_input to False to mark as processed
                output["waiting_for_input"] = False
                
                # Add as new output in array
                current_state["data"]["outputs"][awaiting_step_id].append(output)
                
                # Limit to 5 most recent outputs
                if len(current_state["data"]["outputs"][awaiting_step_id]) > 5:
                    current_state["data"]["outputs"][awaiting_step_id] = current_state["data"]["outputs"][awaiting_step_id][-5:]
                
                # Mark step as complete
                current_state["workflow"][awaiting_step_id]["status"] = "complete"
                current_state["workflow"][awaiting_step_id]["last_executed"] = current_time
                
                logger.info(f"Updated step {awaiting_step_id} with user input and marked as complete")
                return current_state
            
            # Update session state
            self.session_manager.update_session_state(session_id, update_with_user_input)
            
            # Add a brief delay to ensure UI can sync properly before continuing
            time.sleep(0.5)
            
            # Immediately update execution paths to activate downstream steps
            self._update_execution_paths(session_id)
            
            # Return active status to signal that workflow should continue processing
            return "active"

    def _find_next_steps(self, session_id):
        """Find next steps to activate in the workflow based on completed steps"""
        logger = logging.getLogger(__name__)
        
        # Get current state
        state = self.session_manager.get_session_state(session_id)
        if not state:
            return []
            
        # Find completed steps
        completed_steps = []
        for step_id, info in state["workflow"].items():
            if info["status"] == "complete":
                completed_steps.append(step_id)
                
        if not completed_steps:
            return []
            
        # Find next steps from completed ones
        next_steps = []
        for step_id in completed_steps:
            outgoing = self._get_outgoing_relationships(step_id)
            
            for rel in outgoing:
                target_id = rel.get("target_id") or rel.get("target_step")
                if not target_id:
                    continue
                    
                logger.info(f"Evaluating relationship from {step_id} to {target_id}")
                
                # Evaluate condition if present
                conditions_met = True
                if rel.get("condition"):
                    from .variable_resolver import resolve_variable
                    
                    # Extract condition based on what's available
                    condition = rel.get("condition") or []
                    
                    # Parse condition if it's a JSON string
                    if isinstance(condition, str) and (condition.startswith('{') or condition.startswith('[')):
                        try:
                            condition = json.loads(condition)
                        except:
                            logger.warning(f"Failed to parse condition JSON: {condition}")
                            condition = []
                    
                    # Handle different condition formats
                    if isinstance(condition, dict):
                        # Format: {"expected_value": "variable_reference"}
                        results = []
                        for expected_value, variable_ref in condition.items():
                            # Resolve the variable
                            actual_value = resolve_variable(variable_ref, state)
                            logger.info(f"CONDITION CHECK: {actual_value} == {expected_value}?")
                            
                            # Convert to string for comparison
                            if expected_value.lower() in ('true', 'false'):
                                # Boolean comparison
                                expected_bool = expected_value.lower() == 'true'
                                if isinstance(actual_value, bool):
                                    results.append(actual_value == expected_bool)
                                else:
                                    # Try to convert to boolean
                                    actual_bool = str(actual_value).lower() in ('true', 'yes', '1')
                                    results.append(actual_bool == expected_bool)
                            else:
                                # String comparison
                                if not isinstance(actual_value, str):
                                    actual_value = str(actual_value).lower()
                                    
                                expected_value = expected_value.lower()
                                results.append(actual_value == expected_value)
                        
                        # Apply operator logic
                        operator = rel.get("operator") or "AND"
                        if operator == "OR":
                            conditions_met = any(results)
                        else:  # Default to AND
                            conditions_met = all(results)
                    elif isinstance(condition, list):
                        # Format: List of variable references to check for truthy values
                        results = []
                        for variable_ref in condition:
                            value = resolve_variable(variable_ref, state)
                            results.append(bool(value))
                            
                        # Apply operator logic
                        operator = rel.get("operator") or "AND"
                        if operator == "OR":
                            conditions_met = any(results)
                        else:  # Default to AND
                            conditions_met = all(results)
                    else:
                        # Single condition
                        value = resolve_variable(condition, state)
                        conditions_met = bool(value)
                
                logger.info(f"Condition met for {step_id} -> {target_id}: {conditions_met}")
                
                if conditions_met:
                    # Use priority if available
                    priority = rel.get("priority") or 100
                    
                    next_steps.append({
                        "step_id": target_id,
                        "priority": priority,
                        "source_step": step_id
                    })
        
        # Sort next steps by priority
        next_steps.sort(key=lambda x: x["priority"])
        return next_steps
        
    def _activate_step(self, session_id, step_id, source_step, is_loop=False):
        """Activate a step in the workflow"""
        logger = logging.getLogger(__name__)
        
        # Get current state
        state = self.session_manager.get_session_state(session_id)
        if not state:
            return "error"
            
        # Check current status of the step
        current_status = None
        if step_id in state["workflow"]:
            current_status = state["workflow"][step_id]["status"]
            
        # General rule: Don't reactivate a completed step that has already collected user input
        # This is workflow-agnostic - applies to any step with a response field containing user input
        if current_status == "complete" and step_id in state["data"]["outputs"]:
            output = state["data"]["outputs"][step_id]
            if isinstance(output, dict) and output.get("waiting_for_input") is False and "response" in output:
                # This is a completed step that received user input
                # Only allow reactivation through explicit loop transitions
                if source_step == "root":
                    logger.info(f"Skipping reactivation of step with user input: {step_id}")
                    return current_status
            
        # Determine what action to take based on current status
        if current_status is None:
            # Step not in workflow yet - add as active
            logger.info(f"Adding new step to workflow: {step_id}")
            
            def update_state(current_state):
                current_state["workflow"][step_id] = {
                    "status": "active",
                    "error": ""
                }
                return current_state
                
            self.session_manager.update_session_state(session_id, update_state)
            return "active"
            
        elif current_status == "pending":
            # Step is pending - change to active
            logger.info(f"Activating pending step: {step_id}")
            
            def update_state(current_state):
                current_state["workflow"][step_id]["status"] = "active"
                return current_state
                
            self.session_manager.update_session_state(session_id, update_state)
            return "active"
            
        elif is_loop and current_status == "complete":
            # Handle loop activation in a general way
            # Don't allow root to reactivate steps (root is not part of a loop)
            if source_step == "root":
                logger.info(f"Root step should not reactivate completed steps: {step_id}")
                return current_status
                
            # Allow any non-root step to create a loop if explicitly marked as such
            logger.info(f"Reactivating completed step for loop: {step_id} (triggered by {source_step})")
            
            def update_state(current_state):
                current_state["workflow"][step_id]["status"] = "active"
                return current_state
                
            self.session_manager.update_session_state(session_id, update_state)
            return "active"
            
        # Otherwise, keep current status
        return current_status

    def _resolve_variable_reference(self, var_reference, state):
        """
        Resolve a variable reference from the state
        
        Args:
            var_reference: String in format '@{SESSION_ID}.step_id.field'
            state: Current session state
            
        Returns:
            Resolved value or None
        """
        logger = logging.getLogger(__name__)
        
        if not isinstance(var_reference, str) or not var_reference.startswith('@{'):
            return var_reference
        
        try:
            # Extract parts from @{SESSION_ID}.step_id.field
            var_path = var_reference[2:].split('.')
            
            # Remove the SESSION_ID part and any closing brackets
            if len(var_path) > 0:
                var_path[0] = var_path[0].rstrip('}')
            
            if len(var_path) < 2:
                return None
            
            # Get step output from session state
            step_id = var_path[1]
            
            if "data" not in state or "outputs" not in state["data"] or step_id not in state["data"]["outputs"]:
                return None
            
            value = state["data"]["outputs"][step_id]
            
            # Navigate to nested field if specified
            if len(var_path) > 2:
                for field in var_path[2:]:
                    if isinstance(value, dict) and field in value:
                        value = value[field]
                    else:
                        return None
                    
            logger.info(f"Resolved variable {var_reference} to {value}")
            return value
        except Exception as e:
            logger.error(f"Error resolving variable {var_reference}: {e}")
            return None

# Singleton pattern
_engine = None

def get_graph_workflow_engine():
    global _engine
    if _engine is None:
        _engine = GraphWorkflowEngine()
    return _engine 