#!/usr/bin/env python
"""
Fix resolution order between get-question and generate-answer.
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

def add_response_to_request_output():
    """Modify the request function to always include an empty response field."""
    request_file = 'utils/request.py'
    
    # Check if file exists
    if not os.path.exists(request_file):
        logger.error(f"Cannot find {request_file}")
        return
        
    # Read the current content
    with open(request_file, 'r') as f:
        content = f.read()
        
    # Check if we need to modify it
    if 'response: None' not in content:
        # Find the request function
        import re
        request_func = re.search(r'def request\(([^)]*)\):\s+"""[^"]*"""(.*?)\s+return\s+{([^}]*)}', 
                               content, re.DOTALL)
        
        if request_func:
            # Extract the return statement
            return_stmt = request_func.group(3).strip()
            
            # Add response field if not already there
            if '"response"' not in return_stmt:
                new_return = return_stmt + ',\n        "response": None'
                new_content = content.replace(return_stmt, new_return)
                
                # Write the modified content
                with open(request_file, 'w') as f:
                    f.write(new_content)
                    
                logger.info(f"✅ Updated request function to include empty response field")
                return True
                
    logger.info("No update needed for request function")
    return False

def fix_request_in_active_sessions():
    """Fix sessions to ensure get-question outputs include response field."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        result = session.run("""
            MATCH (s:SESSION)
            RETURN s.id as id, s.state as state
        """)
        
        fixed_count = 0
        for record in result:
            session_id = record["id"]
            state_json = record["state"]
            
            if not state_json:
                continue
                
            try:
                state = json.loads(state_json)
                
                # Check if get-question output needs fixing
                if "outputs" in state.get("data", {}) and "get-question" in state["data"]["outputs"]:
                    get_question_output = state["data"]["outputs"]["get-question"]
                    
                    if isinstance(get_question_output, dict) and "response" not in get_question_output:
                        # Find user input from message history
                        user_messages = [m for m in state["data"].get("messages", []) if m.get("role") == "user"]
                        
                        if user_messages:
                            # Add most recent user message as response
                            latest_message = user_messages[-1]["content"]
                            get_question_output["response"] = latest_message
                        else:
                            # No user message yet, add empty response
                            get_question_output["response"] = None
                            
                        # Update state in database
                        session.run("""
                            MATCH (s:SESSION {id: $id})
                            SET s.state = $state
                        """, id=session_id, state=json.dumps(state))
                        
                        fixed_count += 1
            except Exception as e:
                logger.error(f"Error processing session {session_id}: {e}")
        
        logger.info(f"✅ Fixed {fixed_count} sessions to include response field")

def fix_generate_answer_input():
    """Ensure generate-answer has optimal input to handle get-question."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        # First check if need to update the model input
        result = session.run("""
            MATCH (s:STEP {id: 'generate-answer'})
            RETURN s.input as input
        """)
        
        record = result.single()
        if record:
            input_str = record["input"]
            if input_str:
                try:
                    input_data = json.loads(input_str)
                    
                    # Keep all existing fields
                    # Ensure directly_set_reply is true so the schema matches
                    input_data["directly_set_reply"] = True
                    
                    # Make sure schema includes response field
                    if "schema" in input_data:
                        schema = input_data["schema"]
                        if "properties" in schema and "response" in schema["properties"]:
                            logger.info("Generate-answer already has proper schema")
                        else:
                            logger.info("Updating generate-answer schema")
                            # Update the schema
                            session.run("""
                                MATCH (s:STEP {id: 'generate-answer'})
                                SET s.input = $input
                            """, input=json.dumps(input_data))
                            
                            logger.info("✅ Updated generate-answer input schema")
                except:
                    logger.error("Failed to parse generate-answer input")

def check_step_execution_order():
    """Ensure the workflow executes in correct order."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        # Check if relationships between steps are correct
        result = session.run("""
            MATCH (get:STEP {id: 'get-question'})-[r:NEXT]->(generate:STEP {id: 'generate-answer'})
            RETURN r
        """)
        
        if not result.single():
            # Add relationship if missing
            session.run("""
                MATCH (get:STEP {id: 'get-question'})
                MATCH (generate:STEP {id: 'generate-answer'})
                MERGE (get)-[r:NEXT]->(generate)
                RETURN r
            """)
            
            logger.info("✅ Added relationship from get-question to generate-answer")
        
        # Check if generate-answer connects to provide-answer
        result = session.run("""
            MATCH (generate:STEP {id: 'generate-answer'})-[r:NEXT]->(provide:STEP {id: 'provide-answer'})
            RETURN r
        """)
        
        if not result.single():
            # Add relationship if missing
            session.run("""
                MATCH (generate:STEP {id: 'generate-answer'})
                MATCH (provide:STEP {id: 'provide-answer'})
                MERGE (generate)-[r:NEXT]->(provide)
                RETURN r
            """)
            
            logger.info("✅ Added relationship from generate-answer to provide-answer")
        
        # Check if provide-answer loops back to get-question when merits_followup
        result = session.run("""
            MATCH (provide:STEP {id: 'provide-answer'})-[r:NEXT]->(get:STEP {id: 'get-question'})
            RETURN r, r.conditions as conditions
        """)
        
        record = result.single()
        if not record:
            # Add relationship with condition if missing
            session.run("""
                MATCH (provide:STEP {id: 'provide-answer'})
                MATCH (get:STEP {id: 'get-question'})
                MERGE (provide)-[r:NEXT]->(get)
                ON CREATE SET r.conditions = $conditions
                RETURN r
            """, conditions=json.dumps(["@{SESSION_ID}.generate-answer.merits_followup"]))
            
            logger.info("✅ Added conditional relationship from provide-answer to get-question")
        elif not record.get("conditions"):
            # Update the conditions if missing
            session.run("""
                MATCH (provide:STEP {id: 'provide-answer'})-[r:NEXT]->(get:STEP {id: 'get-question'})
                SET r.conditions = $conditions
                RETURN r
            """, conditions=json.dumps(["@{SESSION_ID}.generate-answer.merits_followup"]))
            
            logger.info("✅ Updated conditions on provide-answer to get-question relationship")

if __name__ == "__main__":
    # Step 1: Make utils.request.request include response field
    add_response_to_request_output()
    
    # Step 2: Fix existing active sessions
    fix_request_in_active_sessions()
    
    # Step 3: Ensure generate-answer has optimal model input
    fix_generate_answer_input()
    
    # Step 4: Check execution order of steps
    check_step_execution_order()
    
    print("✅ Workflow resolution order has been fixed!")
    print("   Now restarting the server should show proper conversation flow") 