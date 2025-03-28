"""
Neo4j database driver implementation using connection pooling.
"""

from neo4j import GraphDatabase
import os

class Neo4jDriver:
    def __init__(self, uri, username, password, max_connection_lifetime=3600):
        self.driver = GraphDatabase.driver(
            uri, 
            auth=(username, password),
            max_connection_lifetime=max_connection_lifetime
        )
        
    def get_session(self, database=None):
        return self.driver.session(database=database)
        
    def close(self):
        self.driver.close()

# Singleton pattern for Neo4j driver
_driver = None

def get_neo4j_driver():
    global _driver
    if _driver is None:
        uri = os.environ.get("NEO4J_URI")
        username = os.environ.get("NEO4J_USERNAME")
        password = os.environ.get("NEO4J_PASSWORD")
        _driver = Neo4jDriver(uri, username, password)
    return _driver 