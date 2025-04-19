#!/usr/bin/env python
"""
Check workflow connections and step configurations.
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
    from core.graph_engine import get_graph_workflow_engine
    logger.info("Successfully imported core components")
except ImportError as e:
    logger.error(f"Failed to import components: {e}")
    sys.exit(1)

def check_workflow_nodes():
    """Check workflow nodes and their configurations."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        print("\n=== STEP CONFIGURATIONS ===")
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
            
            # Parse input JSON if possible
            if input_str:
                try:
                    input_data = json.loads(input_str)
                    if step_id == "generate-answer" and "user" in input_data:
                        print(f"  Variable reference: {input_data['user']}")
                    elif step_id == "provide-answer" and "message" in input_data:
                        print(f"  Variable reference: {input_data['message']}")
                except:
                    print("  Invalid JSON")

def check_workflow_connections():
    """Check workflow connections between steps."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        print("\n=== WORKFLOW CONNECTIONS ===")
        result = session.run("""
            MATCH (source:STEP)-[r:NEXT]->(target:STEP)
            RETURN source.id as source, target.id as target,
                   r.conditions as conditions
            ORDER BY source.id
        """)
        
        for record in result:
            source = record["source"]
            target = record["target"]
            conditions = record["conditions"] or "None"
            
            print(f"{source} -> {target}")
            print(f"  Conditions: {conditions}")

def check_execution_sequence():
    """Check execution sequence of a workflow."""
    print("\n=== EXECUTION SEQUENCE ===")
    print("Expected sequence:")
    print("1. root -> get-question (get-question awaits input)")
    print("2. User provides input")
    print("3. get-question -> generate-answer")
    print("4. generate-answer -> provide-answer (displays response)")
    print("5. provide-answer -> get-question (if merits_followup=true)")
    
def create_test_session():
    """Create a test session and trace workflow execution."""
    session_manager = get_session_manager()
    engine = get_graph_workflow_engine()
    
    # Create a new session
    session_id = session_manager.create_session()
    print(f"\n=== CREATED TEST SESSION: {session_id} ===")
    
    # Process workflow
    print("\nProcessing workflow...")
    status = engine.process_workflow(session_id)
    print(f"Status after initial processing: {status}")
    
    # Get session state 
    state = session_manager.get_session_state(session_id)
    
    # Check step status
    print("\nStep statuses:")
    for step_id, info in state["workflow"].items():
        print(f"  {step_id}: {info['status']}")
    
    # Check if awaiting input
    awaiting_steps = [step_id for step_id, info in state["workflow"].items() if info["status"] == "awaiting_input"]
    if awaiting_steps:
        print(f"\nSteps awaiting input: {awaiting_steps}")
        
        # Check if get-question is awaiting input
        if "get-question" in awaiting_steps:
            print("\nChecking get-question output:")
            if "get-question" in state["data"]["outputs"]:
                output = state["data"]["outputs"]["get-question"]
                print(f"  {output}")
    
    return session_id, state

def simulate_user_input(session_id):
    """Simulate user input to the workflow."""
    engine = get_graph_workflow_engine()
    
    # Simulate user input
    print(f"\n=== SIMULATING USER INPUT ===")
    print("User input: 'Tell me about ducks'")
    status = engine.handle_user_input(session_id, {"response": "Tell me about ducks"})
    print(f"Status after user input: {status}")
    
    # Process workflow again
    print("\nProcessing workflow after user input...")
    status = engine.process_workflow(session_id)
    print(f"Status after processing: {status}")
    
    # Get session state 
    session_manager = get_session_manager()
    state = session_manager.get_session_state(session_id)
    
    # Check step status
    print("\nStep statuses after user input:")
    for step_id, info in state["workflow"].items():
        print(f"  {step_id}: {info['status']}")
    
    # Check outputs
    print("\nOutputs after user input:")
    for step_id, output in state["data"]["outputs"].items():
        print(f"  {step_id}: {output}")
    
    return status, state

if __name__ == "__main__":
    check_workflow_nodes()
    check_workflow_connections()
    check_execution_sequence()
    
    # Create a test session and trace execution
    session_id, state = create_test_session()
    
    # Simulate user input if waiting for input
    awaiting_steps = [step_id for step_id, info in state["workflow"].items() if info["status"] == "awaiting_input"]
    if awaiting_steps and "get-question" in awaiting_steps:
        status, state = simulate_user_input(session_id) 