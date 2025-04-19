"""
Check the properties of NEXT relationships in the database.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set up path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)  # Add current directory to path

# Load environment
env_path = os.path.join(script_dir, '.env.local')
load_dotenv(env_path)

# Import core components
from core.session_manager import get_session_manager

def check_relationships():
    """Check the properties of NEXT relationships."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        # Get all relationships
        result = session.run("""
        MATCH ()-[r:NEXT]->() 
        RETURN DISTINCT keys(r) as properties
        """)
        
        print("Relationship property keys:")
        for record in result:
            print(f"  {record['properties']}")
            
        # Get all relationships with their source and target
        result = session.run("""
        MATCH (source:STEP)-[r:NEXT]->(target:STEP)
        RETURN source.id as source, target.id as target, properties(r) as props
        """)
        
        print("\nDetail of relationships:")
        for record in result:
            print(f"  {record['source']} -> {record['target']}: {record['props']}")
            
        # Check relationships from provide-answer step
        result = session.run("""
        MATCH (source:STEP {id: 'provide-answer'})-[r:NEXT]->(target:STEP)
        RETURN source.id as source, target.id as target, properties(r) as props
        """)
        
        print("\nRelationships from provide-answer:")
        for record in result:
            print(f"  {record['source']} -> {record['target']}: {record['props']}")

if __name__ == "__main__":
    check_relationships() 