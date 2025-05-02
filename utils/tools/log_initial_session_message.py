from core.session_manager import get_session_manager
from utils.code import sanitize_neo4j_values
import logging
import json
import sys

def main():
    """
    Log the initial message to the Neo4j database by creating a MESSAGE node
    and connecting it to the SESSION node with a HAS_MESSAGE relationship.
    
    The message properties are injected by the code utility through the variables parameter.
    Required variables:
    - session_id: The ID of the session
    - message_id: The ID of the message
    - content: The content of the message
    - author_username: The username of the message author
    - created_at: The timestamp when the message was created
    - channel_id: The Discord channel ID
    """
    logger = logging.getLogger(__name__)
    
    # Get session manager for database access
    session_manager = get_session_manager()
    
    # Detailed debugging of local and global variables
    logger.info("=== SCRIPT EXECUTION ENVIRONMENT ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Script name: {__name__}")
    
    # Check if required variables exist in the global scope
    required_vars = ["session_id", "message_id", "content", "author_username", "created_at", "channel_id", "guild_id"]
    logger.info("=== VARIABLE EXISTENCE CHECK ===")
    
    missing_vars = []
    for var in required_vars:
        if var in globals():
            logger.info(f"✓ Variable '{var}' exists in globals")
        else:
            logger.warning(f"✗ Variable '{var}' MISSING from globals")
            missing_vars.append(var)
    
    if missing_vars:
        error_msg = f"Missing required variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        return [{"status": "error", "error": error_msg, "missing_variables": missing_vars}]
    
    # Log all input variables with detailed type info
    logger.info("=== LOG_INITIAL_SESSION_MESSAGE INPUTS ===")
    logger.info(f"session_id: {session_id} (type: {type(session_id).__name__})")
    logger.info(f"message_id: {message_id} (type: {type(message_id).__name__})")
    logger.info(f"content: {content} (type: {type(content).__name__})")
    logger.info(f"author_username: {author_username} (type: {type(author_username).__name__})")
    logger.info(f"created_at: {created_at} (type: {type(created_at).__name__})")
    logger.info(f"channel_id: {channel_id} (type: {type(channel_id).__name__})")
    logger.info(f"guild_id: {guild_id} (type: {type(guild_id).__name__})")
    logger.info("======================================")
    
    # Validate variable contents
    logger.info("=== VARIABLE CONTENT VALIDATION ===")
    is_valid = True
    
    if not session_id or not isinstance(session_id, str):
        logger.error(f"Invalid session_id: {session_id}")
        is_valid = False
    
    if not message_id or not isinstance(message_id, str):
        logger.error(f"Invalid message_id: {message_id}")
        is_valid = False
    
    if not content or not isinstance(content, str):
        logger.warning(f"Potentially invalid content: {content}")
    
    if not channel_id or not isinstance(channel_id, str):
        logger.error(f"Invalid channel_id: {channel_id}")
        is_valid = False
    
    if not is_valid:
        error_msg = "One or more variables have invalid values"
        logger.error(error_msg)
        return [{"status": "error", "error": error_msg}]
    
    try:
        # Create a query to insert the message and link it to the session
        cypher_query = """
        MATCH (s:SESSION {id: $session_id})
        CREATE (m:MESSAGE {
            session_id: $session_id,
            message_id: $message_id, 
            content: $content,
            author_username: $author_username,
            created_at: $created_at,
            channel_id: $channel_id,
            guild_id: $guild_id
        })
        CREATE (s)-[:HAS_MESSAGE]->(m)
        RETURN m.message_id, s.id
        """
        
        logger.info(f"Executing query to create message node for message {message_id} in session {session_id}")
        logger.info(f"Cypher query: {cypher_query}")
        
        # Sanitize the parameters to ensure they're safe for Neo4j
        params = sanitize_neo4j_values({
            "session_id": session_id,
            "message_id": message_id,
            "content": content,
            "author_username": author_username,
            "created_at": created_at,
            "channel_id": channel_id,
            "guild_id": guild_id
        })
        
        logger.info(f"Query parameters: {json.dumps(params, indent=2)}")
        
        # Execute the query
        with session_manager.driver.get_session() as db_session:
            logger.info("Obtained Neo4j database session")
            result = db_session.run(cypher_query, params)
            logger.info("Query executed successfully")
            record = result.single()
            
            if record:
                logger.info(f"Successfully logged message {record['m.message_id']} for session {record['s.id']}")
                success_result = {
                    "message_id": record["m.message_id"],
                    "session_id": record["s.id"],
                    "status": "success"
                }
                logger.info(f"Returning result: {json.dumps(success_result, indent=2)}")
                return [success_result]
            else:
                error_msg = f"Failed to log message {message_id} for session {session_id} - no record returned"
                logger.error(error_msg)
                error_result = {
                    "message_id": message_id,
                    "session_id": session_id,
                    "status": "error",
                    "error": "No record returned from database"
                }
                logger.info(f"Returning error result: {json.dumps(error_result, indent=2)}")
                return [error_result]
                
    except Exception as e:
        error_msg = f"Error in log_initial_session_message: {str(e)}"
        logger.error(error_msg)
        logger.exception("Full exception details:")
        error_result = {
            "message_id": message_id if 'message_id' in globals() else "UNKNOWN",
            "session_id": session_id if 'session_id' in globals() else "UNKNOWN",
            "status": "error",
            "error": str(e)
        }
        logger.info(f"Returning exception result: {json.dumps(error_result, indent=2)}")
        return [error_result]

# Set the result for the workflow
logger = logging.getLogger(__name__)
logger.info("=== STARTING LOG_INITIAL_SESSION_MESSAGE SCRIPT ===")
try:
    result = main()
    logger.info(f"Script execution completed. Result: {json.dumps(result, indent=2)}")
except Exception as e:
    logger.critical(f"Critical error in script execution: {str(e)}")
    logger.exception("Script execution failed:")
    result = [{"status": "error", "error": f"Script execution failed: {str(e)}"}]

"""
Note on Variable Resolution:
Outputs from this script can be referenced in subsequent workflow steps using the following syntax:
- First result element: @{SESSION_ID}.step_id[0] (access the first array element)
- Message ID: @{SESSION_ID}.step_id[0].message_id
- Session ID: @{SESSION_ID}.step_id[0].session_id
- Status: @{SESSION_ID}.step_id[0].status ('success' or 'error')
- Error (if any): @{SESSION_ID}.step_id[0].error

Note that this script returns an array with a single element, so indexing [0] is required.

Examples:
- @{SESSION_ID}.log_message[0].status (status of operation - 'success' or 'error')
- @{SESSION_ID}.log_message[0].message_id (ID of the message that was logged)
- @{SESSION_ID}.log_message[0].session_id (ID of the session the message was linked to)
- @{SESSION_ID}.log_message[0].error (error message if status is 'error')

Expected Configuration Format:
When configuring this script in a workflow step, provide the following input parameters:
{
  "function": "utils.code.code",
  "file_path": "log_initial_session_message.py",
  "variables": {
    "session_id": "SESSION_ID", // ID of the session
    "message_id": "MESSAGE_ID", // ID of the message to log
    "content": "Message content", // Content of the message
    "author_username": "username", // Author of the message
    "created_at": "TIMESTAMP", // Creation timestamp
    "channel_id": "CHANNEL_ID", // Discord channel ID
    "guild_id": "GUILD_ID" // Discord guild/server ID
  }
}

These variables can also use variable resolution syntax to reference outputs from previous steps:
{
  "function": "utils.code.code",
  "file_path": "log_initial_session_message.py",
  "variables": {
    "session_id": "@{SESSION_ID}.create_channel_session[0].response.session_id",
    "message_id": "@{SESSION_ID}.initial.message.id",
    "content": "@{SESSION_ID}.initial.message.content",
    "author_username": "@{SESSION_ID}.initial.author.username",
    "created_at": "@{SESSION_ID}.initial.message.createdAt",
    "channel_id": "@{SESSION_ID}.initial.channel_id",
    "guild_id": "@{SESSION_ID}.initial.guild.id"
  }
}
"""
