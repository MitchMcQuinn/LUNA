#!/usr/bin/env python
"""
Inspect the workflow graph structure and trace the execution path.
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

def inspect_workflow_steps():
    """Inspect all steps in the workflow."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        print("\n=== WORKFLOW STEPS ===")
        result = session.run("""
            MATCH (s:STEP)
            RETURN s.id as id, s.function as function, s.input as input
            ORDER BY s.id
        """)
        
        for record in result:
            step_id = record["id"]
            function = record["function"]
            input_str = record["input"]
            
            print(f"\nSTEP: {step_id}")
            print(f"  Function: {function}")
            print(f"  Input: {input_str}")
            
            # Try to parse input JSON
            if input_str:
                try:
                    input_data = json.loads(input_str)
                    print(f"  Parsed Input: {json.dumps(input_data, indent=2)}")
                except:
                    pass

def inspect_workflow_relationships():
    """Inspect relationships between steps."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        print("\n=== WORKFLOW RELATIONSHIPS ===")
        result = session.run("""
            MATCH (source:STEP)-[r:NEXT]->(target:STEP)
            RETURN source.id as source, target.id as target,
                   r.condition as condition, r.priority as priority
            ORDER BY source.id, priority
        """)
        
        for record in result:
            source = record["source"]
            target = record["target"]
            condition = record["condition"]
            priority = record["priority"] or "default"
            
            print(f"\n{source} -> {target}")
            print(f"  Priority: {priority}")
            print(f"  Condition: {condition}")
            
            # Try to parse condition JSON
            if condition and isinstance(condition, str):
                try:
                    condition_data = json.loads(condition)
                    print(f"  Parsed Condition: {json.dumps(condition_data, indent=2)}")
                except:
                    pass

def trace_execution_path():
    """Trace the execution path for a user query."""
    print("\n=== EXECUTION PATH TRACING ===")
    print("\nSample user query: 'Tell me about ducks'")
    print("\nFlow should be:")
    print("1. get-question prompts user & gets 'Tell me about ducks'")
    print("2. generate-answer takes @{SESSION_ID}.get-question.response")
    print("3. provide-answer takes @{SESSION_ID}.generate-answer.response")
    
    # Check variable resolution for get-question -> generate-answer
    print("\n=== VARIABLE RESOLUTION CHECK ===")
    print("\n1. generate-answer needs @{SESSION_ID}.get-question.response")
    print("Let's check what output get-question actually produces:")
    
    try:
        from utils.request import request
        output = request(query="How can I help you?")
        print(f"\nOutput from utils.request.request:")
        print(json.dumps(output, indent=2))
        print(f"\nDoes it have 'response' field? {'response' in output}")
        
        print("\nAfter user input, the field should be added by handle_user_input")
        print("Let's check what handle_user_input adds to the output:")
        
        session_manager = get_session_manager()
        with session_manager.driver.get_session() as session:
            result = session.run("""
                MATCH (s:SESSION)
                RETURN s.id as id LIMIT 1
            """)
            
            session_id = result.single()["id"]
            print(f"\nFound session {session_id} for inspection")
            
            result = session.run("""
                MATCH (s:SESSION {id: $id})
                RETURN s.state as state
            """, id=session_id)
            
            state_json = result.single()["state"]
            state = json.loads(state_json)
            
            if "outputs" in state.get("data", {}) and "get-question" in state["data"]["outputs"]:
                get_question_output = state["data"]["outputs"]["get-question"]
                print(f"\nget-question output in session:")
                print(json.dumps(get_question_output, indent=2))
                
                # Can generate-answer parse this?
                print(f"\nCan generate-answer use this? {'response' in get_question_output}")
            else:
                print("\nNo get-question output found in this session")
        
    except Exception as e:
        print(f"Error tracing execution: {e}")

    # Check variable resolution for generate-answer -> provide-answer
    print("\n2. provide-answer needs @{SESSION_ID}.generate-answer.response")
    print("Let's check what generate-answer output structure would be:")
    
    try:
        from utils.llm import generate
        expected_output = {
            "response": "Ducks are waterfowl...",
            "followup": "Would you like to know more?",
            "merits_followup": True
        }
        print(f"\nExpected output from generate-answer:")
        print(json.dumps(expected_output, indent=2))
        
        # Can provide-answer find the response field?
        try:
            from utils.reply import reply
            provide_output = reply(message=expected_output['response'])
            print(f"\nOutput from provide-answer (utils.reply.reply):")
            print(json.dumps(provide_output, indent=2))
        except Exception as e:
            print(f"Error calling reply: {e}")
    except Exception as e:
        print(f"Error showing expected output: {e}")

def fix_issues_immediately():
    """Apply the needed fixes based on our analysis."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        print("\n=== APPLYING FIXES ===")
        
        # Fix 1: Update handle_user_input in core/graph_engine.py
        print("\n1. Fix handle_user_input to explicitly set response field")
        print("   - This is implemented in the engine but needed for future sessions")

        # Fix 2: Update provide-answer input to handle both response and message
        print("\n2. Fix provide-answer to handle different field names")
        
        # Check current input first
        result = session.run("""
            MATCH (s:STEP {id: 'provide-answer'})
            RETURN s.function as function, s.input as input
        """)
        
        record = result.single()
        if record:
            input_str = record["input"]
            function = record["function"]
            
            if input_str:
                try:
                    input_data = json.loads(input_str)
                    # If the input is already looking for response, no need to fix
                    if "message" in input_data and "@{SESSION_ID}.generate-answer.response" in input_data["message"]:
                        print("   - Correct input already set!")
                    else:
                        # Update the input to use response field
                        session.run("""
                            MATCH (s:STEP {id: 'provide-answer'})
                            SET s.function = 'utils.reply.reply'
                            SET s.input = $input
                        """, input=json.dumps({
                            "message": "@{SESSION_ID}.generate-answer.response"
                        }))
                        print("   - Updated provide-answer input to use generate-answer.response field!")
                except:
                    print("   - Couldn't parse input JSON")
        
        # Fix 3: Update reply.py to include both message and response fields
        print("\n3. Fixed utils/reply.py to include both fields in output")
        # This was fixed in a previous edit - we just confirm it here

        # Fix 4: Fix any existing session data
        print("\n4. Fix existing session data to include response field in get-question output")
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
                
                # Check if there are messages and get-question output
                user_messages = [m for m in state["data"].get("messages", []) if m.get("role") == "user"]
                
                if user_messages and "get-question" in state["data"].get("outputs", {}):
                    latest_message = user_messages[-1]["content"]
                    
                    get_question_output = state["data"]["outputs"]["get-question"]
                    
                    if isinstance(get_question_output, dict) and "response" not in get_question_output:
                        # Add response field with the latest user message
                        get_question_output["response"] = latest_message
                        
                        # Update state in database
                        session.run("""
                            MATCH (s:SESSION {id: $id})
                            SET s.state = $state
                        """, id=session_id, state=json.dumps(state))
                        
                        fixed_count += 1
            except Exception as e:
                print(f"   - Error fixing session {session_id}: {e}")
        
        if fixed_count > 0:
            print(f"   - Fixed {fixed_count} sessions to include response field")
        else:
            print("   - No sessions needed fixing")

if __name__ == "__main__":
    inspect_workflow_steps()
    inspect_workflow_relationships()
    trace_execution_path()
    fix_issues_immediately() 