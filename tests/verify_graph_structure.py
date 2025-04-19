#!/usr/bin/env python3
"""
Script to verify the actual graph structure in Neo4j against conversation_loop.cypher.
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

# Load environment variables
load_dotenv()

# Get Neo4j connection details
neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
neo4j_user = os.environ.get("NEO4J_USERNAME", "neo4j")
neo4j_password = os.environ.get("NEO4J_PASSWORD", "password")

def connect_to_neo4j():
    """Connect to the Neo4j database."""
    try:
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        # Verify connection
        with driver.session() as session:
            result = session.run("RETURN 'Connection successful' AS message")
            record = result.single()
            if record:
                logger.info(f"Connected to Neo4j: {record['message']}")
            else:
                logger.error("Connection test failed")
                return None
        return driver
    except Exception as e:
        logger.error(f"Error connecting to Neo4j: {e}")
        return None

def read_expected_structure():
    """Read the expected graph structure from conversation_loop.cypher."""
    try:
        with open("conversation_loop.cypher", "r") as f:
            cypher_content = f.read()
            logger.info("Successfully read conversation_loop.cypher")
            return cypher_content
    except Exception as e:
        logger.error(f"Error reading conversation_loop.cypher: {e}")
        return None

def get_actual_structure(driver):
    """Retrieve the actual graph structure from the Neo4j database."""
    nodes = {}
    relationships = []
    
    try:
        with driver.session() as session:
            # Get all STEP nodes
            result = session.run("""
                MATCH (n:STEP)
                RETURN n.id as id, n.description as description, 
                       n.function as function, n.input as input
            """)
            
            for record in result:
                node_id = record["id"]
                nodes[node_id] = {
                    "description": record["description"],
                    "function": record["function"],
                    "input": record["input"]
                }
            
            # Get all NEXT relationships
            result = session.run("""
                MATCH (s:STEP)-[r:NEXT]->(t:STEP)
                RETURN s.id as source, t.id as target, 
                       r.conditions as conditions
            """)
            
            for record in result:
                relationship = {
                    "source": record["source"],
                    "target": record["target"],
                    "conditions": record["conditions"]
                }
                relationships.append(relationship)
                
            logger.info(f"Retrieved {len(nodes)} nodes and {len(relationships)} relationships")
            return {"nodes": nodes, "relationships": relationships}
    except Exception as e:
        logger.error(f"Error reading graph structure: {e}")
        return None

def analyze_structure(nodes, relationships, cypher_content):
    """Compare the actual graph structure with the expected structure."""
    # Expected structure from cypher file (simplified analysis)
    expected_nodes = ["root", "request", "generate", "reply"]
    expected_relationships = [
        ("root", "request"),
        ("request", "generate"),
        ("generate", "reply"),
        ("reply", "request", True)  # With conditions
    ]
    
    # Check nodes
    missing_nodes = [node for node in expected_nodes if node not in nodes]
    extra_nodes = [node for node in nodes if node not in expected_nodes]
    
    if missing_nodes:
        logger.error(f"Missing nodes: {missing_nodes}")
    else:
        logger.info("All expected nodes are present")
    
    if extra_nodes:
        logger.warning(f"Extra nodes found: {extra_nodes}")
    
    # Check relationships
    relationship_map = {}
    for rel in relationships:
        source = rel["source"]
        target = rel["target"]
        has_conditions = rel["conditions"] is not None
        relationship_map[(source, target)] = has_conditions
    
    for source, target, conditional in expected_relationships:
        if (source, target) not in relationship_map:
            logger.error(f"Missing relationship: {source} -> {target}")
        elif conditional and not relationship_map[(source, target)]:
            logger.error(f"Relationship {source} -> {target} should have conditions but doesn't")
        elif not conditional and relationship_map[(source, target)]:
            logger.warning(f"Relationship {source} -> {target} has conditions but shouldn't")
    
    # Check for extra relationships
    for (source, target), has_conditions in relationship_map.items():
        found = False
        for exp_source, exp_target, exp_conditional in expected_relationships:
            if source == exp_source and target == exp_target:
                found = True
                break
        if not found:
            logger.warning(f"Extra relationship found: {source} -> {target}")
    
    # Detailed node properties check
    logger.info("\nDetailed node properties:")
    for node_id, properties in nodes.items():
        logger.info(f"\nNode: {node_id}")
        logger.info(f"  Description: {properties.get('description')}")
        logger.info(f"  Function: {properties.get('function')}")
        input_val = properties.get('input')
        if input_val:
            # Truncate long input values for readability
            if len(input_val) > 100:
                input_val = input_val[:100] + "..."
            logger.info(f"  Input: {input_val}")
    
    # Check conditional relationship details
    logger.info("\nRelationship details:")
    for rel in relationships:
        source = rel["source"]
        target = rel["target"]
        conditions = rel["conditions"]
        if conditions:
            logger.info(f"Relationship {source} -> {target} has conditions: {conditions}")
        else:
            logger.info(f"Relationship {source} -> {target} has no conditions")

def main():
    """Main function to verify graph structure."""
    driver = connect_to_neo4j()
    if not driver:
        logger.error("Failed to connect to Neo4j")
        return
    
    cypher_content = read_expected_structure()
    if not cypher_content:
        driver.close()
        return
    
    graph_structure = get_actual_structure(driver)
    if not graph_structure:
        driver.close()
        return
    
    analyze_structure(
        graph_structure["nodes"], 
        graph_structure["relationships"],
        cypher_content
    )
    
    driver.close()
    logger.info("Graph structure verification complete")

if __name__ == "__main__":
    main() 