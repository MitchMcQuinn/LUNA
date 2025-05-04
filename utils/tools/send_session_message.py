"""
Send a message to an existing workflow session.

This script sends a message to an existing workflow session using the GraphWorkflowEngine directly,
without requiring an HTTP request to a nested server.

Example usage in workflow:
{
  "function": "utils.code.code",
  "file_path": "send_session_message.py",
  "variables": {
    "session_id": "@{SESSION_ID}.create_nested_session.session_id",
    "message": "Hello from the parent workflow!"
  }
}
"""

from core.graph_engine import get_graph_workflow_engine
from core.session_manager import get_session_manager
import logging
import json
import uuid
import time

def main():
    """
    Send a message to an existing workflow session and process it.
    
    Required variables:
    - session_id: ID of the session to send the message to
    - message: Message content to send
    
    Returns:
    - Dictionary containing the session response and status
    """
    logger = logging.getLogger(__name__)
    
    # These variables will be injected by the code utility from the pre-resolved variables
    if 'session_id' not in globals():
        logger.error("No session_id provided")
        return {
            "success": False,
            "error": "No session_id provided"
        }
    
    if 'message' not in globals():
        logger.error("No message content provided")
        return {
            "success": False,
            "error": "No message content provided"
        }
    
    logger.info(f"Sending message to session {session_id}: {message}")
    
    try:
        # Get the necessary components
        engine = get_graph_workflow_engine()
        session_manager = get_session_manager()
        
        # Make sure session exists
        state = session_manager.get_session_state(session_id)
        if not state:
            logger.error(f"Session {session_id} not found")
            return {
                "success": False,
                "error": f"Session {session_id} not found"
            }
        
        # Add user message to the session
        current_time = time.time()
        user_message = {
            "role": "user", 
            "content": message,
            "_message_id": str(uuid.uuid4())[:8],
            "timestamp": current_time
        }
        
        # Update the session state with the user message
        def update_with_user_message(current_state):
            if "data" not in current_state:
                current_state["data"] = {}
            if "messages" not in current_state["data"]:
                current_state["data"]["messages"] = []
            
            # Add user message
            current_state["data"]["messages"].append(user_message)
            return current_state
        
        session_manager.update_session_state(session_id, update_with_user_message)
        logger.info(f"Added user message to session state")
        
        # Handle user input with the message
        status = engine.handle_user_input(session_id, message)
        logger.info(f"Status after handling input: {status}")
        
        # Process the workflow until completion or awaiting input
        if status == "active":
            logger.info(f"Processing workflow after user input")
            processing_start = time.time()
            
            # Process with timeout protection
            max_iterations = 20
            iteration = 0
            while status == "active" and iteration < max_iterations:
                logger.info(f"Processing workflow iteration {iteration+1}")
                status = engine.process_workflow(session_id)
                logger.info(f"Status after processing: {status}")
                iteration += 1
                
                # Break if taking too long
                if time.time() - processing_start > 30:  # 30 seconds max processing time
                    logger.warning(f"Processing timeout reached for session {session_id}")
                    break
                    
            if iteration >= max_iterations:
                logger.warning(f"Reached maximum workflow processing iterations for session {session_id}")
        
        # Get updated session state
        state = session_manager.get_session_state(session_id)
        
        # Extract assistant responses that came after our message
        assistant_responses = []
        if "data" in state and "messages" in state["data"]:
            # Find all assistant messages after our user message
            messages = state["data"]["messages"]
            found_our_message = False
            
            for msg in messages:
                if not found_our_message and msg.get("role") == "user" and msg.get("content") == message:
                    found_our_message = True
                    continue
                
                if found_our_message and msg.get("role") == "assistant":
                    assistant_responses.append(msg)
        
        # Return the result
        return {
            "success": True,
            "session_id": session_id,
            "status": status,
            "responses": assistant_responses,
            "message_sent": message
        }
    
    except Exception as e:
        logger.error(f"Error sending message to session: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id
        }

# Set the result for the workflow
result = main()

"""
Note on Variable Resolution:
Outputs from this script can be referenced in subsequent workflow steps using the following syntax:
- Success status: @{SESSION_ID}.step_id.success
- Error message (if any): @{SESSION_ID}.step_id.error
- Session ID: @{SESSION_ID}.step_id.session_id
- Workflow status: @{SESSION_ID}.step_id.status
- Assistant responses: @{SESSION_ID}.step_id.responses

For indexed access to a specific execution history entry:
- @{SESSION_ID}.step_id[index].field

Expected Configuration Format:
When configuring this script in a workflow step, provide the following input parameters:
{
  "function": "utils.code.code",
  "file_path": "send_session_message.py",
  "variables": {
    "session_id": "@{SESSION_ID}.create_nested_session.session_id",  // Session ID to send message to
    "message": "Your message content here"  // Message to send to the session
  }
}
""" 