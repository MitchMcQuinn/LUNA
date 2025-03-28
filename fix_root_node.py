#!/usr/bin/env python
"""
Fix the root node in the Neo4j database by adding the required function property.
"""

import logging
from core.database import get_neo4j_driver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_root_node():
    """Update the root node with function and input properties"""
    driver = get_neo4j_driver()
    
    with driver.get_session() as session:
        # First check if root node exists
        result = session.run("""
        MATCH (s:STEP {id: 'root'})
        RETURN s
        """)
        
        record = result.single()
        if not record:
            logger.error("Root node not found in database")
            return False
            
        node = record["s"]
        logger.info(f"Found root node with properties: {dict(node)}")
        
        # Check if function is missing
        if node.get("function") is None:
            # Update the root node to properly connect to get-question
            session.run("""
            MATCH (s:STEP {id: 'root'})
            SET s.function = 'utils.request.request',
                s.input = '{"prompt": "How can I help you today?"}'
            """)
            
            logger.info("✅ Updated root node with function and input properties")
            
            # Verify the update
            verify = session.run("""
            MATCH (s:STEP {id: 'root'})
            RETURN s.function, s.input
            """)
            
            rec = verify.single()
            if rec:
                logger.info(f"Root node now has function={rec['s.function']} and input={rec['s.input']}")
            
            return True
        else:
            logger.info(f"Root node already has function: {node.get('function')}")
            return False

if __name__ == "__main__":
    logger.info("Starting to fix root node...")
    success = fix_root_node()
    logger.info(f"Fix completed with success={success}") 