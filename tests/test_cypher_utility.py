#!/usr/bin/env python3
"""
Test script for the cypher utility.
"""

import os
import sys
import json
import logging
import uuid
import time
from dotenv import load_dotenv
from utils.cypher import cypher

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
        load_dotenv(env_path)
        break
else:
    logger.warning("No environment file found. Tests may fail due to missing database configuration.")

# Check if Neo4j environment variables are set
neo4j_uri = os.environ.get("NEO4J_URI")
neo4j_user = os.environ.get("NEO4J_USERNAME")
neo4j_password = os.environ.get("NEO4J_PASSWORD")

if not neo4j_uri or not neo4j_user or not neo4j_password:
    logger.error("Neo4j environment variables not set. Please set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD.")
    logger.info("Current environment:")
    for key in sorted(os.environ.keys()):
        if "NEO4J" in key:
            value = os.environ[key]
            # Mask password for security
            if "PASSWORD" in key:
                masked_value = "*" * len(value) if value else "NOT SET"
                logger.info(f"  {key}={masked_value}")
            else:
                logger.info(f"  {key}={value}")
    sys.exit(1)

# Import core components
from core.session_manager import get_session_manager
from core.utility_registry import get_utility_registry

def setup_test_data():
    """Create test data in Neo4j for the tests"""
    logger.info("Setting up test data in Neo4j")
    
    # Get session manager
    session_manager = get_session_manager()
    
    # Create a test session node
    session_id = str(uuid.uuid4())
    
    # Initialize the session state
    initial_state = {
        "id": session_id,
        "workflow": {
            "root": {
                "status": "active",
                "error": ""
            }
        },
        "last_evaluated": 0,
        "data": {
            "outputs": {
                "test_step": [{"value": "test_value", "array_value": [1, 2, 3]}]
            },
            "messages": []
        }
    }
    
    # Create session node in Neo4j
    with session_manager.driver.get_session() as session:
        session.run(
            """
            CREATE (s:SESSION {id: $id, state: $state})
            """,
            id=session_id,
            state=json.dumps(initial_state)
        )
        
        # Create some test step nodes
        session.run(
            """
            CREATE (s1:STEP {id: 'test_step_1', function: 'utils.test.function'})
            CREATE (s2:STEP {id: 'test_step_2', function: 'utils.test.function'})
            CREATE (s3:STEP {id: 'test_step_3', function: 'utils.test.function'})
            """
        )
    
    logger.info(f"Created test session with ID: {session_id}")
    return session_id

def cleanup_test_data(session_id):
    """Clean up test data from Neo4j"""
    logger.info("Cleaning up test data from Neo4j")
    
    # Get session manager
    session_manager = get_session_manager()
    
    # Delete test data
    with session_manager.driver.get_session() as session:
        # Delete test session
        session.run(
            """
            MATCH (s:SESSION {id: $id})
            DETACH DELETE s
            """,
            id=session_id
        )
        
        # Delete test steps
        session.run(
            """
            MATCH (s:STEP) 
            WHERE s.id IN ['test_step_1', 'test_step_2', 'test_step_3']
            DETACH DELETE s
            """
        )

def test_direct_mode():
    """Test direct mode with a predefined query"""
    logger.info("Testing direct mode with predefined query")
    
    # Simple read query
    result = cypher(
        query="MATCH (s:SESSION) RETURN count(s) as session_count",
        max_results=10
    )
    
    # Check result structure
    assert "query" in result, "Result should contain the query"
    assert "result" in result, "Result should contain the results"
    assert "overview" in result, "Result should contain an overview"
    
    # Check that result contains data
    assert isinstance(result["result"], list), "Result should be a list"
    
    logger.info("✅ Direct mode test passed")
    return result

def test_dynamic_mode():
    """Test dynamic mode with natural language instruction"""
    logger.info("Testing dynamic mode with natural language instruction")
    
    # Simple read query using natural language
    result = cypher(
        instruction="Count how many SESSION nodes exist in the database",
        ontology="The database contains SESSION nodes with id and state properties.",
        max_results=10
    )
    
    # Check result structure
    assert "query" in result, "Result should contain the query"
    assert "result" in result, "Result should contain the results"
    assert "overview" in result, "Result should contain an overview"
    
    # Check that a query was generated
    assert "MATCH" in result["query"], "A Cypher query should have been generated"
    assert "SESSION" in result["query"], "The query should mention SESSION nodes"
    
    logger.info("✅ Dynamic mode test passed")
    return result

def test_variable_resolution(session_id):
    """Test variable resolution in queries"""
    logger.info("Testing variable resolution in queries")
    
    # Query using a variable reference
    result = cypher(
        query="MATCH (s:STEP) WHERE s.id = @{" + session_id + "}.test_step[0].value RETURN s",
        session_id=session_id,
        max_results=10
    )
    
    # Check that variable was resolved
    assert "query" in result, "Result should contain the query"
    assert "'test_value'" in result["query"], "Variable should be resolved to 'test_value'"
    
    logger.info("✅ Variable resolution test passed")
    return result

def test_safety_checks():
    """Test safety checks for write operations"""
    logger.info("Testing safety checks for write operations")
    
    # Write query with safety on
    result = cypher(
        query="CREATE (t:TEST_NODE {id: 'temp_test'})",
        safety_on=True,
        confirmed=False
    )
    
    # Check that confirmation is requested
    assert "waiting_for_input" in result, "Should request confirmation for write operation"
    assert "prompt" in result, "Confirmation request should have a prompt"
    assert "options" in result, "Confirmation request should have options"
    
    logger.info("✅ Safety checks test passed")
    return result

def test_write_operation_with_confirmation():
    """Test write operation with confirmation"""
    logger.info("Testing write operation with confirmation")
    
    # Write query with confirmation
    result = cypher(
        query="CREATE (t:TEST_NODE {id: 'temp_test'}) RETURN t",
        safety_on=True,
        confirmed=True
    )
    
    # Check result
    assert "query" in result, "Result should contain the query"
    assert "result" in result, "Result should contain the results"
    
    # Verify node was created
    session_manager = get_session_manager()
    with session_manager.driver.get_session() as session:
        count_result = session.run(
            "MATCH (t:TEST_NODE {id: 'temp_test'}) RETURN count(t) as count"
        ).single()
        assert count_result["count"] > 0, "Node should have been created"
    
    # Clean up the created node
    with session_manager.driver.get_session() as session:
        session.run("MATCH (t:TEST_NODE {id: 'temp_test'}) DELETE t")
    
    logger.info("✅ Write operation with confirmation test passed")
    return result

def test_error_handling():
    """Test error handling for invalid queries"""
    logger.info("Testing error handling for invalid queries")
    
    # Invalid query
    result = cypher(
        query="MATCH (s:INVALID_SYNTAX WHERE s.id = 'test' RETURN s",
        max_results=10
    )
    
    # Check error handling
    assert "error" in result, "Result should contain error information"
    assert "overview" in result, "Result should contain error overview"
    
    logger.info("✅ Error handling test passed")
    return result

def test_retry_mechanism():
    """Test retry mechanism for dynamic mode"""
    logger.info("Testing retry mechanism")
    
    # Deliberately generate an error in dynamic mode
    result = cypher(
        instruction="Find nodes with incorrect.syntax",
        max_retries=2  # Limit retries for test
    )
    
    # We expect either success after retry or error information if all retries failed
    assert "query" in result, "Result should contain the query"
    if "error" in result:
        assert "overview" in result, "Result should contain error overview"
    
    logger.info("✅ Retry mechanism test passed")
    return result

def test_result_size_limiting():
    """Test result size limiting"""
    logger.info("Testing result size limiting")
    
    # Query with small result limit
    result = cypher(
        query="MATCH (n) RETURN n LIMIT 100",
        max_results=3  # Set very low limit for testing
    )
    
    # Check if results were limited
    assert "result" in result, "Result should contain results"
    if len(result["result"]) > 0 and "_info" in result["result"][-1]:
        assert "limited" in result["result"][-1]["_info"], "Result should have limit info"
    
    logger.info("✅ Result size limiting test passed")
    return result

def main():
    """Run all tests"""
    logger.info("Starting cypher utility tests")
    
    try:
        # Setup test data
        session_id = setup_test_data()
        
        # Run tests
        test_results = {}
        
        try:
            # Test direct mode
            test_results["direct_mode"] = test_direct_mode()
            
            # Test dynamic mode
            test_results["dynamic_mode"] = test_dynamic_mode()
            
            # Test variable resolution
            test_results["variable_resolution"] = test_variable_resolution(session_id)
            
            # Test safety checks
            test_results["safety_checks"] = test_safety_checks()
            
            # Test write operation with confirmation
            test_results["write_operation"] = test_write_operation_with_confirmation()
            
            # Test error handling
            test_results["error_handling"] = test_error_handling()
            
            # Test retry mechanism
            test_results["retry_mechanism"] = test_retry_mechanism()
            
            # Test result size limiting
            test_results["result_limiting"] = test_result_size_limiting()
            
            logger.info("All tests completed successfully!")
            
        except AssertionError as e:
            logger.error(f"Test failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during tests: {e}", exc_info=True)
            raise
        finally:
            # Always clean up test data
            cleanup_test_data(session_id)
    
    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)
        sys.exit(1)
    
    logger.info("All tests passed! The cypher utility is working as expected.")

if __name__ == "__main__":
    main() 