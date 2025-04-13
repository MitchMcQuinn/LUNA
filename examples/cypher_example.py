#!/usr/bin/env python3
"""
Example script demonstrating the use of the cypher utility in a workflow.
"""

import os
import sys
import uuid
import json
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

# Load environment variables
env_paths = [
    os.path.join(project_root, '.env.local'),  
    os.path.join(project_root, '.env')
]

for env_path in env_paths:
    if os.path.exists(env_path):
        logger.info(f"Loading environment from: {env_path}")
        load_dotenv(env_path)
        break
else:
    logger.warning("No environment file found.")

# Import core components
from core.session_manager import get_session_manager
from core.graph_engine import get_graph_workflow_engine

def create_example_workflow():
    """Create an example workflow using the cypher utility"""
    logger.info("Creating example workflow")
    
    # Get session manager
    session_manager = get_session_manager()
    
    # Create a unique ID for this workflow
    workflow_id = f"cypher_example_{uuid.uuid4().hex[:8]}"
    
    # Create unique step IDs based on workflow ID
    root_id = f"{workflow_id}_root"
    count_id = f"{workflow_id}_count"
    find_id = f"{workflow_id}_find"
    create_id = f"{workflow_id}_create"
    reply_id = f"{workflow_id}_reply"
    
    # Define the graph ontology for this example
    ontology = """
    The graph database contains the following node types:
    - SESSION: Represents a workflow session with properties id, state, created_at
    - STEP: Represents a workflow step with properties id, function
    """
    
    # Create workflow nodes and relationships in Neo4j
    with session_manager.driver.get_session() as session:
        # Create workflow root step
        session.run(
            """
            CREATE (root:STEP {
                id: $root_id,
                function: 'utils.request.request',
                input: $input
            })
            """,
            root_id=root_id,
            input=json.dumps({
                "prompt": "Welcome to the Cypher example workflow! What would you like to do?",
                "options": [
                    {"value": "count_sessions", "text": "Count all sessions"},
                    {"value": "find_steps", "text": "Find workflow steps"},
                    {"value": "create_test_node", "text": "Create a test node"}
                ]
            })
        )
        
        # Create count_sessions step using dynamic mode (natural language)
        session.run(
            """
            CREATE (count:STEP {
                id: $count_id,
                function: 'utils.cypher.cypher',
                input: $input
            })
            """,
            count_id=count_id,
            input=json.dumps({
                "instruction": "Count all SESSION nodes in the database and return the count",
                "ontology": ontology
            })
        )
        
        # Create find_steps step using direct mode (predefined query with variable)
        session.run(
            """
            CREATE (find:STEP {
                id: $find_id,
                function: 'utils.cypher.cypher',
                input: $input
            })
            """,
            find_id=find_id,
            input=json.dumps({
                "query": "MATCH (s:STEP) RETURN s.id as id, s.function as function LIMIT 10"
            })
        )
        
        # Create create_node step with safety checks
        session.run(
            """
            CREATE (create:STEP {
                id: $create_id,
                function: 'utils.cypher.cypher',
                input: $input
            })
            """,
            create_id=create_id,
            input=json.dumps({
                "query": "CREATE (t:TEST_NODE {id: 'example_test_node', created_at: datetime()}) RETURN t",
                "safety_on": True
            })
        )
        
        # Create reply step 
        session.run(
            """
            CREATE (reply:STEP {
                id: $reply_id,
                function: 'utils.reply.reply',
                input: $input
            })
            """,
            reply_id=reply_id,
            input=json.dumps({
                "message": f"@{{SESSION_ID}}.{count_id}.overview|No query results to display."
            })
        )
        
        # Create example relationships
        session.run(
            """
            MATCH (root:STEP {id: $root_id})
            MATCH (count:STEP {id: $count_id})
            MATCH (find:STEP {id: $find_id})
            MATCH (create:STEP {id: $create_id})
            MATCH (reply:STEP {id: $reply_id})
            
            CREATE (root)-[:NEXT {conditions: [$condition1]}]->(count)
            CREATE (root)-[:NEXT {conditions: [$condition2]}]->(find)
            CREATE (root)-[:NEXT {conditions: [$condition3]}]->(create)
            CREATE (count)-[:NEXT]->(reply)
            CREATE (find)-[:NEXT]->(reply)
            CREATE (create)-[:NEXT]->(reply)
            """,
            root_id=root_id,
            count_id=count_id,
            find_id=find_id,
            create_id=create_id,
            reply_id=reply_id,
            condition1=f"@{{SESSION_ID}}.{root_id}[0].response.value = 'count_sessions'",
            condition2=f"@{{SESSION_ID}}.{root_id}[0].response.value = 'find_steps'",
            condition3=f"@{{SESSION_ID}}.{root_id}[0].response.value = 'create_test_node'"
        )
        
        logger.info(f"Created workflow: {workflow_id}")
    
    return workflow_id

def run_workflow():
    """Run the example workflow"""
    # Create the workflow
    workflow_id = create_example_workflow()
    
    # Create a session
    session_manager = get_session_manager()
    session_id = session_manager.create_session(workflow_id)
    logger.info(f"Created session: {session_id}")
    
    # Get the workflow engine
    engine = get_graph_workflow_engine()
    
    # Start the workflow
    status = engine.process_workflow(session_id)
    logger.info(f"Workflow initial status: {status}")
    
    # Handle user input for option selection (simulate user choosing "count_sessions")
    if status == "awaiting_input":
        logger.info("Providing user input: count_sessions")
        status = engine.handle_user_input(session_id, "count_sessions")
        logger.info(f"Workflow status after input: {status}")
        
        # Process the workflow until completion
        while status in ["active", "pending"]:
            status = engine.process_workflow(session_id)
            logger.info(f"Workflow status: {status}")
    
    # Get final state
    state = session_manager.get_session_state(session_id)
    
    # Print the conversation messages
    logger.info("Conversation:")
    for message in state.get("data", {}).get("messages", []):
        role = message.get("role", "unknown")
        content = message.get("content", "")
        logger.info(f"{role.upper()}: {content}")
    
    # Print the outputs from each step
    logger.info("\nStep outputs:")
    for step_id, outputs in state.get("data", {}).get("outputs", {}).items():
        if outputs:
            if isinstance(outputs, list):
                latest_output = outputs[-1]
                logger.info(f"{step_id}: {json.dumps(latest_output, indent=2)[:200]}...")
            else:
                logger.info(f"{step_id}: {json.dumps(outputs, indent=2)[:200]}...")
        else:
            logger.info(f"{step_id}: No output")
    
    return session_id

if __name__ == "__main__":
    try:
        session_id = run_workflow()
        logger.info(f"Workflow completed successfully with session ID: {session_id}")
    except Exception as e:
        logger.error(f"Error running workflow: {e}", exc_info=True) 