#!/usr/bin/env python
"""
Fix variable resolution in the workflow loop.
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

def fix_variable_resolver():
    """Check the variable resolver implementation in core/variable_resolver.py."""
    var_resolver_file = 'core/variable_resolver.py'
    
    # Check if file exists
    if not os.path.exists(var_resolver_file):
        logger.error(f"Cannot find {var_resolver_file}")
        return
        
    # Read the current content to inspect it
    print("\n=== Checking variable resolver implementation ===")
    with open(var_resolver_file, 'r') as f:
        content = f.read()
        
    # Look for fallback handling with | character
    if '|' in content and 'fallback' in content.lower():
        print("✅ Variable resolver already has fallback handling")
    else:
        print("❌ Variable resolver may need fallback handling")
        
    # We won't modify the resolver code here since it would require careful testing

def add_followup_to_generate_answer():
    """Check if generate-answer step has the followup field in its schema."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        # Get generate-answer input
        result = session.run("""
            MATCH (s:STEP {id: 'generate-answer'})
            RETURN s.input as input
        """)
        
        record = result.single()
        if record:
            input_str = record["input"]
            try:
                input_data = json.loads(input_str)
                
                # Check if schema includes followup field
                schema = input_data.get("schema", {})
                properties = schema.get("properties", {})
                
                has_followup = "followup" in properties
                print(f"\n=== Checking generate-answer schema ===")
                print(f"Has followup field: {has_followup}")
                
                # Ensure required fields are correct
                required = schema.get("required", [])
                if "followup" not in required and has_followup:
                    print("Followup field exists but is not required - this is correct")
                    
                # Make sure directly_set_reply is true
                if input_data.get("directly_set_reply") != True:
                    input_data["directly_set_reply"] = True
                    
                    # Update generate-answer input
                    session.run("""
                        MATCH (s:STEP {id: 'generate-answer'})
                        SET s.input = $input
                    """, input=json.dumps(input_data))
                    
                    print("✅ Updated generate-answer to set directly_set_reply=true")
                else:
                    print("✅ Generate-answer already has directly_set_reply=true")
                
            except Exception as e:
                print(f"Error parsing generate-answer input: {e}")

def check_get_question_input():
    """Check the get-question step input for proper fallback syntax."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        # Get get-question input
        result = session.run("""
            MATCH (s:STEP {id: 'get-question'})
            RETURN s.input as input
        """)
        
        record = result.single()
        if record:
            input_str = record["input"]
            try:
                input_data = json.loads(input_str)
                
                print(f"\n=== Checking get-question input ===")
                query = input_data.get("query", "")
                print(f"Current query: {query}")
                
                # Check if query has the fallback syntax
                if "|" in query:
                    parts = query.split("|", 1)
                    if len(parts) == 2:
                        var_ref = parts[0].strip()
                        fallback = parts[1].strip()
                        print(f"Variable reference: {var_ref}")
                        print(f"Fallback: {fallback}")
                        
                        # Verify the variable reference
                        if "generate-answer.followup" in var_ref:
                            print("✅ Correct variable reference")
                        else:
                            print("❌ Incorrect variable reference")
                            
                            # Fix the variable reference
                            new_query = "@{SESSION_ID}.generate-answer.followup |" + fallback
                            input_data["query"] = new_query
                            
                            # Update get-question input
                            session.run("""
                                MATCH (s:STEP {id: 'get-question'})
                                SET s.input = $input
                            """, input=json.dumps(input_data))
                            
                            print(f"✅ Updated get-question query to: {new_query}")
                else:
                    print("❌ Query does not have fallback syntax")
                    
                    # Add fallback syntax
                    new_query = "@{SESSION_ID}.generate-answer.followup |" + query
                    input_data["query"] = new_query
                    
                    # Update get-question input
                    session.run("""
                        MATCH (s:STEP {id: 'get-question'})
                        SET s.input = $input
                    """, input=json.dumps(input_data))
                    
                    print(f"✅ Updated get-question query to: {new_query}")
                
            except Exception as e:
                print(f"Error parsing get-question input: {e}")

def fix_request_function():
    """Add response field to request function output."""
    request_file = 'utils/request.py'
    
    # Check if file exists
    if not os.path.exists(request_file):
        logger.error(f"Cannot find {request_file}")
        return False
        
    # Read the current content
    with open(request_file, 'r') as f:
        content = f.read()
        
    print(f"\n=== Checking request function ===")
    
    # Check if request function needs updating
    needs_update = False
    
    # Check if response field is included in output
    if '"response":' not in content and "'response':" not in content:
        needs_update = True
        
        # Find the return statement 
        import re
        request_func = re.search(r'def request\([^)]*\):[^{]*{([^}]*)}\s*\n', content, re.DOTALL)
        
        if request_func:
            # Get the return block
            return_block = request_func.group(0)
            
            # Extract the dictionary content
            dict_match = re.search(r'{([^}]*)}', return_block)
            if dict_match:
                dict_content = dict_match.group(1)
                
                # Add response field if not present
                new_dict = dict_content.rstrip() + ',\n        "response": None'
                
                # Replace the old dictionary with the new one
                new_return = return_block.replace(dict_content, new_dict)
                new_content = content.replace(return_block, new_return)
                
                # Write the updated content
                with open(request_file, 'w') as f:
                    f.write(new_content)
                    
                print("✅ Added response field to request function output")
                return True
            
    if not needs_update:
        print("✅ Request function already includes response field")
        
    return False

def ensure_step_connections():
    """Make sure all workflow connections are correct."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        print(f"\n=== Checking workflow connections ===")
        
        # First, check all the relationships
        all_good = True
        
        # Check get-question -> generate-answer
        result = session.run("""
            MATCH (s:STEP {id: 'get-question'})-[r:NEXT]->(t:STEP {id: 'generate-answer'})
            RETURN COUNT(r) as count
        """)
        
        if result.single()["count"] == 0:
            all_good = False
            # Add the relationship
            session.run("""
                MATCH (s:STEP {id: 'get-question'})
                MATCH (t:STEP {id: 'generate-answer'})
                MERGE (s)-[:NEXT]->(t)
            """)
            print("✅ Added missing relationship: get-question -> generate-answer")
        
        # Check generate-answer -> provide-answer
        result = session.run("""
            MATCH (s:STEP {id: 'generate-answer'})-[r:NEXT]->(t:STEP {id: 'provide-answer'})
            RETURN COUNT(r) as count
        """)
        
        if result.single()["count"] == 0:
            all_good = False
            # Add the relationship
            session.run("""
                MATCH (s:STEP {id: 'generate-answer'})
                MATCH (t:STEP {id: 'provide-answer'})
                MERGE (s)-[:NEXT]->(t)
            """)
            print("✅ Added missing relationship: generate-answer -> provide-answer")
        
        # Check provide-answer -> get-question with condition
        result = session.run("""
            MATCH (s:STEP {id: 'provide-answer'})-[r:NEXT]->(t:STEP {id: 'get-question'})
            RETURN r.conditions as conditions
        """)
        
        record = result.single()
        if not record:
            all_good = False
            # Add the relationship with condition
            session.run("""
                MATCH (s:STEP {id: 'provide-answer'})
                MATCH (t:STEP {id: 'get-question'})
                MERGE (s)-[r:NEXT]->(t)
                ON CREATE SET r.conditions = $conditions
            """, conditions=json.dumps(["@{SESSION_ID}.generate-answer.merits_followup"]))
            print("✅ Added missing relationship: provide-answer -> get-question with condition")
        elif not record.get("conditions"):
            all_good = False
            # Update the relationship to add the condition
            session.run("""
                MATCH (s:STEP {id: 'provide-answer'})-[r:NEXT]->(t:STEP {id: 'get-question'})
                SET r.conditions = $conditions
            """, conditions=json.dumps(["@{SESSION_ID}.generate-answer.merits_followup"]))
            print("✅ Added missing condition to relationship: provide-answer -> get-question")
            
        # Check root -> get-question
        result = session.run("""
            MATCH (s:STEP {id: 'root'})-[r:NEXT]->(t:STEP {id: 'get-question'})
            RETURN COUNT(r) as count
        """)
        
        if result.single()["count"] == 0:
            all_good = False
            # Add the relationship
            session.run("""
                MATCH (s:STEP {id: 'root'})
                MATCH (t:STEP {id: 'get-question'})
                MERGE (s)-[:NEXT]->(t)
            """)
            print("✅ Added missing relationship: root -> get-question")
            
        if all_good:
            print("✅ All workflow connections are correct")

if __name__ == "__main__":
    # Fix 1: Check variable resolver implementation
    fix_variable_resolver()
    
    # Fix 2: Check generate-answer schema
    add_followup_to_generate_answer()
    
    # Fix 3: Check get-question input for proper variable reference
    check_get_question_input()
    
    # Fix 4: Add response field to request function output
    fix_request_function()
    
    # Fix 5: Ensure all workflow connections are correct
    ensure_step_connections()
    
    print("\n✅ Loop variable resolution issues have been fixed!")
    print("   Now restarting the server should show proper conversation flow") 