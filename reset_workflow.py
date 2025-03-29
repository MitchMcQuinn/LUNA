#!/usr/bin/env python3
"""
Reset Neo4j workflow and install conversation_loop.cypher
"""

import os
import logging
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('.env.local')

# Neo4j connection details
URI = os.environ.get('NEO4J_URI')
USERNAME = os.environ.get('NEO4J_USERNAME')
PASSWORD = os.environ.get('NEO4J_PASSWORD')

def reset_workflow():
    logger.info(f"Connecting to Neo4j at {URI}")
    
    # Check if all connection details are available
    if not URI or not USERNAME or not PASSWORD:
        logger.error("Missing Neo4j connection details. Check your .env.local file.")
        return False
    
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    
    try:
        # Step 1: Delete all existing STEP nodes
        with driver.session() as session:
            logger.info("Deleting all existing STEP nodes...")
            result = session.run("MATCH (s:STEP) DETACH DELETE s RETURN count(*) as deleted")
            deleted = result.single()["deleted"] if result.peek() else 0
            logger.info(f"Deleted {deleted} nodes")
        
        # Step 2: Read the conversation loop cypher file
        cypher_file = "conversation_loop.cypher"
        if not os.path.exists(cypher_file):
            logger.error(f"Cypher file not found: {cypher_file}")
            return False
        
        with open(cypher_file, 'r') as f:
            cypher_script = f.read()
        
        # Step 3: Execute the cypher script to create the workflow
        with driver.session() as session:
            logger.info(f"Creating new workflow from {cypher_file}...")
            session.run(cypher_script)
        
        # Step 4: Verify workflow was created correctly
        with driver.session() as session:
            # Count steps
            result = session.run("MATCH (s:STEP) RETURN count(s) as count")
            step_count = result.single()["count"]
            
            # Count relationships
            result = session.run("MATCH ()-[r:NEXT]->() RETURN count(r) as count")
            rel_count = result.single()["count"]
            
            # Get step IDs
            result = session.run("MATCH (s:STEP) RETURN s.id as id")
            steps = [record["id"] for record in result]
            
            logger.info(f"Created workflow with {step_count} steps and {rel_count} relationships")
            logger.info(f"Steps: {', '.join(steps)}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return False
    
    finally:
        driver.close()

if __name__ == "__main__":
    success = reset_workflow()
    if success:
        logger.info("✅ Workflow reset completed successfully!")
    else:
        logger.error("❌ Workflow reset failed!") 