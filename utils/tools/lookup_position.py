from core.session_manager import get_session_manager
from utils.code import sanitize_neo4j_values
import logging
import json
import sys

def main():
    """
    Look up a session by message ID, then find the most recent message in that session
    without an inbound REPLY_TO relationship (i.e., a message that hasn't been replied to yet).
    """
    logger = logging.getLogger(__name__)
    
    # Setup detailed logging
    logger.info("=" * 50)
    logger.info("LOOKUP_MESSAGE_ID SCRIPT START")
    logger.info("=" * 50)
    
    # Log environment info
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Script name: {__name__}")
    
    # Log all available global variables
    logger.info("Available variables in global scope:")
    for var_name in globals():
        if not var_name.startswith('__'):
            var_value = globals()[var_name]
            var_type = type(var_value).__name__
            try:
                # Truncate long values for readability
                if isinstance(var_value, str) and len(var_value) > 50:
                    display_value = f"{var_value[:50]}... (truncated)"
                else:
                    display_value = var_value
                logger.info(f"  {var_name}: {display_value} (type: {var_type})")
            except:
                logger.info(f"  {var_name}: <unprintable> (type: {var_type})")
    
    # Check for required variables
    required_vars = ['message_id']
    
    # Validate required variables
    missing_vars = []
    for var in required_vars:
        if var not in globals() or globals()[var] is None:
            missing_vars.append(var)
            logger.error(f"MISSING REQUIRED VARIABLE: {var}")
        else:
            logger.info(f"FOUND required variable: {var} = {globals()[var]}")
    
    # Exit if missing required variables
    if missing_vars:
        error_msg = f"Missing required variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        return {
            "success": False, 
            "error": error_msg,
            "missing_variables": missing_vars
        }
    
    # All variables are injected by the code utility through the variables parameter
    logger.info(f"Looking up session using message_id: {message_id}")
    
    # Get session manager for database access
    session_manager = get_session_manager()
    
    try:
        # Use get_session() instead of session()
        with session_manager.driver.get_session() as db_session:
            # First find the session associated with the original message
            lookup_query = """
            MATCH (m:MESSAGE {message_id: $message_id})
            MATCH (s:SESSION)-[:HAS_MESSAGE]->(m)
            RETURN m, s
            """
            
            # Sanitize the parameters to ensure they're safe for Neo4j
            lookup_params = sanitize_neo4j_values({"message_id": message_id})
            
            logger.info(f"Running lookup query with params: {json.dumps(lookup_params)}")
            
            # Look up the original message and session
            lookup_result = db_session.run(lookup_query, lookup_params)
            lookup_record = lookup_result.single()
            
            if not lookup_record:
                logger.warning(f"No session found for message {message_id}")
                return {
                    "success": False, 
                    "error": "No session found",
                    "original_message_id": message_id
                }
                
            # Get session and message data
            original_message = lookup_record["m"]
            session = lookup_record["s"]
            session_id = session["id"]
            
            logger.info(f"Found session {session_id} for message {message_id}")
            
            # Now find the most recent message in the session without an inbound REPLY_TO relationship
            # but exclude messages from the bot itself to prevent replying to own messages
            unreplied_query = """
            MATCH (s:SESSION {id: $session_id})-[:HAS_MESSAGE]->(m:MESSAGE)
            WHERE NOT EXISTS { MATCH ()-[:REPLY_TO]->(m) }
            AND m.author_username <> 'bot'
            RETURN m
            ORDER BY m.created_at DESC
            LIMIT 1
            """
            
            unreplied_params = sanitize_neo4j_values({"session_id": session_id})
            
            logger.info(f"Running unreplied message query with params: {json.dumps(unreplied_params)}")
            
            # Find the most recent unreplied message
            unreplied_result = db_session.run(unreplied_query, unreplied_params)
            unreplied_record = unreplied_result.single()
            
            if not unreplied_record:
                logger.warning(f"No unreplied message found in session {session_id}")
                return {
                    "success": False, 
                    "error": "No unreplied message found",
                    "session_id": session_id
                }
            
            # Get the unreplied message data
            unreplied_message = unreplied_record["m"]
            unreplied_message_id = unreplied_message["message_id"]
            
            logger.info(f"Found unreplied message {unreplied_message_id} in session {session_id}")
            
            # Build detailed response
            response = {
                "success": True, 
                "session_id": session_id,
                "original_message_id": message_id,
                "unreplied_message": {
                    "id": unreplied_message["message_id"],
                    "content": unreplied_message.get("content", "N/A"),
                    "author": unreplied_message.get("author_username", "N/A"),
                    "created_at": unreplied_message.get("created_at", "N/A"),
                    "channel_id": unreplied_message.get("channel_id", "N/A")
                }
            }
            
            logger.info(f"Returning successful response: {json.dumps(response)}")
            return response
                
    except Exception as e:
        import traceback
        logger.error(f"Error in lookup_message_id: {str(e)}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
    finally:
        logger.info("=" * 50)
        logger.info("LOOKUP_MESSAGE_ID SCRIPT END")
        logger.info("=" * 50)

# Set the result for the workflow
result = main()

"""
Note on Variable Resolution:
Outputs from this script can be referenced in subsequent workflow steps using the following syntax:
- Success status: @{SESSION_ID}.step_id.success (returns True/False)
- Session ID: @{SESSION_ID}.step_id.session_id
- Original message ID: @{SESSION_ID}.step_id.original_message_id
- Unreplied message ID: @{SESSION_ID}.step_id.unreplied_message.id
- Unreplied message content: @{SESSION_ID}.step_id.unreplied_message.content
- Unreplied message author: @{SESSION_ID}.step_id.unreplied_message.author
- Unreplied message created_at: @{SESSION_ID}.step_id.unreplied_message.created_at
- Unreplied message channel_id: @{SESSION_ID}.step_id.unreplied_message.channel_id
- Error (if failed): @{SESSION_ID}.step_id.error

For indexed access to a specific execution history entry:
- @{SESSION_ID}.step_id[index].field

Examples:
- @{SESSION_ID}.lookup_message.success (boolean value)
- @{SESSION_ID}.lookup_message.session_id (session ID from database)
- @{SESSION_ID}.lookup_message.unreplied_message.id (ID of the unreplied message)

Expected Configuration Format:
When configuring this script in a workflow step, provide the following input parameters:
{
  "function": "utils.code.code",
  "file_path": "lookup_message_id.py",
  "variables": {
    "message_id": "MESSAGE_ID" // ID of the message to look up the session for
  }
}

These variables can also use variable resolution syntax to reference outputs from previous steps:
{
  "function": "utils.code.code",
  "file_path": "lookup_message_id.py",
  "variables": {
    "message_id": "@{SESSION_ID}.extract_message.id"
  }
}
"""
