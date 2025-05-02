#!/usr/bin/env python
"""
Check database connections between Session and Message nodes for a specific session.
"""

import os
import sys
import json
import logging
import argparse
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

def check_session_message_connections(session_id=None):
    """Check connections between Session and Message nodes."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as db_session:
        print("\n=== CHECKING SESSION-MESSAGE CONNECTIONS ===")
        
        if session_id:
            # Check all messages and connections for the specific session
            print(f"Checking connections for session: {session_id}")
            
            # 1. Check SESSION node
            result = db_session.run("""
                MATCH (s:SESSION {id: $id})
                RETURN s.id as id, s.created_at as created_at
            """, id=session_id)
            
            record = result.single()
            if not record:
                print(f"No session found with ID: {session_id}")
                return
                
            print(f"Found session: {record['id']} (created: {record['created_at']})")
            
            # 2. Check MESSAGE nodes
            result = db_session.run("""
                MATCH (m:MESSAGE {session_id: $id})
                RETURN m.message_id as message_id, m.content as content, m.created_at as created_at
                ORDER BY m.created_at
            """, id=session_id)
            
            messages = list(result)
            print(f"\nFound {len(messages)} messages for this session:")
            for message in messages:
                print(f"  - Message ID: {message['message_id']}")
                print(f"    Content: {message['content']}")
                print(f"    Created: {message['created_at']}")
                
            # 3. Check SESSION-MESSAGE relationships
            result = db_session.run("""
                MATCH (s:SESSION {id: $id})-[r:HAS_MESSAGE]->(m:MESSAGE)
                RETURN s.id as session_id, m.message_id as message_id, type(r) as relationship
            """, id=session_id)
            
            relationships = list(result)
            print(f"\nFound {len(relationships)} SESSION-MESSAGE relationships:")
            for rel in relationships:
                print(f"  - Session {rel['session_id']} --[{rel['relationship']}]--> Message {rel['message_id']}")
            
            # 4. Check for disconnected messages (messages for this session without relationship)
            result = db_session.run("""
                MATCH (m:MESSAGE {session_id: $id})
                WHERE NOT (:SESSION)-[:HAS_MESSAGE]->(m)
                RETURN m.message_id as message_id, m.content as content
            """, id=session_id)
            
            disconnected = list(result)
            if disconnected:
                print(f"\nFound {len(disconnected)} DISCONNECTED messages (no HAS_MESSAGE relationship):")
                for message in disconnected:
                    print(f"  - Message ID: {message['message_id']}")
                    print(f"    Content: {message['content']}")
            else:
                print("\nNo disconnected messages found - all messages have proper relationships")
                
            # 5. Check for the specific response_id mentioned in the logs
            # Get response_id from session state
            result = db_session.run("""
                MATCH (s:SESSION {id: $id})
                RETURN s.state as state
            """, id=session_id)
            
            record = result.single()
            if record and record["state"]:
                state = json.loads(record["state"])
                if "outputs" in state.get("data", {}) and "send_session_followup_message" in state["data"]["outputs"]:
                    followup_output = state["data"]["outputs"]["send_session_followup_message"][0]
                    if "result" in followup_output and "response" in followup_output["result"]:
                        response_id = followup_output["result"]["response"]["id"]
                        print(f"\nChecking for bot response message with ID: {response_id}")
                        
                        # Check if this message exists in the graph
                        result = db_session.run("""
                            MATCH (m:MESSAGE {message_id: $id})
                            RETURN m.message_id as message_id, m.content as content, m.session_id as session_id
                        """, id=response_id)
                        
                        record = result.single()
                        if record:
                            print(f"Found bot response message in graph database:")
                            print(f"  - Message ID: {record['message_id']}")
                            print(f"  - Content: {record['content']}")
                            print(f"  - Session ID: {record['session_id']}")
                            
                            # Check if properly connected to session
                            result = db_session.run("""
                                MATCH (s:SESSION)-[:HAS_MESSAGE]->(m:MESSAGE {message_id: $id})
                                RETURN s.id as session_id
                            """, id=response_id)
                            
                            if result.single():
                                print("  ✓ Message is properly connected to session")
                            else:
                                print("  ✗ Message exists but NOT connected to any session")
                        else:
                            print(f"✗ Bot response message NOT found in graph database")
                            
                            # Suggest fix for the missing message
                            print("\nSuggested Cypher query to add the missing message:")
                            response_data = followup_output["result"]["response"]
                            print(f"""
CREATE (m:MESSAGE {{
    message_id: '{response_id}',
    session_id: '{session_id}',
    content: '{response_data.get("content", "")}',
    created_at: '{response_data.get("timestamp", "")}'
}})
WITH m
MATCH (s:SESSION {{id: '{session_id}'}})
CREATE (s)-[:HAS_MESSAGE]->(m)
RETURN m.message_id, s.id
                            """)
        else:
            # List messages across all sessions
            result = db_session.run("""
                MATCH (m:MESSAGE)
                RETURN m.message_id as message_id, m.session_id as session_id, m.content as content
                LIMIT 25
            """)
            
            messages = list(result)
            print(f"Found {len(messages)} messages (showing up to 25):")
            for message in messages:
                print(f"  - Message: {message['message_id']}")
                print(f"    Session: {message['session_id']}")
                print(f"    Content: {message['content']}")
                print()
            
            print("\nTo check a specific session, run: python check_db_connections.py --session SESSION_ID")

def main():
    parser = argparse.ArgumentParser(description='Check Neo4j database connections')
    parser.add_argument('--session', type=str, help='Session ID to check')
    args = parser.parse_args()
    
    check_session_message_connections(args.session)

if __name__ == "__main__":
    main() 