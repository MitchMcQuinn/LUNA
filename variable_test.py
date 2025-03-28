"""
Test script to debug variable resolution.
"""

import os
import json
import sys
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Use DEBUG level for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set up path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)  # Add current directory to path

# Load environment
env_path = os.path.join(script_dir, '.env.local')
load_dotenv(env_path)

# Import necessary components
from core.session_manager import get_session_manager
from core.variable_resolver import resolve_variable, resolve_inputs

def test_variable_resolution():
    """Test variable resolution with a simple session state"""
    # Create a test session state
    test_state = {
        "id": "test-session",
        "workflow": {
            "root": {"status": "complete"},
            "get-question": {"status": "complete"},
            "generate-answer": {"status": "active"}
        },
        "data": {
            "outputs": {
                "root": {},
                "get-question": {
                    "waiting_for_input": True,
                    "prompt": "How can I help you today?",
                    "options": None,
                    "response": "Tell me about the weather"
                }
            },
            "messages": []
        }
    }
    
    # Test inputs from generate-answer step
    test_inputs = {
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "system": "You are a helpful assistant...",
        "user": "@{test-session}.get-question.response",
        "include_history": True,
        "directly_set_reply": True,
        "schema": {
            "type": "object",
            "properties": {
                "response": {
                    "type": "string",
                    "description": "The main response to the user query"
                },
                "followup": {
                    "type": "string",
                    "description": "A follow-up question"
                },
                "merits_followup": {
                    "type": "boolean",
                    "description": "Whether to follow up"
                }
            },
            "required": ["response", "merits_followup"]
        }
    }
    
    # Resolve the user variable
    user_var_ref = "@{test-session}.get-question.response"
    resolved_user = resolve_variable(user_var_ref, test_state)
    print(f"\nResolved user variable:")
    print(f"  Reference: {user_var_ref}")
    print(f"  Result: {resolved_user}")
    
    # Resolve all inputs
    resolved = resolve_inputs(test_inputs, test_state)
    print(f"\nResolved inputs:")
    for key, value in resolved.items():
        if key == "schema":
            print(f"  {key}: [schema object]")
        elif key == "system":
            print(f"  {key}: {value[:30]}...")
        else:
            print(f"  {key}: {value}")
    
    # Try with the real session state from Neo4j
    try:
        session_manager = get_session_manager()
        session_id = session_manager.create_session()
        logger.info(f"Created session: {session_id}")
        
        # Create test output for get-question
        def update_state(current_state):
            current_state["data"]["outputs"]["get-question"] = {
                "waiting_for_input": True,
                "prompt": "How can I help you today?",
                "options": None,
                "response": "Tell me about the weather"
            }
            current_state["workflow"]["get-question"] = {"status": "complete"}
            return current_state
            
        session_manager.update_session_state(session_id, update_state)
        
        # Get updated state
        state = session_manager.get_session_state(session_id)
        
        # Test with actual input from the graph
        # Print the schema from Neo4j
        with session_manager.driver.get_session() as neo_session:
            result = neo_session.run(
                "MATCH (s:STEP {id: 'generate-answer'}) RETURN s.input as input"
            )
            record = result.single()
            if record and record["input"]:
                try:
                    input_data = json.loads(record["input"])
                    print("\nInput schema from Neo4j:")
                    for key, value in input_data.items():
                        if key == "schema":
                            print(f"  {key}: [schema object]")
                        elif key == "system":
                            print(f"  {key}: {str(value)[:30]}...")
                        else:
                            print(f"  {key}: {value}")
                            
                    # Replace SESSION_ID with actual session id
                    for key, value in input_data.items():
                        if isinstance(value, str) and "@{SESSION_ID}" in value:
                            input_data[key] = value.replace("@{SESSION_ID}", f"@{{{session_id}}}")
                    
                    # Resolve with actual session state        
                    resolved = resolve_inputs(input_data, state)
                    print("\nResolved Neo4j inputs with actual session state:")
                    for key, value in resolved.items():
                        if key == "schema":
                            print(f"  {key}: [schema object]")
                        elif key == "system":
                            print(f"  {key}: {str(value)[:30]}...")
                        else:
                            print(f"  {key}: {value}")
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON input: {e}")
                    print(f"Raw input: {record['input']}")
            else:
                print("No input found for generate-answer step")
    except Exception as e:
        logger.error(f"Error with Neo4j test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_variable_resolution() 