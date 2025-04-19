from neo4j import GraphDatabase
import os
import dotenv

dotenv.load_dotenv('.env.local')

uri = os.environ.get('NEO4J_URI')
username = os.environ.get('NEO4J_USERNAME')
password = os.environ.get('NEO4J_PASSWORD')

print(f'Testing connection to {uri} with username {username}')

try:
    driver = GraphDatabase.driver(uri, auth=(username, password))
    with driver.session() as session:
        result = session.run('MATCH (n) RETURN count(n) as count')
        print(f'Connection successful! Node count: {result.single()["count"]}')
except Exception as e:
    print(f'Connection failed: {str(e)}') 