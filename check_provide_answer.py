"""
Check and update the provide-answer step configuration.
"""

import os
import sys
import logging
import json
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env.local')
load_dotenv(env_path)
logger.info(f"Loaded environment from: {env_path}")

# Import core components
from core.session_manager import get_session_manager

def check_provide_answer():
    """Check the provide-answer step configuration in the database."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        # First check the current input
        result = session.run("""
            MATCH (s:STEP {id: 'provide-answer'})
            RETURN s.input as input, s.function as function, s.utility as utility
        """)
        
        record = result.single()
        if record:
            print(f"Current provide-answer config:")
            
            input_data = record.get('input')
            function = record.get('function')
            utility = record.get('utility')
            
            print(f"Input: {input_data}")
            print(f"Function: {function}")
            print(f"Utility: {utility}")
            
            # Try to parse input as JSON
            if input_data:
                try:
                    parsed_input = json.loads(input_data)
                    print(f"Parsed input: {json.dumps(parsed_input, indent=2)}")
                except json.JSONDecodeError:
                    print(f"Could not parse input as JSON: {input_data}")

def update_provide_answer():
    """Update the provide-answer step to properly handle template responses."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        # Update the input to handle the template string
        result = session.run("""
            MATCH (s:STEP {id: 'provide-answer'})
            SET s.function = 'utils.reply.reply'
            SET s.input = $input
            RETURN s.id as id
        """, input=json.dumps({
            "message": "@{SESSION_ID}.generate-answer.response"
        }))
        
        record = result.single()
        if record:
            print(f"Updated provide-answer step: {record['id']}")
        else:
            print("Failed to update provide-answer step!")

if __name__ == "__main__":
    print("Checking provide-answer step...")
    check_provide_answer()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--update':
        print("\nUpdating provide-answer step...")
        update_provide_answer()
        
        print("\nVerifying updated configuration...")
        check_provide_answer() 