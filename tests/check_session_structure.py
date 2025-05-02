#!/usr/bin/env python
"""
Check session structure and print out key values needed for workflow steps.
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set up paths
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
os.chdir(parent_dir)

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

def check_session_structure(session_id=None):
    """Check the structure of a session and print out key values."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as db_session:
        # If no specific session ID is provided, get the most recent session
        if not session_id:
            result = db_session.run("""
                MATCH (s:SESSION)
                RETURN s.id as id
                ORDER BY s.created_at DESC
                LIMIT 1
            """)
            
            record = result.single()
            if record:
                session_id = record["id"]
                logger.info(f"Using most recent session: {session_id}")
            else:
                logger.error("No sessions found in the database")
                return
        
        # Get the full session state
        result = db_session.run("""
            MATCH (s:SESSION {id: $id})
            RETURN s.id as id, s.state as state, s.created_at as created_at
        """, id=session_id)
        
        record = result.single()
        if not record:
            logger.error(f"No session found with ID: {session_id}")
            return
        
        # Print session details
        print("\n=== SESSION DETAILS ===")
        print(f"Session ID: {record['id']}")
        print(f"Created At: {record['created_at']}")
        
        # Parse and print session state
        if record["state"]:
            state = json.loads(record["state"])
            print("\n=== SESSION STATE ===")
            print(f"ID: {state.get('id')}")
            print(f"Workflow ID: {state.get('workflow_id')}")
            
            # Print data section with each output
            if 'data' in state and 'outputs' in state['data']:
                print("\n=== WORKFLOW OUTPUTS ===")
                for key, value in state['data']['outputs'].items():
                    print(f"\n-- {key} --")
                    print(json.dumps(value, indent=2))
            
            # Check useful variables for our workflow steps
            print("\n=== IMPORTANT VARIABLES FOR WORKFLOW STEPS ===")
            print(f"Session ID: {state.get('id')}")
            
            try:
                print(f"Message ID: {state['data']['outputs']['message']['id']}")
            except (KeyError, TypeError):
                print("Message ID: Not found in expected path")
            
            try:
                print(f"Content: {state['data']['outputs']['message']['content']}")
            except (KeyError, TypeError):
                print("Content: Not found in expected path")
            
            try:
                print(f"Author Username: {state['data']['outputs']['author']['username']}")
            except (KeyError, TypeError):
                print("Author Username: Not found in expected path")
            
            try:
                print(f"Created At: {state['data']['outputs']['message']['createdAt']}")
            except (KeyError, TypeError):
                print("Created At: Not found in expected path")
            
            try:
                print(f"Channel ID: {state['data']['outputs']['channel_id']}")
            except (KeyError, TypeError):
                print("Channel ID: Not found in expected path")
            
            try:
                print(f"Guild ID: {state['data']['outputs']['guild']['id']}")
            except (KeyError, TypeError):
                print("Guild ID: Not found in expected path")
            
            # Check values needed for lookup_followup_session_id
            print("\n=== REFERENCE MESSAGE VARIABLES (FOR REPLIES) ===")
            try:
                print(f"Reference Message ID: {state['data']['outputs']['message']['reference']['messageId']}")
            except (KeyError, TypeError):
                print("Reference Message ID: Not found or this message is not a reply")
        
        # Check for messages connected to this session
        result = db_session.run("""
            MATCH (s:SESSION {id: $id})-[:HAS_MESSAGE]->(m:MESSAGE)
            RETURN m.message_id as message_id, m.content as content
        """, id=session_id)
        
        messages = list(result)
        print(f"\n=== CONNECTED MESSAGES ({len(messages)}) ===")
        for msg in messages:
            print(f"Message ID: {msg['message_id']}")
            print(f"Content: {msg['content']}")
            print()

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Check session structure')
    parser.add_argument('--session', type=str, help='Session ID to check')
    args = parser.parse_args()
    
    check_session_structure(args.session)

if __name__ == "__main__":
    main() 