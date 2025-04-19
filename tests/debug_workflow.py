#!/usr/bin/env python
"""
Diagnostic script to debug workflow execution and cypher utility.
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set up paths
script_dir = os.path.dirname(os.path.abspath(__file__))
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
    from core.graph_engine import get_graph_workflow_engine
    logger.info("Successfully imported core components")
except ImportError as e:
    logger.error(f"Failed to import components: {e}")
    sys.exit(1)

def inspect_recent_sessions():
    """Inspect the most recent workflow sessions for debugging."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        print("\n=== RECENT SESSIONS ===")
        result = session.run("""
            MATCH (s:SESSION)
            RETURN s.id as id, s.state as state
            ORDER BY s.created_at DESC
            LIMIT 5
        """)
        
        for record in result:
            session_id = record["id"]
            state_json = record["state"]
            
            if not state_json:
                continue
                
            try:
                state = json.loads(state_json)
                print(f"\nSESSION: {session_id}")
                
                # Print workflow steps and status
                print("\n  STEP STATUS:")
                for step_id, info in state.get("workflow", {}).items():
                    status = info.get("status", "unknown")
                    error = info.get("error", "")
                    print(f"    {step_id}: {status}" + (f" - ERROR: {error}" if error else ""))
                
                # Look specifically for movie_info step activation
                if "movie_info" in state.get("workflow", {}):
                    print("\n  MOVIE_INFO STEP DETAILS:")
                    movie_info_status = state["workflow"]["movie_info"].get("status", "unknown")
                    print(f"    Status: {movie_info_status}")
                    
                    # Check for output from movie_info step
                    if "movie_info" in state.get("data", {}).get("outputs", {}):
                        movie_output = state["data"]["outputs"]["movie_info"]
                        print(f"    Output: {json.dumps(movie_output, indent=2)}")
                    else:
                        print("    No output found")
                        
                    # If there's an error, show it
                    if movie_info_status == "error":
                        error = state["workflow"]["movie_info"].get("error", "No error message")
                        print(f"    Error: {error}")
                else:
                    print("\n  MOVIE_INFO step was never activated")
                
                # Check if generate step had is_movie_question
                if "generate" in state.get("data", {}).get("outputs", {}):
                    generate_outputs = state["data"]["outputs"]["generate"]
                    if isinstance(generate_outputs, list) and generate_outputs:
                        latest_output = generate_outputs[-1]
                        if "is_movie_question" in latest_output:
                            print(f"\n  GENERATE step is_movie_question: {latest_output['is_movie_question']}")
                        else:
                            print("\n  GENERATE step did not include is_movie_question in output")
                
                # Look at user messages to identify movie-related queries
                messages = state.get("data", {}).get("messages", [])
                user_messages = [m for m in messages if m.get("role") == "user"]
                if user_messages:
                    print("\n  USER MESSAGES:")
                    for msg in user_messages[-3:]:  # Show last 3 messages
                        content = msg.get("content", "")
                        print(f"    User: {content}")
            except Exception as e:
                print(f"Error parsing session {session_id}: {e}")

def inspect_workflow_nodes():
    """Inspect workflow nodes and relationships to ensure correct setup."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        print("\n=== WORKFLOW NODES AND RELATIONSHIPS ===")
        
        # Check for movie_info step
        result = session.run("""
            MATCH (s:STEP {id: 'movie_info'})
            RETURN s.function as function, s.input as input
        """)
        
        record = result.single()
        if record:
            function = record["function"]
            input_str = record["input"]
            
            print("\nMOVIE_INFO STEP:")
            print(f"  Function: {function}")
            print(f"  Input: {input_str}")
            
            try:
                input_data = json.loads(input_str)
                print(f"  Parsed Input: {json.dumps(input_data, indent=2)}")
            except:
                print("  Failed to parse input as JSON")
        else:
            print("\nMOVIE_INFO step not found in database")
        
        # Check conditions on relationships
        result = session.run("""
            MATCH (generate:STEP {id: 'generate'})-[r:NEXT]->(target:STEP)
            RETURN target.id as target, r.conditions as conditions, r.priority as priority
            ORDER BY priority
        """)
        
        print("\nGENERATE STEP OUTGOING RELATIONSHIPS:")
        for record in result:
            target = record["target"]
            conditions = record["conditions"]
            priority = record["priority"]
            
            print(f"  → {target}")
            print(f"    Conditions: {conditions}")
            print(f"    Priority: {priority}")

def patch_cypher_utility():
    """Add debug logging to cypher.py utility."""
    print("\n=== ADDING DEBUG LOGGING TO CYPHER UTILITY ===")
    print("To add debug logging, edit utils/cypher.py to add more detailed logging statements.")
    print("Specifically look at:")
    print("1. cypher - Add logging before and after variable resolution")
    print("2. generate_cypher_query - Log the exact query being generated")
    print("3. execute_query - Log parameters and query execution details")

def run_test_query():
    """Run a test query directly using the cypher utility."""
    print("\n=== RUNNING TEST QUERY ===")
    
    try:
        from utils.cypher import cypher
        
        # Get a session ID to use for variable resolution
        session_id = "test_session"
        
        # Test with direct query
        test_result = cypher(
            query="MATCH (m:Movie) WHERE m.title CONTAINS 'Fight' RETURN m"
        )
        print("Direct query result:", test_result)
        
        # Test with parameterized query
        test_result = cypher(
            query="MATCH (m:Movie {title: $title}) RETURN m",
            title="Fight Club"
        )
        print("Parameterized query result:", test_result)
        
        # Test with instruction
        test_result = cypher(
            instruction="Find all information about the movie Fight Club",
        )
        print("Instruction result:", test_result)
        
        # Test with more complex query to retrieve actors
        test_result = cypher(
            instruction="Find the movie Fight Club and all actors who starred in it",
            ontology="The graph contains Movie nodes with properties (title, year, description) and Person nodes with properties (name, age). Persons are connected to Movies via ACTED_IN relationships."
        )
        print("Complex query result:", test_result)
        
    except Exception as e:
        print(f"Error during testing: {e}")

if __name__ == "__main__":
    inspect_recent_sessions()
    inspect_workflow_nodes()
    patch_cypher_utility()
    run_test_query() 