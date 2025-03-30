#!/usr/bin/env python
"""
Examine workflow details from the Neo4j database.
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
sys.path.append(script_dir)

# Load environment variables
load_dotenv()

# Try to import the session manager
try:
    from core.session_manager import get_session_manager
except ImportError as e:
    logger.error(f"Failed to import components: {e}")
    sys.exit(1)

def examine_workflow():
    """Examine the workflow configuration in Neo4j."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        # Get offensive-reply step details
        print("\n=== OFFENSIVE-REPLY STEP DETAILS ===")
        result = session.run("""
            MATCH (s:STEP {id: 'offensive-reply'})
            RETURN s.id as id, s.function as function, s.input as input
        """)
        
        record = result.single()
        if record:
            step_id = record["id"]
            function = record["function"]
            input_str = record["input"]
            
            print(f"Step ID: {step_id}")
            print(f"Function: {function}")
            print(f"Input: {input_str}")
            
            if input_str:
                try:
                    input_data = json.loads(input_str)
                    print(f"Parsed Input: {json.dumps(input_data, indent=2)}")
                except:
                    print("Could not parse input as JSON")
        else:
            print("No offensive-reply step found")
        
        # Get paths to and from offensive-reply
        print("\n=== PATHS TO OFFENSIVE-REPLY ===")
        result = session.run("""
            MATCH (source:STEP)-[r:NEXT]->(target:STEP {id: 'offensive-reply'})
            RETURN source.id as source, r.conditions as conditions
        """)
        
        for record in result:
            source = record["source"]
            conditions = record["conditions"]
            print(f"From {source} with conditions: {conditions}")
        
        print("\n=== PATHS FROM OFFENSIVE-REPLY ===")
        result = session.run("""
            MATCH (source:STEP {id: 'offensive-reply'})-[r:NEXT]->(target:STEP)
            RETURN target.id as target, r.conditions as conditions
        """)
        
        for record in result:
            target = record["target"]
            conditions = record["conditions"]
            print(f"To {target} with conditions: {conditions}")
        
        # Check session processing output handling
        print("\n=== ENGINE RESPONSE HANDLING ===")
        result = session.run("""
            MATCH (s:STEP)
            WHERE s.function CONTAINS 'reply'
            RETURN s.id as id, s.function as function
        """)
        
        print("Steps using reply functions:")
        for record in result:
            print(f"- {record['id']}: {record['function']}")
            
        # Look at the most recent session execution
        print("\n=== RECENT SESSION EXECUTION ===")
        result = session.run("""
            MATCH (s:SESSION)
            RETURN s.id as id, s.state as state
            ORDER BY s.created_at DESC
            LIMIT 1
        """)
        
        record = result.single()
        if record:
            session_id = record["id"]
            state_json = record["state"]
            
            print(f"Most recent session: {session_id}")
            
            if state_json:
                try:
                    state = json.loads(state_json)
                    
                    # Check if offensive-reply was executed
                    if "outputs" in state.get("data", {}) and "offensive-reply" in state["data"]["outputs"]:
                        print("\noffensive-reply was executed with output:")
                        print(json.dumps(state["data"]["outputs"]["offensive-reply"], indent=2))
                    else:
                        print("\noffensive-reply was not executed in this session")
                        
                    # Check workflow status
                    for step_id, status in state.get("workflow", {}).items():
                        print(f"\nStep {step_id} status:")
                        print(json.dumps(status, indent=2))
                except:
                    print("Could not parse state as JSON")
        else:
            print("No sessions found")

if __name__ == "__main__":
    examine_workflow() 