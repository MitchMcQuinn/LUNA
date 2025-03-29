#!/usr/bin/env python
"""
Fix message handling in the workflow by updating the current session data.
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

def fix_session_data():
    """Fix the session data by copying user messages to get-question response field."""
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
                    
                    # Update get-question output to include response field
                    get_question_output = state["data"]["outputs"]["get-question"]
                    
                    if isinstance(get_question_output, dict) and "response" not in get_question_output:
                        # Add response field
                        get_question_output["response"] = latest_message
                        
                        # Update state in database
                        session.run("""
                            MATCH (s:SESSION {id: $id})
                            SET s.state = $state
                        """, id=session_id, state=json.dumps(state))
                        
                        logger.info(f"✅ Updated session {session_id}: Added response field to get-question output")
                    else:
                        logger.info(f"Session {session_id}: No update needed")
                
            except Exception as e:
                logger.error(f"Error processing session {session_id}: {e}")

def fix_get_question_step():
    """Update the get-question step to store response properly."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        # Check if the get-question step exists
        result = session.run("""
            MATCH (s:STEP {id: 'get-question'})
            RETURN s.function as function, s.input as input
        """)
        
        record = result.single()
        if record:
            # Update the get-question step's function
            # Make sure it properly captures and includes the response field
            session.run("""
                MATCH (s:STEP {id: 'get-question'})
                SET s.function = 'utils.request.request_with_response'
            """)
            
            logger.info("✅ Updated get-question step to use request_with_response function")

def add_request_with_response_function():
    """Add the request_with_response function if it doesn't exist."""
    # Create utils/request.py and add the request_with_response function
    os.makedirs('utils', exist_ok=True)
    request_file = os.path.join('utils', 'request.py')
    
    if not os.path.exists(request_file):
        with open(request_file, 'w') as f:
            f.write('''"""
Request utilities for workflow inputs.
"""

import logging

logger = logging.getLogger(__name__)

def request(query=None, options=None):
    """
    Request input from the user
    
    Args:
        query: The question to ask
        options: Optional list of preset options
        
    Returns:
        Request object
    """
    logger.info(f"Requesting input with prompt: {query}")
    
    return {
        "waiting_for_input": True,
        "prompt": query,
        "options": options
    }
    
def request_with_response(query=None, options=None, response=None):
    """
    Request input from the user, with response field
    
    Args:
        query: The question to ask
        options: Optional list of preset options
        response: Response from the user (when available)
        
    Returns:
        Request object with response field if available
    """
    result = {
        "waiting_for_input": True,
        "prompt": query,
        "options": options
    }
    
    # When a response is provided, include it
    if response:
        result["response"] = response
        logger.info(f"Request with response: {response}")
    
    return result
''')
        logger.info("✅ Created utils/request.py with request_with_response function")
    else:
        # Check if the file already has the function, if not append it
        with open(request_file, 'r') as f:
            content = f.read()
            
        if 'def request_with_response' not in content:
            with open(request_file, 'a') as f:
                f.write('''
def request_with_response(query=None, options=None, response=None):
    """
    Request input from the user, with response field
    
    Args:
        query: The question to ask
        options: Optional list of preset options
        response: Response from the user (when available)
        
    Returns:
        Request object with response field if available
    """
    result = {
        "waiting_for_input": True,
        "prompt": query,
        "options": options
    }
    
    # When a response is provided, include it
    if response:
        result["response"] = response
        logger.info(f"Request with response: {response}")
    
    return result
''')
            logger.info("✅ Added request_with_response function to utils/request.py")
        else:
            logger.info("request_with_response function already exists")

if __name__ == "__main__":
    # Step 1: Add the request_with_response function
    add_request_with_response_function()
    
    # Step 2: Update the get-question step to use this function
    fix_get_question_step()
    
    # Step 3: Fix existing session data
    fix_session_data()
    
    print("Done! You can now restart the server and test the chat interface.") 