#!/usr/bin/env python3
"""
Simple test script to check Neo4j connection.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

# Load environment variables - first try .env.local
env_paths = [
    os.path.join(script_dir, '.env.local'),  
    os.path.join(project_root, '.env.local'),
    os.path.join(script_dir, '.env'),  
    os.path.join(project_root, '.env')
]

for env_path in env_paths:
    if os.path.exists(env_path):
        logger.info(f"Loading environment from: {env_path}")
        # Print contents of the file (masking passwords)
        with open(env_path, 'r') as f:
            content = f.read()
            # Replace password values for security
            masked_content = []
            for line in content.split('\n'):
                if "PASSWORD" in line and "=" in line:
                    parts = line.split('=', 1)
                    masked_line = f"{parts[0]}=[HIDDEN]"
                    masked_content.append(masked_line)
                else:
                    masked_content.append(line)
            logger.info(f"File content:\n{''.join(masked_content)}")
        
        load_dotenv(env_path)
        break
else:
    logger.warning("No environment file found.")

# Check for Neo4j environment variables
neo4j_uri = os.environ.get("NEO4J_URI")
neo4j_user = os.environ.get("NEO4J_USERNAME")
neo4j_password = os.environ.get("NEO4J_PASSWORD")

logger.info("Neo4j connection parameters from environment:")
if neo4j_uri:
    logger.info(f"URI: {neo4j_uri}")
else:
    logger.error("NEO4J_URI is not set")

if neo4j_user:
    logger.info(f"Username: {neo4j_user}")
else:
    logger.error("NEO4J_USERNAME is not set")

if neo4j_password:
    logger.info("Password: [HIDDEN]")
else:
    logger.error("NEO4J_PASSWORD is not set")

# List all environment variables for debugging
logger.info("All environment variables:")
for key, value in sorted(os.environ.items()):
    if "PASSWORD" in key or "SECRET" in key:
        logger.info(f"{key}=[HIDDEN]")
    else:
        logger.info(f"{key}={value}")

# Try to connect to Neo4j directly
if neo4j_uri and neo4j_user and neo4j_password:
    try:
        logger.info(f"Attempting to connect directly to Neo4j at {neo4j_uri}")
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        # Verify connection
        with driver.session() as session:
            result = session.run("RETURN 'Connection successful' AS message")
            record = result.single()
            if record:
                logger.info(f"Direct connection test: {record['message']}")
                
            # Count nodes as a basic query test
            result = session.run("MATCH (n) RETURN count(n) AS node_count")
            record = result.single()
            if record:
                logger.info(f"Database contains {record['node_count']} nodes.")
                
        logger.info("Direct Neo4j connection test successful!")
        driver.close()
        
    except Exception as e:
        logger.error(f"Error connecting directly to Neo4j: {e}")

# Now try using the database module
try:
    logger.info("Attempting to connect using database module")
    from core.database import get_neo4j_driver
    
    driver = get_neo4j_driver()
    
    with driver.get_session() as session:
        result = session.run("RETURN 'Module connection successful' AS message")
        record = result.single()
        if record:
            logger.info(f"Module connection test: {record['message']}")
            
        # Count nodes as a basic query test
        result = session.run("MATCH (n) RETURN count(n) AS node_count")
        record = result.single()
        if record:
            logger.info(f"Database contains {record['node_count']} nodes.")
            
    logger.info("Module Neo4j connection test successful!")
    
except Exception as e:
    logger.error(f"Error connecting to Neo4j using module: {e}")
    
# Now try using the session manager
try:
    logger.info("Attempting to connect using session manager")
    from core.session_manager import get_session_manager
    
    session_manager = get_session_manager()
    
    # Create a test session
    session_id = session_manager.create_session("test_workflow")
    logger.info(f"Created test session: {session_id}")
    
    # Get session state
    state = session_manager.get_session_state(session_id)
    logger.info(f"Session state: {state}")
    
    # Delete test session
    session_manager.delete_session(session_id)
    logger.info(f"Deleted test session: {session_id}")
    
    logger.info("Session manager test successful!")
    
except Exception as e:
    logger.error(f"Error using session manager: {e}")

logger.info("Neo4j connection tests completed.") 