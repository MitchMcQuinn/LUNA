from core.session_manager import get_session_manager
from utils.code import sanitize_neo4j_values
import logging
import json
import inspect
import sys

def main():
    """
    Look up session by message reference ID to find existing sessions.
    
    Required variables:
    - message_id: The Discord message ID to look up (reference.messageId)
    """
    logger = logging.getLogger(__name__)
    
    # Enhanced logging for debugging variable resolution
    logger.info("========== LOOKUP CHANNEL SESSION DEBUG INFO ==========")
    
    # Log all available variables in the global namespace
    global_vars = {k: str(v) for k, v in globals().items() 
                   if not k.startswith('__') and not inspect.ismodule(v) and not inspect.isfunction(v)}
    logger.info(f"Available global variables: {json.dumps(global_vars, indent=2)}")
    
    # Log initial variable and any environment details
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current frame locals: {list(locals().keys())}")
    
    # Check for the required message_id variable
    if 'message_id' in globals():
        logger.info(f"message_id value: {message_id!r}")
    else:
        logger.error("ERROR: 'message_id' variable is not defined in the global scope")
    
    # Log initial message details if available
    if 'initial' in globals():
        try:
            logger.info(f"Initial message data: {json.dumps(initial, indent=2)}")
            if isinstance(initial, dict) and 'message' in initial and 'reference' in initial['message']:
                logger.info(f"Reference in initial message: {initial['message']['reference']}")
        except (TypeError, ValueError):
            logger.error("Could not serialize 'initial' variable to JSON", exc_info=True)
    
    # Get session manager for database access
    session_manager = get_session_manager()
    
    # Check if we have a message_id
    if not message_id:
        logger.warning("No message_id provided, cannot look up session")
        return {
            "session_id": None,
            "found": False,
            "debug_info": {
                "resolved_message_id": None,
                "error": "No message_id provided"
            }
        }
    
    logger.info(f"Looking up session for message reference: {message_id}")
    
    try:
        # Log the query we're about to execute
        cypher_query = """
        MATCH (m:MESSAGE {message_id: $message_id})
        MATCH (s:SESSION)-[:HAS_MESSAGE]->(m)
        RETURN s.id as session_id, m.message_id as message_id, m.content as content
        LIMIT 1
        """
        logger.info(f"Executing Neo4j query with params: {{'message_id': {message_id!r}}}")
        logger.info(f"Query: {cypher_query}")
        
        # Sanitize the parameters to ensure they're safe for Neo4j
        params = sanitize_neo4j_values({"message_id": message_id})
        logger.info(f"Sanitized params: {params}")
        
        # Execute the query
        with session_manager.driver.get_session() as db_session:
            result = db_session.run(cypher_query, params)
            record = result.single()
            
            if record:
                logger.info(f"Found session {record['session_id']} for message {message_id}")
                return {
                    "session_id": record["session_id"],
                    "message_id": record["message_id"],
                    "content": record["content"],
                    "found": True,
                    "debug_info": {
                        "resolved_message_id": message_id,
                        "query_params": params,
                        "success": True
                    }
                }
            else:
                logger.info(f"No session found for message {message_id}")
                # Try to find if the message exists at all
                try:
                    check_query = """
                    MATCH (m:MESSAGE {message_id: $message_id})
                    RETURN m.message_id as message_id, m.content as content, m.created_at as created_at
                    LIMIT 1
                    """
                    result = db_session.run(check_query, params)
                    msg_record = result.single()
                    
                    if msg_record:
                        logger.info(f"Message {message_id} exists but is not connected to a session")
                        msg_info = {
                            "message_id": msg_record["message_id"],
                            "content": msg_record["content"],
                            "created_at": msg_record.get("created_at", "unknown")
                        }
                    else:
                        logger.info(f"Message {message_id} does not exist in the database")
                        msg_info = None
                        
                    return {
                        "session_id": None,
                        "found": False,
                        "debug_info": {
                            "resolved_message_id": message_id,
                            "query_params": params,
                            "success": False,
                            "message_exists": msg_info is not None,
                            "message_info": msg_info
                        }
                    }
                except Exception as check_error:
                    logger.error(f"Error checking message existence: {str(check_error)}")
                    return {
                        "session_id": None,
                        "found": False,
                        "debug_info": {
                            "resolved_message_id": message_id,
                            "query_params": params,
                            "success": False,
                            "check_error": str(check_error)
                        }
                    }
                
    except Exception as e:
        logger.error(f"Error in lookup_channel_session by message: {str(e)}", exc_info=True)
        return {
            "session_id": None,
            "found": False,
            "error": str(e),
            "debug_info": {
                "resolved_message_id": message_id,
                "exception": str(e),
                "exception_type": type(e).__name__
            }
        }
    finally:
        logger.info("========== END LOOKUP CHANNEL SESSION DEBUG INFO ==========")

# Set the result for the workflow
result = main() 

"""
Note on Variable Resolution:
Outputs from this script can be referenced in subsequent workflow steps using the following syntax:
- Session ID: @{SESSION_ID}.step_id.session_id
- Message ID: @{SESSION_ID}.step_id.message_id
- Message content: @{SESSION_ID}.step_id.content
- Found status: @{SESSION_ID}.step_id.found (returns True/False)
- Error (if any): @{SESSION_ID}.step_id.error
- Debug info: @{SESSION_ID}.step_id.debug_info (contains detailed troubleshooting information)

For indexed access to a specific execution history entry:
- @{SESSION_ID}.step_id[index].field

Examples:
- @{SESSION_ID}.lookup_channel.found (boolean value indicating if session was found)
- @{SESSION_ID}.lookup_channel.session_id (session ID if found, null if not found)
- @{SESSION_ID}.lookup_channel.message_id (message ID of the referenced message)
- @{SESSION_ID}.lookup_channel.debug_info (detailed debugging information)

Expected Configuration Format:
When configuring this script in a workflow step, provide the following input parameters:
{
  "function": "utils.code.code",
  "file_path": "lookup_channel_session.py",
  "variables": {
    "message_id": "@{SESSION_ID}.initial.message.reference.messageId" // Message reference ID to look up
  }
}
""" 