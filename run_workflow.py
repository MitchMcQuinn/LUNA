"""
Script to test running a workflow directly.
"""

import os
import sys
import logging
import time
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set up path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)  # Add current directory to path

# Load environment
env_path = os.path.join(script_dir, '.env.local')
load_dotenv(env_path)

# Import core components
from core.graph_engine import get_graph_workflow_engine
from core.session_manager import get_session_manager

def run_workflow():
    """Run a workflow with interactive input handling"""
    try:
        # Create a new session
        session_manager = get_session_manager()
        session_id = session_manager.create_session()
        logger.info(f"Created new session: {session_id}")
        
        # Get workflow engine
        engine = get_graph_workflow_engine()
        
        # Start processing workflow
        status = engine.process_workflow(session_id)
        logger.info(f"Initial workflow status: {status}")
        
        # Safety mechanism to prevent infinite loops
        max_iterations = 10
        iteration_count = 0
        processed_states = set()
        
        # Main interaction loop
        while status in ["active", "awaiting_input"] and iteration_count < max_iterations:
            # Track iteration count
            iteration_count += 1
            
            # Get state and create a hash to track if we're in a loop
            current_state = session_manager.get_session_state(session_id)
            state_hash = hash(frozenset([(step_id, info["status"]) for step_id, info in current_state["workflow"].items()]))
            
            # Check if we've seen this exact state before
            if state_hash in processed_states:
                print("\nWARNING: Detected a loop in workflow processing. Same state encountered multiple times.")
                break
                
            processed_states.add(state_hash)
            
            if status == "awaiting_input":
                # Get session state
                state = session_manager.get_session_state(session_id)
                
                # Find the awaiting step
                awaiting_step = None
                for step_id, info in state["workflow"].items():
                    if info["status"] == "awaiting_input":
                        awaiting_step = step_id
                        break
                
                # Get prompt from the step output
                prompt = "Input required: "
                if awaiting_step and awaiting_step in state["data"]["outputs"]:
                    req_data = state["data"]["outputs"][awaiting_step]
                    if req_data and isinstance(req_data, dict):
                        prompt = req_data.get("prompt", prompt)
                
                # Get user input
                user_input = input(f"\n{prompt} ")
                
                # Add the 'response' field to make variable resolution work
                processed_input = {"response": user_input}
                
                # Process user input
                status = engine.handle_user_input(session_id, processed_input)
                logger.info(f"Workflow status after input: {status}")
                
                # Continue processing the workflow until completion or input required
                if status == "active":
                    status = engine.process_workflow(session_id)
                    logger.info(f"Workflow status after processing: {status}")
                
                # Display any system messages
                state = session_manager.get_session_state(session_id)
                
                # Check for any outputs with messages that need to be displayed
                for step_id, output in state["data"]["outputs"].items():
                    if (state["workflow"].get(step_id, {}).get("status") == "complete" and 
                        isinstance(output, dict) and "message" in output):
                        print(f"\nAssistant: {output['message']}")
                        
                # Also display any messages in the messages array    
                for msg in state["data"].get("messages", []):
                    if msg.get("role") == "assistant":
                        print(f"\nAssistant: {msg.get('content')}")
            else:
                # Continue processing if active
                status = engine.process_workflow(session_id)
                logger.info(f"Workflow status: {status}")
                
                # Display any new outputs
                state = session_manager.get_session_state(session_id)
                for step_id, output in state["data"]["outputs"].items():
                    if (state["workflow"].get(step_id, {}).get("status") == "complete" and 
                        isinstance(output, dict) and "message" in output):
                        print(f"\nAssistant: {output['message']}")
        
        # Check if we hit the iteration limit
        if iteration_count >= max_iterations:
            print(f"\nWARNING: Reached maximum iteration count ({max_iterations}). Workflow may be stuck in a loop.")
        
        # Final status check
        if status == "completed":
            print("\nWorkflow completed successfully.")
        else:
            print(f"\nWorkflow ended with status: {status}")
            
        # Show workflow state summary
        state = session_manager.get_session_state(session_id)
        print("\nFinal workflow state:")
        for step_id, info in state["workflow"].items():
            status_str = info['status']
            if status_str == 'error' and 'error' in info:
                status_str += f" - {info['error']}"
            print(f"  Step {step_id}: {status_str}")
        
        # Print step outputs
        print("\nStep Outputs:")
        for step_id, output in state["data"]["outputs"].items():
            print(f"  {step_id}: {output}")
        
        return session_id
        
    except Exception as e:
        logger.error(f"Error running workflow: {e}")
        import traceback
        traceback.print_exc()
        
if __name__ == "__main__":
    run_workflow() 