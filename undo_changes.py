#!/usr/bin/env python
"""
Undo changes to get-question step and implement a direct fix for the response issue.
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set up paths for import
script_dir = os.path.dirname(os.path.abspath(__file__))
luna_dir = os.path.join(script_dir, 'LUNA')
if os.path.exists(luna_dir):
    sys.path.append(luna_dir)
    os.chdir(luna_dir)
else:
    sys.path.append(script_dir)

# Load environment variables
env_path = os.path.join(os.getcwd(), '.env.local')
if os.path.exists(env_path):
    load_dotenv(env_path)
    logger.info(f"Loaded environment from: {env_path}")
else:
    logger.warning(f"No .env.local found at {env_path}")

# Import core components
try:
    from core.session_manager import get_session_manager
    logger.info("Successfully imported core components")
except ImportError as e:
    logger.error(f"Failed to import components: {e}")
    sys.exit(1)

def restore_get_question_step():
    """Restore the get-question step to its original function."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        # Restore the get-question step back to the original function
        session.run("""
            MATCH (s:STEP {id: 'get-question'})
            SET s.function = 'utils.request.request'
        """)
        
        logger.info("✅ Restored get-question step to original request function")
        
def add_response_to_sessions():
    """Add response field to all active sessions' get-question outputs."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        # Get all active sessions
        result = session.run("""
            MATCH (s:SESSION)
            RETURN s.id as id, s.state as state
        """)
        
        for record in result:
            session_id = record["id"]
            state_json = record["state"]
            
            if not state_json:
                continue
                
            try:
                state = json.loads(state_json)
                
                # Check if there are messages and get-question output
                user_messages = [m for m in state["data"].get("messages", []) if m.get("role") == "user"]
                
                if user_messages and "get-question" in state["data"].get("outputs", {}):
                    latest_message = user_messages[-1]["content"]
                    
                    # Force update the output to include the response directly
                    state["data"]["outputs"]["get-question"] = {
                        "waiting_for_input": False,
                        "response": latest_message
                    }
                    
                    # Update state in database
                    session.run("""
                        MATCH (s:SESSION {id: $id})
                        SET s.state = $state
                    """, id=session_id, state=json.dumps(state))
                    
                    logger.info(f"✅ Fixed session {session_id}: Set get-question output directly")
            
            except Exception as e:
                logger.error(f"Error processing session {session_id}: {e}")

def fix_generate_step_condition():
    """Fix the condition that checks for get-question.response field."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        # Connect generate-answer step directly to get-question step if not already connected
        result = session.run("""
            MATCH (generate:STEP {id: 'generate-answer'})-[r:NEXT]->(provide:STEP {id: 'provide-answer'})
            RETURN r
        """)
        
        if not result.single():
            # Create the relationship
            session.run("""
                MATCH (generate:STEP {id: 'generate-answer'})
                MATCH (provide:STEP {id: 'provide-answer'})
                MERGE (generate)-[r:NEXT]->(provide)
                RETURN r
            """)
            
            logger.info("✅ Added relationship from generate-answer to provide-answer")
            
if __name__ == "__main__":
    # Step 1: Restore get-question step to original function
    restore_get_question_step()
    
    # Step 2: Fix session data directly
    add_response_to_sessions()
    
    # Step 3: Fix the graph connections
    fix_generate_step_condition()
    
    print("Done! You can now restart the server and test the chat interface.") 