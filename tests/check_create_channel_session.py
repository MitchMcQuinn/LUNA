#!/usr/bin/env python
"""
Check the create_channel_session output format to properly reference the session_id.
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

def check_create_channel_session_output(session_id=None):
    """Check the create_channel_session output format."""
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
        
        # Parse session state
        if record["state"]:
            state = json.loads(record["state"])
            
            # Print data section with each output
            if 'data' in state and 'outputs' in state['data']:
                outputs = state['data']['outputs']
                
                # Looking specifically for create_channel_session output
                if 'create_channel_session' in outputs:
                    print("\n=== CREATE_CHANNEL_SESSION OUTPUT ===")
                    create_channel_output = outputs['create_channel_session']
                    print(json.dumps(create_channel_output, indent=2))
                    
                    # Check key paths that we need to reference
                    print("\n=== KEY PATHS FOR VARIABLE REFERENCES ===")
                    
                    # Check if it's an array
                    if isinstance(create_channel_output, list) and len(create_channel_output) > 0:
                        first_item = create_channel_output[0]
                        print("Array structure - use @{SESSION_ID}.create_channel_session[0]...")
                        
                        if 'response' in first_item:
                            print("\nResponse object found:")
                            print(json.dumps(first_item['response'], indent=2))
                            
                            if 'session_id' in first_item['response']:
                                print(f"\nSession ID path: @{{SESSION_ID}}.create_channel_session[0].response.session_id")
                                print(f"Value: {first_item['response']['session_id']}")
                    else:
                        print("Not an array structure - use @{SESSION_ID}.create_channel_session...")
                        if 'response' in create_channel_output:
                            print("\nResponse object found:")
                            print(json.dumps(create_channel_output['response'], indent=2))
                            
                            if 'session_id' in create_channel_output['response']:
                                print(f"\nSession ID path: @{{SESSION_ID}}.create_channel_session.response.session_id")
                                print(f"Value: {create_channel_output['response']['session_id']}")
                else:
                    print("No create_channel_session output found in this session")
                    
                    # List all available outputs for reference
                    print("\n=== ALL AVAILABLE OUTPUTS ===")
                    for key in outputs.keys():
                        print(f" - {key}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Check create_channel_session output format')
    parser.add_argument('--session', type=str, help='Session ID to check')
    args = parser.parse_args()
    
    check_create_channel_session_output(args.session)

if __name__ == "__main__":
    main() 