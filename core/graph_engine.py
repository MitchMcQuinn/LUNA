"""
Core workflow execution engine for Neo4j-based graph workflows.
"""

import json
from .session_manager import get_session_manager
from .utility_registry import get_utility_registry
from .variable_resolver import resolve_inputs
import logging
import re

class GraphWorkflowEngine:
    def __init__(self, session_manager=None, utility_registry=None):
        self.session_manager = session_manager or get_session_manager()
        self.utility_registry = utility_registry or get_utility_registry()
        self._recursion_depth = 0
        self._max_recursion = 5
        
    def process_workflow(self, session_id):
        """Process the workflow for the given session until completion or wait state"""
        try:
            # Set up logging
            logger = logging.getLogger(__name__)
            
            # Get current session state
            manager = self.session_manager
            state = manager.get_session_state(session_id)
            if not state:
                logger.error(f"Cannot process workflow - session {session_id} not found")
                return "error"
                
            # Find all steps that are active or awaiting active status
            pending_steps = []
            for step_id, info in state["workflow"].items():
                if info["status"] == "active" or info["status"] == "pending":
                    pending_steps.append(step_id)
            
            logger.info(f"Starting workflow processing with pending steps: {pending_steps}")
            if not pending_steps:
                logger.warning("No active steps found to process")
                
                # Check if we need to activate the root step
                if "root" in state["workflow"] and state["workflow"]["root"]["status"] != "complete":
                    logger.info("Activating root step")
                    pending_steps.append("root")
                    self._update_step_status(session_id, "root", "active")
                else:
                    logger.warning("Root step not found or already complete")
                    
                    # IMPORTANT: If no active steps are found, check for completed steps with outgoing relationships
                    # This is critical for workflow progression after a step is completed
                    next_steps = self._find_next_steps(session_id)
                    if next_steps:
                        logger.info(f"Found next steps to activate: {[s['step_id'] for s in next_steps]}")
                        for next_step in next_steps:
                            step_id_to_activate = next_step["step_id"]
                            source_step = next_step["source_step"]
                            is_loop = False
                            
                            # Activate the step
                            step_status = self._activate_step(session_id, step_id_to_activate, source_step, is_loop)
                            if step_status == "active" or step_status == "pending":
                                pending_steps.append(step_id_to_activate)
            
            # Process any pending steps
            iterations = 0
            max_iterations = 20  # Safety measure
            while pending_steps and iterations < max_iterations:
                iterations += 1
                logger.info(f"Processing iteration {iterations}, pending steps: {pending_steps}")
                
                # Process the first pending step
                step_id = pending_steps.pop(0)
                status = self._process_step(session_id, step_id)
                
                # If step is awaiting input, break processing
                if status == "awaiting_input":
                    logger.info(f"Step {step_id} is awaiting input, pausing workflow")
                    return "awaiting_input"
                
                # After processing, find if there are any newly active steps
                state = manager.get_session_state(session_id)
                next_steps = self._find_next_steps(session_id)
                
                logger.info(f"Evaluated next steps: {[s['step_id'] for s in next_steps]}")
                
                # Activate the next steps based on priority
                for next_step in next_steps:
                    step_id_to_activate = next_step["step_id"]
                    source_step = next_step["source_step"]
                    
                    # Check if this is a loop activation of a completed step
                    is_loop = False
                    if step_id_to_activate in state["workflow"]:
                        current_status = state["workflow"][step_id_to_activate]["status"]
                        if current_status == "complete":
                            is_loop = True
                    
                    # Process or queue this step
                    step_status = self._activate_step(session_id, step_id_to_activate, source_step, is_loop)
                    
                    # If step was activated but not completed (e.g. pending awaiting input)
                    # add it to pending steps for next iteration
                    if step_status == "active" or step_status == "pending":
                        if step_id_to_activate not in pending_steps:
                            pending_steps.append(step_id_to_activate)
                            
                # Special check for provide-answer step to ensure it runs
                if "provide-answer" in state["workflow"] and state["workflow"]["provide-answer"]["status"] == "pending":
                    logger.info("Found provide-answer in pending status, prioritizing it")
                    if "provide-answer" in pending_steps:
                        # Move to front of queue
                        pending_steps.remove("provide-answer")
                    pending_steps.insert(0, "provide-answer")
                
                # Check if all steps are complete 
                if not pending_steps:
                    state = manager.get_session_state(session_id)
                    for step_id, info in state["workflow"].items():
                        if info["status"] == "active" or info["status"] == "pending":
                            pending_steps.append(step_id)
                
                # Log the current state of all steps            
                state = manager.get_session_state(session_id)
                logger.info(f"Current workflow status: {[(s, state['workflow'][s]['status']) for s in state['workflow']]}")
            
            # If we hit max iterations, log warning
            if iterations >= max_iterations:
                logger.warning(f"Reached maximum iterations ({max_iterations}) for session {session_id}")
                return "active"  # Still processing
                
            # If all steps were processed successfully with no pending steps
            if not pending_steps:
                # Check if any step is awaiting input
                state = manager.get_session_state(session_id)
                for step_id, info in state["workflow"].items():
                    if info["status"] == "awaiting_input":
                        return "awaiting_input"
                
                # One more check for next steps before marking as complete
                next_steps = self._find_next_steps(session_id)
                if next_steps:
                    logger.info(f"Found more steps to activate: {[s['step_id'] for s in next_steps]}")
                    return "active"  # Still have steps to process
                        
                # Otherwise completed
                return "complete"
            
            # Still processing
            return "active"
            
        except Exception as e:
            logger.error(f"Error processing workflow: {e}", exc_info=True)
            return "error"
    
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
        
        # Get step details from Neo4j
        step_details = self._get_step_details(step_id)
        if not step_details:
            # Handle missing step
            self._mark_step_error(session_id, step_id, "Step not found")
            return "error"
        
        # Skip processing if the step has a function but it's empty
        function_name = step_details.get("function")
        if function_name is None:
            logger.info(f"Step {step_id} has no function - treating as successful execution")
            self._update_step_status(session_id, step_id, "complete")
            return "complete"
        
        # Check if this step's input contains variable references
        # that need to be resolved from session state
        try:
            input_data = step_details.get("input", {})
            if not input_data:
                # Empty input is valid for some steps
                input_data = {}
            
            # Resolve the variables in the input
            from .variable_resolver import resolve_inputs
            resolved_inputs = resolve_inputs(input_data, self.session_manager.get_session_state(session_id)) or {}
            
            # Log the resolved inputs for debugging
            if resolved_inputs:
                logger.info(f"Resolved inputs for {step_id}: {resolved_inputs}")
            else:
                logger.warning(f"No inputs were resolved for step {step_id}")
                
                # Check if any required inputs are missing
                missing_refs = []
                for key, value in input_data.items():
                    if isinstance(value, str) and "@{SESSION_ID}." in value:
                        # This is a variable reference - check if it resolves
                        parts = value.split("@{SESSION_ID}.", 1)[1].split(".", 1)
                        if len(parts) > 0:
                            ref_step = parts[0].split("}")[0]
                            # Check if referenced step exists and has output
                            if ref_step not in self.session_manager.get_session_state(session_id).get("data", {}).get("outputs", {}):
                                missing_refs.append(ref_step)
                            elif not self.session_manager.get_session_state(session_id)["data"]["outputs"][ref_step]:
                                missing_refs.append(f"{ref_step} (empty output)")
                
                if missing_refs:
                    logger.warning(f"Step {step_id} depends on missing outputs: {missing_refs}")
                    # Mark as pending and wait for dependencies
                    self._update_step_status(session_id, step_id, "pending")
                    return "pending"
        except Exception as e:
            logger.error(f"Error resolving inputs for step {step_id}: {e}")
            self._mark_step_error(session_id, step_id, f"Error resolving inputs: {str(e)}")
            return "error"
        
        # Get function reference
        function_func = self.utility_registry.get_utility(function_name)
        
        if not function_func:
            # Handle missing function
            logger.error(f"Function not found: {function_name}")
            self._mark_step_error(session_id, step_id, f"Function not found: {function_name}")
            return "error"
        
        # Special handling for request function
        if function_name == "utils.request.request":
            logger.info(f"Step {step_id} is a request function, marking as awaiting input")
            self._update_step_status(session_id, step_id, "awaiting_input")
            return "awaiting_input"
        
        # Execute function
        try:
            # More detailed logging for generate step to help diagnose issues
            if function_name == "utils.generate.generate":
                logger.info(f"Executing generate function with inputs: {json.dumps(resolved_inputs, default=str)}")
                
                # Check OPENAI_API_KEY is set
                import os
                api_key = os.environ.get("OPENAI_API_KEY")
                if api_key:
                    masked_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:]
                    logger.info(f"OPENAI_API_KEY is set: {masked_key}")
                else:
                    logger.error("OPENAI_API_KEY is not set in environment - generate will likely fail")
            
            logger.info(f"Executing function: {function_name}")
            result = function_func(**resolved_inputs)
            logger.info(f"Result from {function_name}: {result}")
            
            # Check for error in result
            if isinstance(result, dict) and "error" in result:
                error_message = result.get("error", "Unknown error")
                logger.error(f"Function returned error: {error_message}")
                self._mark_step_error(session_id, step_id, error_message)
                return "error"
            
            # Store result in session
            def update_state(current_state):
                # Also store the input variables for debugging
                if isinstance(result, dict) and function_name == "utils.generate.generate":
                    result["_input_vars"] = resolved_inputs
                    
                current_state["data"]["outputs"][step_id] = result
                current_state["workflow"][step_id]["status"] = "complete"
                return current_state
            
            self.session_manager.update_session_state(session_id, update_state)
            return "complete"
            
        except Exception as e:
            # Handle execution error
            logger.error(f"Error executing step {step_id}: {e}", exc_info=True)
            self._mark_step_error(session_id, step_id, str(e))
            return "error"
    
    def _get_step_details(self, step_id):
        """Get step details from Neo4j"""
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
                # Check which property is available - prefer utility over function
                utility = record["utility"]
                if utility is None:
                    utility = record["function"]
                
                input_data = record["input"]
                
                # Try to parse input as JSON if it's a string
                if isinstance(input_data, str):
                    try:
                        import json
                        input_data = json.loads(input_data)
                    except:
                        # If we can't parse as JSON, leave as is
                        pass
                
                return {
                    "function": utility,  # Use key 'function' for consistency
                    "input": input_data
                }
            return None
    
    def _update_execution_paths(self, session_id):
        """Identify and activate next steps in the workflow"""
        logger = logging.getLogger(__name__)
        logger.info(f"Updating execution paths for session {session_id}")
        
        # Get current state
        state = self.session_manager.get_session_state(session_id)
        if not state:
            logger.warning(f"Session {session_id} not found when updating execution paths")
            return
        
        # Initialize lists for tracking
        completed_steps = []
        next_steps = []
        
        # Find completed steps that need to be evaluated
        for step_id, info in state["workflow"].items():
            # Only include steps that are complete and don't have errors
            if info["status"] == "complete" and not info.get("error"):
                completed_steps.append(step_id)
        
        if not completed_steps:
            logger.info("No completed steps found to evaluate for next steps")
            return
        
        logger.info(f"Completed steps to evaluate: {completed_steps}")
        
        # Find next steps from completed ones
        for step_id in completed_steps:
            # Skip any step that has errors
            if step_id in state["workflow"] and state["workflow"][step_id].get("error"):
                logger.warning(f"Skipping step with error: {step_id}")
                continue
            
            outgoing = self._get_outgoing_relationships(step_id)
            logger.info(f"Found {len(outgoing)} outgoing relationships from {step_id}")
            
            for rel in outgoing:
                target_step = rel["target_step"]
                logger.info(f"Evaluating relationship from {step_id} to {target_step}")
                
                # Check if target step exists - don't try to activate non-existent steps
                target_exists = False
                try:
                    step_details = self._get_step_details(target_step)
                    target_exists = step_details is not None
                except Exception:
                    target_exists = False
                
                if not target_exists:
                    logger.warning(f"Target step {target_step} does not exist, skipping")
                    continue
                
                # Check if the target step is already in error state - don't reactivate
                if target_step in state["workflow"] and state["workflow"][target_step].get("status") == "error":
                    logger.warning(f"Target step {target_step} has error status, skipping activation")
                    continue
                
                # Evaluate conditions if present
                conditions_met = True
                conditions = rel.get("conditions", [])
                
                if conditions:
                    # Resolve each condition
                    results = []
                    for condition in conditions:
                        # Handle conditions with equality operators
                        value = None
                        if " == " in condition:
                            var_ref, expected = condition.split(" == ")
                            actual = self._resolve_variable_reference(var_ref, state)
                            
                            # Only consider the condition met if there's an actual value
                            if actual is None:
                                logger.warning(f"Condition variable {var_ref} resolved to None")
                                value = False
                            else:
                                logger.info(f"Comparing {actual} == {expected}")
                                value = str(actual).lower() == expected.lower()
                        else:
                            # Simple boolean evaluation
                            value = self._resolve_variable_reference(condition, state)
                            
                            # If the value resolves to None, treat as false
                            if value is None:
                                logger.warning(f"Boolean condition {condition} resolved to None")
                                value = False
                        
                        # Convert to boolean and add to results
                        results.append(bool(value))
                        
                    # Apply operator logic
                    operator = rel.get("operator", "AND")
                    if operator == "OR":
                        conditions_met = any(results)
                    else:  # Default to AND
                        conditions_met = all(results)
                
                logger.info(f"Conditions met for {step_id} -> {target_step}: {conditions_met}")
                
                if conditions_met:
                    # Add to the list of steps to activate if:
                    # 1. Step isn't already active
                    # 2. Step isn't already complete 
                    # 3. Step doesn't have an error
                    if (target_step not in state["workflow"] or 
                        (state["workflow"][target_step]["status"] != "active" and 
                         state["workflow"][target_step]["status"] != "complete" and
                         state["workflow"][target_step]["status"] != "error")):
                        next_steps.append(target_step)
        
        # Activate all valid next steps
        if next_steps:
            logger.info(f"Found more steps to activate: {next_steps}")
            
            def update_state(current_state):
                for step_id in next_steps:
                    # Don't activate steps in error state
                    if step_id in current_state["workflow"] and current_state["workflow"][step_id].get("status") == "error":
                        continue
                        
                    if step_id not in current_state["workflow"]:
                        current_state["workflow"][step_id] = {
                            "status": "active",
                            "error": ""
                        }
                    else:
                        current_state["workflow"][step_id]["status"] = "active"
                return current_state
            
            self.session_manager.update_session_state(session_id, update_state)
        
        logger.info(f"Evaluated next steps: {next_steps}")
    
    def _get_outgoing_relationships(self, step_id):
        """Get outgoing NEXT relationships from a step"""
        with self.session_manager.driver.get_session() as session:
            try:
                # Only use necessary properties, remove priority
                result = session.run(
                    """
                    MATCH (s:STEP {id: $id})-[r:NEXT]->(target:STEP)
                    RETURN target.id as target_id, 
                           r.conditions as conditions,
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
                relationships.append({
                    "target_step": record["target_id"],
                    "conditions": record["conditions"] if "conditions" in record else [],
                    "operator": record["operator"] or "AND"
                })
            return relationships
    
    def _update_step_status(self, session_id, step_id, status):
        """Update a step's status in session state"""
        def update_state(current_state):
            if step_id in current_state["workflow"]:
                current_state["workflow"][step_id]["status"] = status
            else:
                current_state["workflow"][step_id] = {
                    "status": status,
                    "error": ""
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
        """
        Handle user input for a workflow that's awaiting input
        
        Args:
            session_id: Session ID
            user_input: User's input data
            
        Returns:
            Updated workflow status
        """
        # Initialize logger
        logger = logging.getLogger(__name__)
        logger.info(f"Handling user input for session {session_id}")
        
        # Get current state
        state = self.session_manager.get_session_state(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")
            
        # Find step awaiting input
        awaiting_step = None
        for step_id, info in state["workflow"].items():
            if info["status"] == "awaiting_input":
                awaiting_step = step_id
                break
                
        if not awaiting_step:
            logger.warning(f"No step is awaiting input for session {session_id}")
            return "completed"
            
        logger.info(f"Updating step {awaiting_step} with user input")
        
        # Check if there is existing stored input from a previous step
        # (for example a followup question from generate-answer)
        existing_question = None
        
        if "data" in state and "outputs" in state["data"] and awaiting_step in state["data"]["outputs"]:
            existing_output = state["data"]["outputs"][awaiting_step]
            if isinstance(existing_output, dict) and "query" in existing_output:
                existing_question = existing_output.get("query")
                logger.info(f"Found existing question in {awaiting_step}: {existing_question}")
        
        # Prepare input with response field for compatibility
        input_data = {"response": user_input}
        
        # Store input and mark step as complete
        def update_state(current_state):
            # Store result, but preserve any existing fields like 'query' that contain the actual question
            if awaiting_step in current_state["data"]["outputs"]:
                # Get existing output and update it
                existing = current_state["data"]["outputs"][awaiting_step]
                if isinstance(existing, dict):
                    # Preserve the existing question/query but update the response
                    existing.update(input_data)
                    current_state["data"]["outputs"][awaiting_step] = existing
                else:
                    # Just set the input directly
                    current_state["data"]["outputs"][awaiting_step] = input_data
            else:
                # No existing output, just set the input directly
                current_state["data"]["outputs"][awaiting_step] = input_data
            
            # Mark step as complete
            current_state["workflow"][awaiting_step]["status"] = "complete"
            
            # Add to message history
            if "messages" not in current_state["data"]:
                current_state["data"]["messages"] = []
            
            current_state["data"]["messages"].append({
                "role": "user",
                "content": user_input
            })
            
            return current_state
        
        self.session_manager.update_session_state(session_id, update_state)
        logger.info(f"User input stored for {awaiting_step}")
        
        # IMPORTANT: Explicitly check for and activate next steps
        # This ensures the workflow properly continues after user input
        next_steps = self._find_next_steps(session_id)
        if next_steps:
            logger.info(f"Found steps to activate after user input: {[s['step_id'] for s in next_steps]}")
            
            # Activate each next step
            for next_step in next_steps:
                step_id_to_activate = next_step["step_id"]
                source_step = next_step["source_step"]
                
                logger.info(f"Activating next step after user input: {step_id_to_activate}")
                self._activate_step(session_id, step_id_to_activate, source_step, False)
        else:
            logger.warning(f"No next steps found after handling user input for {awaiting_step}")
        
        # Resume workflow processing with active status to trigger step evaluation
        logger.info(f"Resuming workflow processing for session {session_id}")
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
                
                # Evaluate conditions if present
                conditions_met = True
                if rel.get("conditions") or rel.get("condition"):
                    from .variable_resolver import resolve_variable
                    
                    # Extract conditions based on what's available
                    conditions = rel.get("conditions") or rel.get("condition") or []
                    
                    # Parse conditions if it's a JSON string
                    if isinstance(conditions, str) and (conditions.startswith('{') or conditions.startswith('[')):
                        try:
                            conditions = json.loads(conditions)
                        except:
                            logger.warning(f"Failed to parse conditions JSON: {conditions}")
                            conditions = []
                    
                    # Handle different condition formats
                    if isinstance(conditions, dict):
                        # Format: {"expected_value": "variable_reference"}
                        results = []
                        for expected_value, variable_ref in conditions.items():
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
                    elif isinstance(conditions, list):
                        # Format: List of variable references to check for truthy values
                        results = []
                        for variable_ref in conditions:
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
                        value = resolve_variable(conditions, state)
                        conditions_met = bool(value)
                
                logger.info(f"Conditions met for {step_id} -> {target_id}: {conditions_met}")
                
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