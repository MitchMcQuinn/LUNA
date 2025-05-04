"""
Retrieve messages from an existing workflow session.

This script gets messages from an existing workflow session using the SessionManager directly,
without requiring an HTTP request to a nested server.

Example usage in workflow:
{
  "function": "utils.code.code",
  "file_path": "get_session_messages.py",
  "variables": {
    "session_id": "@{SESSION_ID}.create_nested_session.session_id",
    "limit": 10
  }
}
"""

from core.session_manager import get_session_manager
import logging
import json

def main():
    """
    Get messages from an existing workflow session.
    
    Required variables:
    - session_id: ID of the session to get messages from
    
    Optional variables:
    - limit: Maximum number of messages to return (default: all messages)
    - after_timestamp: Only return messages after this timestamp
    
    Returns:
    - Dictionary containing the session messages
    """
    logger = logging.getLogger(__name__)
    
    # These variables will be injected by the code utility from the pre-resolved variables
    if 'session_id' not in globals():
        logger.error("No session_id provided")
        return {
            "success": False,
            "error": "No session_id provided"
        }
    
    # Get optional parameters
    message_limit = limit if 'limit' in globals() else None
    timestamp_filter = after_timestamp if 'after_timestamp' in globals() else None
    
    logger.info(f"Getting messages from session {session_id}")
    if message_limit:
        logger.info(f"Limiting to {message_limit} messages")
    if timestamp_filter:
        logger.info(f"Filtering messages after timestamp {timestamp_filter}")
    
    try:
        # Get the session manager
        session_manager = get_session_manager()
        
        # Make sure session exists
        state = session_manager.get_session_state(session_id)
        if not state:
            logger.error(f"Session {session_id} not found")
            return {
                "success": False,
                "error": f"Session {session_id} not found"
            }
        
        # Extract messages from the session state
        if "data" in state and "messages" in state["data"]:
            messages = state["data"]["messages"]
            
            # Apply timestamp filter if provided
            if timestamp_filter:
                messages = [msg for msg in messages if msg.get("timestamp", 0) > timestamp_filter]
            
            # Apply limit if provided
            if message_limit and message_limit > 0:
                messages = messages[-message_limit:]
            
            return {
                "success": True,
                "session_id": session_id,
                "messages": messages,
                "count": len(messages)
            }
        else:
            logger.info(f"No messages found in session {session_id}")
            return {
                "success": True,
                "session_id": session_id,
                "messages": [],
                "count": 0
            }
    
    except Exception as e:
        logger.error(f"Error getting messages from session: {str(e)}", exc_info=True)
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
- Messages: @{SESSION_ID}.step_id.messages
- Message count: @{SESSION_ID}.step_id.count

For indexed access to a specific execution history entry:
- @{SESSION_ID}.step_id[index].field

For indexed access to a specific message:
- @{SESSION_ID}.step_id.messages[0].content

Expected Configuration Format:
When configuring this script in a workflow step, provide the following input parameters:
{
  "function": "utils.code.code",
  "file_path": "get_session_messages.py",
  "variables": {
    "session_id": "@{SESSION_ID}.create_nested_session.session_id",  // Session ID to get messages from
    "limit": 10,  // Optional: Maximum number of messages to return
    "after_timestamp": 1618529400  // Optional: Only return messages after this timestamp
  }
}
""" 