#!/usr/bin/env python3
"""
Test script to check the environment setup and database connections.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_environment():
    """Test environment variables and paths"""
    logger.info("Testing environment setup...")
    
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logger.info(f"Current directory: {current_dir}")
    
    # Check Python path
    logger.info(f"Python path: {sys.path}")
    
    # Load environment variables
    if os.path.exists(".env.local"):
        load_dotenv(".env.local")
        logger.info("Loaded .env.local")
    elif os.path.exists(".env"):
        load_dotenv(".env")
        logger.info("Loaded .env")
    else:
        logger.warning("No .env file found")
    
    # Check environment variables
    logger.info("Checking environment variables...")
    env_vars = {
        "NEO4J_URI": os.environ.get("NEO4J_URI"),
        "NEO4J_USERNAME": os.environ.get("NEO4J_USERNAME"),
        "NEO4J_PASSWORD": os.environ.get("NEO4J_PASSWORD", "***masked***"),
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "***masked***"),
        "FLASK_SECRET_KEY": os.environ.get("FLASK_SECRET_KEY", "***masked***")
    }
    
    for key, value in env_vars.items():
        if value:
            if "PASSWORD" in key or "KEY" in key:
                logger.info(f"{key}: ***masked***")
            else:
                logger.info(f"{key}: {value}")
        else:
            logger.warning(f"{key}: Not set!")

def test_imports():
    """Test importing critical components"""
    logger.info("Testing imports...")
    
    try:
        logger.info("Trying direct import...")
        
        try:
            from core.session_manager import get_session_manager
            from core.graph_engine import get_graph_workflow_engine
            logger.info("✅ Successfully imported from core directly")
        except ImportError as e:
            logger.error(f"❌ Failed to import directly: {e}")
            
            try:
                logger.info("Trying from LUNA package...")
                from LUNA.core.session_manager import get_session_manager
                from LUNA.core.graph_engine import get_graph_workflow_engine
                logger.info("✅ Successfully imported from LUNA.core")
            except ImportError as e:
                logger.error(f"❌ Failed to import from LUNA.core: {e}")
                
    except Exception as e:
        logger.error(f"Unexpected import error: {e}")

def test_neo4j_connection():
    """Test connecting to Neo4j"""
    logger.info("Testing Neo4j connection...")
    
    try:
        from neo4j import GraphDatabase
        
        uri = os.environ.get("NEO4J_URI")
        username = os.environ.get("NEO4J_USERNAME")
        password = os.environ.get("NEO4J_PASSWORD")
        
        if not uri or not username or not password:
            logger.error("❌ Missing Neo4j connection details")
            return
            
        logger.info(f"Connecting to Neo4j at {uri} with username {username}")
        
        try:
            driver = GraphDatabase.driver(uri, auth=(username, password))
            
            with driver.session() as session:
                result = session.run("RETURN 1 as test, timestamp() as now")
                record = result.single()
                logger.info(f"✅ Successfully connected to Neo4j: test={record['test']}, time={record['now']}")
                
                # Count nodes
                result = session.run("MATCH (n) RETURN count(n) as count")
                count = result.single()["count"]
                logger.info(f"Found {count} nodes in the database")
                
                # Count STEP nodes and relationships
                result = session.run("MATCH (s:STEP) RETURN count(s) as steps")
                steps = result.single()["steps"]
                logger.info(f"Found {steps} STEP nodes")
                
                result = session.run("MATCH ()-[r:NEXT]->() RETURN count(r) as rels")
                rels = result.single()["rels"]
                logger.info(f"Found {rels} NEXT relationships")
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to Neo4j: {e}")
    except ImportError:
        logger.error("❌ Neo4j package not installed")

if __name__ == "__main__":
    logger.info("=== Testing Environment ===")
    test_environment()
    
    logger.info("\n=== Testing Imports ===")
    test_imports()
    
    logger.info("\n=== Testing Neo4j Connection ===")
    test_neo4j_connection()
    
    logger.info("\n=== All Tests Complete ===") 