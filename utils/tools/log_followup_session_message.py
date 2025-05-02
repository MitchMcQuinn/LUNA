from core.session_manager import get_session_manager
from utils.code import sanitize_neo4j_values
import logging
import json

def main():
    """
    Log the followup message to the Neo4j database by creating a MESSAGE node
    for the bot's response and connecting it to both the SESSION node and 
    the original message with a REPLY_TO relationship.
    
    The message properties are injected by the code utility through the variables parameter.
    Required variables:
    - session_id: The ID of the session from lookup_channel_session
    - message_id: The ID of the original message being replied to
    - response_id: The ID of the bot's response message
    - response_content: The content of the bot's response
    - author_username: The username of the response author (typically 'bot')
    - created_at: The timestamp when the response was created
    - channel_id: The Discord channel ID
    """
    logger = logging.getLogger(__name__)
    
    # Get session manager for database access
    session_manager = get_session_manager()
    
    # Log all input parameters for debugging
    logger.info("=== LOG_FOLLOWUP_SESSION_MESSAGE INPUTS ===")
    logger.info(f"session_id: {session_id}")
    logger.info(f"message_id: {message_id}")
    logger.info(f"response_id: {response_id}")
    logger.info(f"response_content: {response_content}")
    logger.info(f"author_username: {author_username}")
    logger.info(f"created_at: {created_at}")
    logger.info(f"channel_id: {channel_id}")
    logger.info("=========================================")
    
    try:
        # Connect to Neo4j
        with session_manager.driver.get_session() as db_session:
            # Create query to add the bot response message and connect it to the session and original message
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
            RETURN new_msg.message_id, m.message_id, s.id
            """
            
            # Sanitize the query parameters
            query_params = sanitize_neo4j_values({
                "session_id": session_id,
                "message_id": message_id,
                "response_id": response_id,
                "response_content": response_content,
                "author_username": author_username,
                "created_at": created_at,
                "channel_id": channel_id
            })
            
            logger.info(f"Executing query to create message node for response {response_id} in session {session_id}")
            logger.info(f"Cypher query: {create_query}")
            logger.info(f"Query parameters: {json.dumps(query_params, indent=2)}")
            
            # Execute the query
            result = db_session.run(create_query, query_params)
            record = result.single()
            
            if record:
                logger.info(f"Successfully logged bot response {record['new_msg.message_id']} as reply to {record['m.message_id']} in session {record['s.id']}")
                return {
                    "message_id": record["new_msg.message_id"],
                    "original_message_id": record["m.message_id"],
                    "session_id": record["s.id"],
                    "status": "success"
                }
            else:
                logger.error(f"Failed to log followup message: No record returned")
                return {
                    "status": "failure",
                    "error": "No record returned from database"
                }
                
    except Exception as e:
        logger.error(f"Error in log_followup_session_message: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        } 