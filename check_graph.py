"""
Script to check the actual graph structure including all properties of nodes.
"""

import os
import sys
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Get the absolute path to the .env.local file
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env.local')
print(f"Looking for env file at: {env_path}")

# Load environment variables
load_dotenv(env_path)

# Print loaded env vars for debugging
print(f"NEO4J_URI: {os.environ.get('NEO4J_URI')}")
print(f"NEO4J_USERNAME: {os.environ.get('NEO4J_USERNAME')}")
print(f"NEO4J_PASSWORD: {'*****' if os.environ.get('NEO4J_PASSWORD') else 'Not set'}")

# Connect to Neo4j
uri = os.environ.get("NEO4J_URI")
username = os.environ.get("NEO4J_USERNAME")
password = os.environ.get("NEO4J_PASSWORD")

if not uri or not username or not password:
    print("Missing Neo4j connection details. Please check your .env.local file.")
    sys.exit(1)

driver = GraphDatabase.driver(uri, auth=(username, password))

def check_graph_structure():
    with driver.session() as session:
        # Check for STEP nodes with all their properties
        print("\n=== STEP Nodes with All Properties ===")
        result = session.run("""
        MATCH (s:STEP)
        RETURN s
        """)
        
        for record in result:
            node = record["s"]
            print(f"Node ID: {node.id}")
            print(f"Labels: {list(node.labels)}")
            print("Properties:")
            for key, value in node.items():
                print(f"  {key}: {value}")
            print("---")
            
        # Check for relationships with all properties
        print("\n=== Relationships with All Properties ===")
        result = session.run("""
        MATCH (s1:STEP)-[r]->(s2:STEP)
        RETURN s1.id as from, type(r) as type, r as relationship, s2.id as to
        """)
        
        for record in result:
            rel = record["relationship"]
            print(f"Relationship: {record['from']} -[{record['type']}]-> {record['to']}")
            print("Properties:")
            for key, value in rel.items():
                print(f"  {key}: {value}")
            print("---")
                
        # Get schema statistics
        print("\n=== Database Schema Statistics ===")
        try:
            result = session.run("""
            CALL db.schema.visualization()
            """)
            
            if result:
                record = result.single()
                if record:
                    print(f"Nodes: {record.get('nodes', [])}")
                    print(f"Relationships: {record.get('relationships', [])}")
        except Exception as e:
            print(f"Error getting schema visualization: {e}")

if __name__ == "__main__":
    try:
        check_graph_structure()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.close() 