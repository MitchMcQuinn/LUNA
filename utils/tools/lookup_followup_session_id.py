from core.session_manager import get_session_manager
from utils.code import sanitize_neo4j_values
import logging
import json
import sys

def main():
    """
    Look up the session by message ID, then create a message node in the graph 
    for the bot's response and link it to that session.
    """
    logger = logging.getLogger(__name__)
    
    # Setup detailed logging
    logger.info("=" * 50)
    logger.info("LOOKUP_FOLLOWUP_SESSION_ID SCRIPT START")
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
    required_vars = ['message_id', 'response_id', 'response_content']
    optional_vars = ['channel_id', 'created_at', 'author_username']
    
    # Validate required variables
    missing_vars = []
    for var in required_vars:
        if var not in globals() or globals()[var] is None:
            missing_vars.append(var)
            logger.error(f"MISSING REQUIRED VARIABLE: {var}")
        else:
            logger.info(f"FOUND required variable: {var} = {globals()[var]}")
    
    # Validate optional variables
    for var in optional_vars:
        if var in globals() and globals()[var] is not None:
            logger.info(f"FOUND optional variable: {var} = {globals()[var]}")
        else:
            logger.warning(f"Optional variable not found: {var}")
    
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
    logger.info(f"Bot response ID: {response_id}")
    
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
            logger.info(f"Original message properties: {json.dumps(dict(original_message))}")
            
            # Create the new message node and relationships
            # Extract channel_id from original message if not available
            channel_id_value = getattr(globals(), 'channel_id', original_message.get("channel_id", "unknown"))
            created_at_value = getattr(globals(), 'created_at', "")
            author_username_value = getattr(globals(), 'author_username', "bot")
            
            logger.info(f"Using channel_id: {channel_id_value}")
            logger.info(f"Using created_at: {created_at_value}")
            logger.info(f"Using author_username: {author_username_value}")
            
            create_query = """
            MATCH (s:SESSION {id: $session_id})
            MATCH (m:MESSAGE {message_id: $message_id})
            CREATE (new_msg:MESSAGE {
                message_id: $response_id,
                content: $response_content,
                author_username: $author_username,
                created_at: $created_at,
                channel_id: $channel_id,
                session_id: $session_id
            })
            CREATE (s)-[r1:HAS_MESSAGE]->(new_msg)
            CREATE (new_msg)-[r2:REPLY_TO]->(m)
            RETURN new_msg, m, s, r1, r2
            """
            
            # Parameters for the create query
            create_params = sanitize_neo4j_values({
                "session_id": session_id,
                "message_id": message_id,
                "response_id": response_id,
                "response_content": response_content,
                "author_username": author_username_value,
                "created_at": created_at_value,
                "channel_id": channel_id_value
            })
            
            logger.info(f"Running create query with params: {json.dumps(create_params)}")
            
            # Create new message and relationships
            create_result = db_session.run(create_query, create_params)
            create_record = create_result.single()
            
            if create_record:
                new_message = create_record["new_msg"]
                original_message = create_record["m"]
                session = create_record["s"]
                has_message_rel = create_record["r1"]
                reply_to_rel = create_record["r2"]
                
                logger.info(f"Successfully created message node for response {response_id}")
                logger.info(f"New message properties: {json.dumps(dict(new_message))}")
                
                # Build detailed response
                response = {
                    "success": True, 
                    "session_id": session_id,
                    "new_message": {
                        "id": new_message["message_id"],
                        "content": new_message["content"],
                        "author": new_message["author_username"],
                        "created_at": new_message["created_at"],
                        "channel_id": new_message["channel_id"]
                    },
                    "original_message": {
                        "id": original_message["message_id"],
                        "content": original_message.get("content", "N/A")
                    },
                    "relationships": {
                        "session_has_message": True,
                        "reply_to": True
                    }
                }
                
                logger.info(f"Returning successful response: {json.dumps(response)}")
                return response
            else:
                logger.error(f"Failed to create message node for response {response_id}")
                return {"success": False, "error": "Failed to create message node", "session_id": session_id}
                
    except Exception as e:
        import traceback
        logger.error(f"Error in lookup_followup_session_id: {str(e)}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
    finally:
        logger.info("=" * 50)
        logger.info("LOOKUP_FOLLOWUP_SESSION_ID SCRIPT END")
        logger.info("=" * 50)

# Set the result for the workflow
result = main()

"""
Note on Variable Resolution:
Outputs from this script can be referenced in subsequent workflow steps using the following syntax:
- Success status: @{SESSION_ID}.step_id.success (returns True/False)
- Session ID: @{SESSION_ID}.step_id.session_id
- New message ID: @{SESSION_ID}.step_id.new_message.id
- New message content: @{SESSION_ID}.step_id.new_message.content
- New message author: @{SESSION_ID}.step_id.new_message.author
- New message created_at: @{SESSION_ID}.step_id.new_message.created_at
- New message channel_id: @{SESSION_ID}.step_id.new_message.channel_id
- Original message ID: @{SESSION_ID}.step_id.original_message.id
- Original message content: @{SESSION_ID}.step_id.original_message.content
- Error (if failed): @{SESSION_ID}.step_id.error

For indexed access to a specific execution history entry:
- @{SESSION_ID}.step_id[index].field

Examples:
- @{SESSION_ID}.lookup_session.success (boolean value)
- @{SESSION_ID}.lookup_session.session_id (session ID from database)
- @{SESSION_ID}.lookup_session.new_message.id (newly created message ID)
- @{SESSION_ID}.lookup_session[0].relationships.session_has_message (boolean from first execution)

Expected Configuration Format:
When configuring this script in a workflow step, provide the following input parameters:
{
  "function": "utils.code.code",
  "file_path": "lookup_followup_session_id.py",
  "variables": {
    "message_id": "ORIGINAL_MESSAGE_ID", // ID of the message to look up
    "response_id": "BOT_RESPONSE_ID", // ID of the bot's response message
    "response_content": "Content of the bot's response", // Message content
    "channel_id": "CHANNEL_ID", // Optional: Discord channel ID
    "created_at": "TIMESTAMP", // Optional: Timestamp of creation
    "author_username": "bot" // Optional: Defaults to "bot"
  }
}

These variables can also use variable resolution syntax to reference outputs from previous steps:
{
  "function": "utils.code.code",
  "file_path": "lookup_followup_session_id.py",
  "variables": {
    "message_id": "@{SESSION_ID}.extract_message.id",
    "response_id": "@{SESSION_ID}.send_discord_message.response.id",
    "response_content": "@{SESSION_ID}.send_discord_message.response.content"
  }
}
"""

