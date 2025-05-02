#!/usr/bin/env python
"""
Check the format of messages in the session output to determine the correct path references.
"""

import os
import sys
import json
import logging
from pathlib import Path
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

def main():
    """Main function to check message format"""
    try:
        from core.session_manager import get_session_manager
        sm = get_session_manager()
        
        with sm.driver.get_session() as session:
            # First, get a list of recent sessions
            result = session.run("""
                MATCH (s:SESSION)
                RETURN s.id as session_id
                ORDER BY s.created_at DESC
                LIMIT 5
            """)
            
            sessions = list(result)
            if sessions:
                logger.info(f"Found {len(sessions)} recent sessions")
                for i, s in enumerate(sessions):
                    logger.info(f"{i+1}. Session ID: {s['session_id']}")
                
                # Use the latest session for testing output format
                latest_session_id = sessions[0]['session_id']
                
                # Examine the step execution for this session
                result = session.run("""
                    MATCH (s:SESSION {id: $session_id})-[:HAS_STEP_EXECUTION]->(e)
                    MATCH (e)-[:FOR_STEP]->(step)
                    WHERE step.id IN ['send_followup_channel_session_message', 'lookup_channel_session']
                    RETURN step.id as step_id, e.status as status, e.output as output
                    ORDER BY e.started_at DESC
                """, {"session_id": latest_session_id})
                
                executions = list(result)
                logger.info(f"\nFound {len(executions)} relevant step executions for session {latest_session_id}:")
                
                for execution in executions:
                    step_id = execution['step_id']
                    status = execution['status']
                    output = execution['output']
                    
                    logger.info(f"\nStep: {step_id}")
                    logger.info(f"Status: {status}")
                    
                    if output:
                        try:
                            # Try to parse as JSON if it's a string
                            if isinstance(output, str):
                                output_data = json.loads(output)
                            else:
                                output_data = output
                                
                            # Pretty print the output
                            output_json = json.dumps(output_data, indent=2)
                            logger.info(f"Output:\n{output_json}")
                            
                            # If this is the send_followup_channel_session_message step, 
                            # examine the message structure specifically
                            if step_id == 'send_followup_channel_session_message':
                                if isinstance(output_data, list) and len(output_data) > 0:
                                    response = output_data[0].get('response', {})
                                    
                                    # Check for messages array
                                    messages = response.get('messages', [])
                                    logger.info(f"\nMessages structure (count={len(messages)}):")
                                    
                                    for i, msg in enumerate(messages):
                                        msg_id = msg.get('_message_id', msg.get('_prompt_id', 'unknown'))
                                        role = msg.get('role', 'unknown')
                                        content_preview = msg.get('content', '')[:50] + ('...' if len(msg.get('content', '')) > 50 else '')
                                        
                                        logger.info(f"Message {i}: ID={msg_id}, Role={role}, Content={content_preview}")
                                        
                                    # Check response structure for id field
                                    if 'id' in response:
                                        logger.info(f"\nResponse has direct 'id' field: {response['id']}")
                                    
                                    # Last message should be the bot response
                                    if messages and messages[-1]['role'] == 'assistant':
                                        last_msg = messages[-1]
                                        logger.info(f"\nLast message (assistant): ID={last_msg.get('_message_id', 'unknown')}")
                                        
                                        # Check if _message_id exists and what format it's in
                                        if '_message_id' in last_msg:
                                            logger.info(f"  Format of _message_id: {type(last_msg['_message_id']).__name__}")
                                    
                        except Exception as e:
                            logger.error(f"Error parsing output: {e}")
                            logger.info(f"Raw output: {output}")
            else:
                logger.warning("No sessions found")
                
    except Exception as e:
        logger.error(f"Error examining session data: {str(e)}")
        
if __name__ == "__main__":
    main() 