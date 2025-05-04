from core.session_manager import get_session_manager
from utils.code import sanitize_neo4j_values
import logging
import json
import sys

def main():
    """
    Delete a session from the Neo4j database by finding and removing the SESSION node
    and all its connected MESSAGE nodes.
    
    The session ID is injected by the code utility through the variables parameter.
    Required variables:
    - session_id: The ID of the session to delete
    """
    logger = logging.getLogger(__name__)
    
    # Get session manager for database access
    session_manager = get_session_manager()
    
    # Detailed debugging of local and global variables
    logger.info("=== SCRIPT EXECUTION ENVIRONMENT ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Script name: {__name__}")
    
    # Check if required variables exist in the global scope
    required_vars = ["session_id"]
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
    logger.info("=== DELETE_SESSION INPUTS ===")
    logger.info(f"session_id: {session_id} (type: {type(session_id).__name__})")
    logger.info("======================================")
    
    # If session_id is in format "session_id:ABC123", extract just the ID part
    actual_session_id = session_id
    if isinstance(session_id, str) and "session_id:" in session_id:
        actual_session_id = session_id.split("session_id:", 1)[1].strip()
        logger.info(f"Extracted session ID from input: {actual_session_id}")
    
    # Validate variable contents
    logger.info("=== VARIABLE CONTENT VALIDATION ===")
    is_valid = True
    
    if not actual_session_id or not isinstance(actual_session_id, str):
        logger.error(f"Invalid session_id: {actual_session_id}")
        is_valid = False
    
    if not is_valid:
        error_msg = "One or more variables have invalid values"
        logger.error(error_msg)
        return [{"status": "error", "error": error_msg}]
    
    try:
        # First get info about the session to return in the result
        info_query = """
        MATCH (s:SESSION {id: $session_id})
        OPTIONAL MATCH (s)-[:HAS_MESSAGE]->(m:MESSAGE)
        RETURN s.id AS session_id, count(m) AS message_count
        """
        
        # Create a query to delete the session and all connected messages
        delete_query = """
        MATCH (s:SESSION {id: $session_id})
        OPTIONAL MATCH (s)-[:HAS_MESSAGE]->(m:MESSAGE)
        DETACH DELETE s, m
        RETURN count(*) as nodes_deleted
        """
        
        logger.info(f"Executing query to get info about session {actual_session_id}")
        logger.info(f"Info query: {info_query}")
        
        # Sanitize the parameters to ensure they're safe for Neo4j
        params = sanitize_neo4j_values({
            "session_id": actual_session_id
        })
        
        logger.info(f"Query parameters: {json.dumps(params, indent=2)}")
        
        # Execute the info query first
        with session_manager.driver.get_session() as db_session:
            logger.info("Obtained Neo4j database session")
            info_result = db_session.run(info_query, params)
            logger.info("Info query executed successfully")
            info_record = info_result.single()
            
            if not info_record:
                logger.warning(f"Session {actual_session_id} not found in database")
                return [{
                    "session_id": actual_session_id,
                    "status": "warning",
                    "message": "Session not found",
                    "nodes_deleted": 0
                }]
            
            message_count = info_record["message_count"]
            
            # Now execute the delete query
            logger.info(f"Executing query to delete session {actual_session_id} and its {message_count} messages")
            logger.info(f"Delete query: {delete_query}")
            
            delete_result = db_session.run(delete_query, params)
            logger.info("Delete query executed successfully")
            delete_record = delete_result.single()
            
            if delete_record:
                nodes_deleted = delete_record["nodes_deleted"]
                logger.info(f"Successfully deleted session {actual_session_id} with {nodes_deleted} nodes removed")
                success_result = {
                    "session_id": actual_session_id,
                    "status": "success",
                    "message": f"Session deleted with {message_count} associated messages",
                    "nodes_deleted": nodes_deleted,
                    "message_count": message_count
                }
                logger.info(f"Returning result: {json.dumps(success_result, indent=2)}")
                return [success_result]
            else:
                error_msg = f"Failed to delete session {actual_session_id} - no confirmation returned"
                logger.error(error_msg)
                error_result = {
                    "session_id": actual_session_id,
                    "status": "error",
                    "error": "No confirmation returned from database",
                    "nodes_deleted": 0
                }
                logger.info(f"Returning error result: {json.dumps(error_result, indent=2)}")
                return [error_result]
                
    except Exception as e:
        error_msg = f"Error in delete_session: {str(e)}"
        logger.error(error_msg)
        logger.exception("Full exception details:")
        error_result = {
            "session_id": actual_session_id if 'actual_session_id' in locals() else session_id if 'session_id' in globals() else "UNKNOWN",
            "status": "error",
            "error": str(e),
            "nodes_deleted": 0
        }
        logger.info(f"Returning exception result: {json.dumps(error_result, indent=2)}")
        return [error_result]

# Set the result for the workflow
logger = logging.getLogger(__name__)
logger.info("=== STARTING DELETE_SESSION SCRIPT ===")
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
- Session ID: @{SESSION_ID}.step_id[0].session_id
- Status: @{SESSION_ID}.step_id[0].status ('success', 'warning', or 'error')
- Message: @{SESSION_ID}.step_id[0].message (success message)
- Error (if any): @{SESSION_ID}.step_id[0].error
- Nodes deleted: @{SESSION_ID}.step_id[0].nodes_deleted
- Message count: @{SESSION_ID}.step_id[0].message_count

Note that this script returns an array with a single element, so indexing [0] is required.

Examples:
- @{SESSION_ID}.delete_session[0].status (status of operation - 'success', 'warning', or 'error')
- @{SESSION_ID}.delete_session[0].message (success message)
- @{SESSION_ID}.delete_session[0].nodes_deleted (count of nodes deleted)

Expected Configuration Format:
When configuring this script in a workflow step, provide the following input parameters:
{
  "function": "utils.code.code",
  "file_path": "delete_session.py",
  "variables": {
    "session_id": "@{SESSION_ID}.data.session_id" // Use the session ID from the current workflow session
  }
}

Alternative configurations:
{
  "function": "utils.code.code",
  "file_path": "delete_session.py",
  "variables": {
    "session_id": "@{SESSION_ID}.create_channel_session[0].response.session_id" // Use the nested session ID
  }
}

Or to use the current session ID:
{
  "function": "utils.code.code",
  "file_path": "delete_session.py",
  "variables": {
    "session_id": "@{SESSION_ID}" // Use the current session ID directly
  }
}
"""
