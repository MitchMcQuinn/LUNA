"""
Script to check the current database state.
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv('LUNA/.env.local')

# Connect to Neo4j
uri = os.environ.get("NEO4J_URI")
username = os.environ.get("NEO4J_USERNAME")
password = os.environ.get("NEO4J_PASSWORD")

driver = GraphDatabase.driver(uri, auth=(username, password))

def check_database():
    with driver.session() as session:
        # Check for SESSION nodes
        result = session.run("MATCH (s:SESSION) RETURN count(s) as count")
        session_count = result.single()["count"]
        print(f"Number of SESSION nodes: {session_count}")
        
        # Check for STEP nodes
        result = session.run("MATCH (s:STEP) RETURN count(s) as count")
        step_count = result.single()["count"]
        print(f"Number of STEP nodes: {step_count}")
        
        # List all STEP nodes
        print("\nAll STEP nodes:")
        result = session.run("""
        MATCH (s:STEP)
        RETURN s.id, s.utility, s.input
        """)
        
        for record in result:
            print(f"ID: {record['s.id']}, Utility: {record['s.utility']}, Input: {record['s.input']}")
        
        # Check relationships
        print("\nRelationships:")
        result = session.run("""
        MATCH (s1:STEP)-[r:NEXT]->(s2:STEP)
        RETURN s1.id, s2.id, r.condition, r.operator
        """)
        
        for record in result:
            print(f"{record['s1.id']} -> {record['s2.id']}, Condition: {record['r.condition']}, Operator: {record['r.operator']}")

if __name__ == "__main__":
    try:
        check_database()
    finally:
        driver.close() 