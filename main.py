"""
Main entry point for the Neo4j Graph-Based Workflow Engine.

This script provides a simple interface to create and run workflows.
"""

import os
import json
import logging
import sys
import argparse
from dotenv import load_dotenv

# Load environment variables from .env.local file
load_dotenv('LUNA/.env.local')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Import core components
from core.graph_engine import get_graph_workflow_engine
from core.session_manager import get_session_manager

def init_database():
    """Initialize Neo4j database with schema constraints"""
    from core.database import get_neo4j_driver
    
    driver = get_neo4j_driver()
    with driver.get_session() as session:
        try:
            # Create constraints
            session.run("""
            CREATE CONSTRAINT session_id IF NOT EXISTS 
            FOR (s:SESSION) REQUIRE s.id IS UNIQUE
            """)
            
            session.run("""
            CREATE CONSTRAINT step_id IF NOT EXISTS 
            FOR (s:STEP) REQUIRE s.id IS UNIQUE
            """)
            
            logger.info("Database schema initialized")
        except Exception as e:
            logger.error(f"Error initializing database schema: {str(e)}")
            raise

def create_example_workflow():
    """Create a simple example workflow in Neo4j"""
    from core.database import get_neo4j_driver
    
    driver = get_neo4j_driver()
    with driver.get_session() as session:
        try:
            # First check if workflow already exists
            result = session.run("""
            MATCH (s:STEP {id: 'root'})
            RETURN count(s) as count
            """)
            
            if result.single()["count"] > 0:
                logger.info("Example workflow already exists")
                return
                
            # Create example workflow
            session.run("""
            // Root step - initial user input
            CREATE (root:STEP {
              id: "root",
              function: "utils.request",
              input: '{"prompt": "How can I help you today?"}'
            })
            """)
            
            session.run("""
            // Generate answer based on user query
            CREATE (generate:STEP {
              id: "generate-answer",
              function: "utils.generate",
              input: '{"user": "User query: \\\"@{SESSION_ID}.root.response\\\". Provide a helpful response."}'
            })
            """)
            
            session.run("""
            // Reply to user with generated answer
            CREATE (reply:STEP {
              id: "send-response",
              function: "utils.reply",
              input: '{"message": "@{SESSION_ID}.generate-answer.response"}'
            })
            """)
            
            session.run("""
            // Create flow relationships
            MATCH (root:STEP {id: "root"})
            MATCH (generate:STEP {id: "generate-answer"})
            CREATE (root)-[:NEXT]->(generate)
            """)
            
            session.run("""
            MATCH (generate:STEP {id: "generate-answer"})
            MATCH (reply:STEP {id: "send-response"})
            CREATE (generate)-[:NEXT]->(reply)
            """)
            
            logger.info("Example workflow created")
        except Exception as e:
            logger.error(f"Error creating example workflow: {str(e)}")
            raise

def run_workflow(session_id=None):
    """Run a workflow session"""
    engine = get_graph_workflow_engine()
    
    if not session_id:
        # Create a new session
        session_manager = get_session_manager()
        session_id = session_manager.create_session()
        logger.info(f"Created new session: {session_id}")
    
    # Start processing workflow
    status = engine.process_workflow(session_id)
    
    while status in ["active", "awaiting_input"]:
        if status == "awaiting_input":
            # Get session state
            session_state = engine.session_manager.get_session_state(session_id)
            
            # Find the awaiting step output
            awaiting_step = None
            for step_id, info in session_state["workflow"].items():
                if info["status"] == "awaiting_input":
                    awaiting_step = step_id
                    break
            
            if awaiting_step and awaiting_step in session_state["data"]["outputs"]:
                req_data = session_state["data"]["outputs"][awaiting_step]
                prompt = req_data.get("prompt", "Input required:")
                
                # Get user input
                user_input = input(f"{prompt} ")
                
                # Handle user input and continue workflow
                status = engine.handle_user_input(session_id, user_input)
            else:
                logger.error("Awaiting input but no awaiting step found")
                break
        else:
            # Continue processing
            status = engine.process_workflow(session_id)
    
    # Get final session state
    session_state = engine.session_manager.get_session_state(session_id)
    
    # Check for errors
    errors = []
    for step_id, info in session_state["workflow"].items():
        if info["status"] == "error":
            errors.append(f"{step_id}: {info.get('error', 'Unknown error')}")
    
    if errors:
        logger.error(f"Workflow completed with errors: {', '.join(errors)}")
    else:
        logger.info(f"Workflow completed successfully")
    
    return session_id, status

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Neo4j Graph-Based Workflow Engine')
    parser.add_argument('--init', action='store_true', help='Initialize database schema')
    parser.add_argument('--create-example', action='store_true', help='Create example workflow')
    parser.add_argument('--run', action='store_true', help='Run workflow')
    parser.add_argument('--session', type=str, help='Session ID (for --run)')
    
    args = parser.parse_args()
    
    try:
        if args.init:
            init_database()
            
        if args.create_example:
            create_example_workflow()
            
        if args.run:
            run_workflow(args.session)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 