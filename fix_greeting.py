"""
Fix the get-question step in the database.
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set up path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)  # Add current directory to path

# Load environment
env_path = os.path.join(script_dir, '.env.local')
load_dotenv(env_path)

# Import core components
from core.session_manager import get_session_manager

def fix_greeting():
    """Fix the get-question step to use a static greeting."""
    
    # Get database connection
    session_manager = get_session_manager()
    
    # Update the get-question step to use a static greeting
    with session_manager.driver.get_session() as session:
        # First check if the step exists
        result = session.run(
            """
            MATCH (s:STEP {id: "get-question"})
            RETURN s.id as id, s.input as input
            """
        )
        
        step = result.single()
        if not step:
            logger.error("get-question step not found in database")
            return False
            
        logger.info(f"Current get-question input: {step['input']}")
        
        # Update the step with a static greeting
        result = session.run(
            """
            MATCH (s:STEP {id: "get-question"})
            SET s.input = $input
            RETURN s.id as id, s.input as input
            """,
            input=json.dumps({"query": "GM! How can I help you today?"})
        )
        
        updated = result.single()
        if updated:
            logger.info(f"Updated get-question input: {updated['input']}")
            return True
        else:
            logger.error("Failed to update get-question step")
            return False

def fix_relationships():
    """Fix relationships in the graph that have problems."""
    session_manager = get_session_manager()
    
    # Fix the provide-answer -> get-question relationship 
    with session_manager.driver.get_session() as session:
        # First, check the current relationship
        result = session.run("""
        MATCH (source:STEP {id: 'provide-answer'})-[r:NEXT]->(target:STEP {id: 'get-question'})
        RETURN r.conditions as conditions
        """)
        
        record = result.single()
        if record:
            print(f"Found provide-answer -> get-question relationship with conditions: {record['conditions']}")
            
            # Now update it with a simple merits_followup condition that's more explicit
            session.run("""
            MATCH (source:STEP {id: 'provide-answer'})-[r:NEXT]->(target:STEP {id: 'get-question'})
            SET r.conditions = '["@{SESSION_ID}.generate-answer.merits_followup"]'
            """)
            
            print("Updated relationship condition to use direct boolean check")
            
        else:
            print("Relationship not found, creating it...")
            
            # Create the relationship if it doesn't exist
            session.run("""
            MATCH (source:STEP {id: 'provide-answer'})
            MATCH (target:STEP {id: 'get-question'})
            CREATE (source)-[r:NEXT {
              id: 'forward_followup',
              conditions: '["@{SESSION_ID}.generate-answer.merits_followup"]'
            }]->(target)
            """)
            
            print("Created new relationship with direct boolean check")
        
        # Verify the update
        result = session.run("""
        MATCH (source:STEP {id: 'provide-answer'})-[r:NEXT]->(target:STEP {id: 'get-question'})
        RETURN r.conditions as conditions
        """)
        
        record = result.single()
        if record:
            print(f"Verified relationship now has conditions: {record['conditions']}")

def update_generate_answer_input():
    """Update the generate-answer step input to ensure it has the right schema definition."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        # First check the current input
        result = session.run("""
        MATCH (s:STEP {id: 'generate-answer'})
        RETURN s.input as input
        """)
        
        record = result.single()
        if record:
            print(f"Current generate-answer input: {record['input']}")
            
            # Update with explicit schema requirements
            session.run("""
            MATCH (s:STEP {id: 'generate-answer'})
            SET s.input = '{
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "system": "You are a helpful assistant specializing in explaining topics in a user-friendly way. Provide clear explanations that assume no prior knowledge. Maintain the conversation context and topic throughout your responses. Be brief and concise. If the conversation has reached a natural conclusion or the user signals disinterest, set merits_followup to false.",
                "user": "@{SESSION_ID}.get-question.response",
                "include_history": true,
                "directly_set_reply": true,
                "schema": {
                    "type": "object",
                    "properties": {
                        "response": {
                            "type": "string",
                            "description": "The main response to the user query"
                        },
                        "followup": {
                            "type": "string",
                            "description": "A question for the user that encourages them to continue to explore the subject. If merits_followup is false, this field can be empty."
                        },
                        "merits_followup": {
                            "type": "boolean",
                            "description": "Indicates whether the conversation should continue. Set to false if the topic has been fully explored or the users question has been completely answered."
                        }
                    },
                    "required": ["response", "merits_followup", "followup"]
                }
            }'
            """)
            
            print("Updated generate-answer input with explicit schema requirements")
            
        else:
            print("generate-answer step not found!")

if __name__ == "__main__":
    print("Fixing greeting in get-question step...")
    if fix_greeting():
        print("Successfully fixed the greeting!")
    else:
        print("Failed to fix the greeting.")
    fix_relationships()
    update_generate_answer_input()
    print("Fixes applied successfully") 