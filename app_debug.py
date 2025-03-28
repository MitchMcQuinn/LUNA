"""
Simple app to run one workflow cycle and debug issues
"""

import os
import json
import logging
import sys
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set up path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

# Load environment variables
env_path = os.path.join(script_dir, '.env.local')
print(f"Loading environment from: {env_path}")
load_dotenv(env_path)

from core.session_manager import get_session_manager
from core.graph_engine import get_graph_workflow_engine

def run_debug_workflow():
    """Run one workflow cycle with debug information"""
    # Create a new session
    session_manager = get_session_manager()
    session_id = session_manager.create_session()
    print(f"Created new session: {session_id}")
    
    # Manually set up a workflow state that would be created
    # after user input for debugging
    def setup_state(current_state):
        # Set root step as complete
        current_state["workflow"]["root"]["status"] = "complete"
        
        # Add get-question step with user input
        current_state["workflow"]["get-question"] = {"status": "complete"}
        current_state["data"]["outputs"]["get-question"] = {
            "waiting_for_input": True,
            "prompt": "How can I help you today?",
            "response": "Tell me about the weather"  # This is what would come from user input
        }
        
        return current_state
    
    # Update the session state
    session_manager.update_session_state(session_id, setup_state)
    
    # Get the updated state
    state = session_manager.get_session_state(session_id)
    print("\nSession state after setup:")
    print(json.dumps(state, indent=2))
    
    # Now try to process the workflow - this should activate generate-answer
    engine = get_graph_workflow_engine()
    
    # Check next steps
    print("\nChecking next steps from get-question...")
    next_steps = engine._get_outgoing_relationships("get-question")
    print(f"Next steps: {next_steps}")
    
    # Update execution paths
    print("\nUpdating execution paths...")
    engine._update_execution_paths(session_id)
    
    # Get updated state
    state = session_manager.get_session_state(session_id)
    print("\nWorkflow state after updating paths:")
    for step_id, info in state["workflow"].items():
        print(f"  Step {step_id}: {info['status']}")
    
    # Try to process the generate-answer step
    print("\nProcessing generate-answer step...")
    if "generate-answer" in state["workflow"]:
        # Get the step details
        step_details = engine._get_step_details("generate-answer")
        print(f"Step details: {step_details}")
        
        # Manually resolve the input
        from core.variable_resolver import resolve_inputs
        input_data = json.loads(step_details["input"]) if step_details["input"] else {}
        
        # Print the input data
        print("\nInput data for generate-answer:")
        for key, value in input_data.items():
            if key == "schema":
                print(f"  {key}: [schema object]")
            elif key == "system":
                print(f"  {key}: {str(value)[:30]}...")
            else:
                print(f"  {key}: {value}")
        
        # Replace SESSION_ID with actual session id in user field
        if "user" in input_data and isinstance(input_data["user"], str):
            input_data["user"] = input_data["user"].replace("@{SESSION_ID}", f"@{{{session_id}}}")
        
        # Resolve variables
        resolved_inputs = resolve_inputs(input_data, state)
        print("\nResolved inputs for generate-answer:")
        if resolved_inputs:
            for key, value in resolved_inputs.items():
                if key == "schema":
                    print(f"  {key}: [schema object]")
                elif key == "system":
                    print(f"  {key}: {str(value)[:30]}...")
                else:
                    print(f"  {key}: {value}")
        else:
            print("  Failed to resolve inputs")
            
        # Try to execute the generate step manually
        try:
            utility_name = step_details["utility"]
            utility_func = engine.utility_registry.get_utility(utility_name)
            
            if utility_func:
                print(f"\nExecuting utility function: {utility_name}")
                if resolved_inputs and "user" in resolved_inputs:
                    result = utility_func(**resolved_inputs)
                    print(f"Result: {result}")
                else:
                    # Set user parameter manually for testing
                    resolved_inputs = resolved_inputs or {}
                    resolved_inputs["user"] = "Tell me about the weather"
                    print("Using manual user input:", resolved_inputs["user"])
                    result = utility_func(**resolved_inputs)
                    print(f"Result: {result}")
            else:
                print(f"Utility not found: {utility_name}")
        except Exception as e:
            print(f"Error executing utility: {e}")
    else:
        print("generate-answer step not found in workflow state")

if __name__ == "__main__":
    run_debug_workflow() 