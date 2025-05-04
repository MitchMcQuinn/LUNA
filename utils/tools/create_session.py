"""
Create a new workflow session.

This script creates a new session using the core SessionManager directly,
without requiring an HTTP request to a nested server.

Example usage in workflow:
{
  "function": "utils.code.code",
  "file_path": "create_session.py",
  "variables": {
    "workflow_id": "my_workflow",
    "initial_data": {
      "key": "value",
      "another_key": "another_value"
    }
  }
}
"""

from core.session_manager import get_session_manager
import logging
import json

# Configure logger at the module level
logger = logging.getLogger(__name__)

def main():
    """
    Create a new workflow session and initialize it with data.
    
    Required variables:
    - workflow_id: ID of the workflow to run (defaults to "default" if not provided)
    - initial_data: Dictionary of initial data to add to the session (optional)
    """
    # These variables will be injected by the code utility from the pre-resolved variables
    # in the step input, so we can directly access them by name
    # If not provided, set defaults
    workflow_id_value = workflow_id if 'workflow_id' in globals() else "default"
    initial_data_value = initial_data if 'initial_data' in globals() else {}
    
    logger.info(f"Creating new session with workflow_id: {workflow_id_value}")
    logger.info(f"Initial data: {json.dumps(initial_data_value, default=str)}")
    
    # Get the session manager
    session_manager = get_session_manager()
    
    # Create the session
    session_id = session_manager.create_session(workflow_id_value)
    logger.info(f"Created session with ID: {session_id}")
    
    # If initial data was provided, update the session state
    if initial_data_value:
        def update_with_initial_data(current_state):
            # Initialize data structure if needed
            if "data" not in current_state:
                current_state["data"] = {}
            if "outputs" not in current_state["data"]:
                current_state["data"]["outputs"] = {}
            
            # Add each top-level key in initial_data as a separate step output
            # This makes them directly accessible via @{SESSION_ID}.key.subkey
            for key, value in initial_data_value.items():
                current_state["data"]["outputs"][key] = value
            
            # Also add the entire initial_data object as an "initial" step output
            # This allows accessing via @{SESSION_ID}.initial.key.subkey
            current_state["data"]["outputs"]["initial"] = initial_data_value
            
            logger.info(f"Updated session state with initial data for keys: {list(initial_data_value.keys())}")
            return current_state
        
        session_manager.update_session_state(session_id, update_with_initial_data)
    
    # Process the workflow to advance to the waiting step
    try:
        from core.graph_engine import get_graph_workflow_engine
        engine = get_graph_workflow_engine()
        status = engine.process_workflow(session_id)
        logger.info(f"Initial workflow process status: {status}")
    except Exception as e:
        logger.error(f"Error processing initial workflow: {e}")
    
    # Return the session information
    return {
        "session_id": session_id,
        "workflow_id": workflow_id_value,
        "initial_data": initial_data_value
    }

# Set the result for the workflow
result = main()

"""
Note on Variable Resolution:
Outputs from this script can be referenced in subsequent workflow steps using the following syntax:
- Session ID: @{SESSION_ID}.step_id.session_id
- Workflow ID: @{SESSION_ID}.step_id.workflow_id
- Initial data: @{SESSION_ID}.step_id.initial_data

For indexed access to a specific execution history entry:
- @{SESSION_ID}.step_id[index].field

Expected Configuration Format:
When configuring this script in a workflow step, provide the following input parameters:
{
  "function": "utils.code.code",
  "file_path": "create_session.py",
  "variables": {
    "workflow_id": "my_workflow",  // ID of the workflow to run
    "initial_data": {              // Initial data to populate
      "key": "value",
      "another_key": "another_value"
    }
  }
}
""" 