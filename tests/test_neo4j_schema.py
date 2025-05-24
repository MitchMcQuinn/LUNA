"""
Neo4j Schema Test

This test checks the Neo4j database schema to identify missing properties
that were mentioned in the application logs as warnings.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_neo4j_schema():
    """Test Neo4j schema and check for missing properties"""
    
    logger.info("🔍 Testing Neo4j Schema")
    logger.info("=" * 50)
    
    try:
        # Load environment variables
        env_file = project_root / '.env.local'
        if env_file.exists():
            load_dotenv(env_file)
            logger.info("✅ Loaded .env.local file")
        
        # Import Neo4j driver
        from core.database import get_neo4j_driver
        driver = get_neo4j_driver()
        
        with driver.get_session() as session:
            
            # Check STEP nodes and their properties
            logger.info("📊 Checking STEP nodes and properties...")
            result = session.run("""
                MATCH (s:STEP)
                RETURN s.id as id, 
                       s.function as function, 
                       s.input as input,
                       keys(s) as all_properties
                LIMIT 5
            """)
            
            step_records = list(result)
            if step_records:
                logger.info(f"Found {len(step_records)} STEP nodes (showing first 5):")
                
                for i, record in enumerate(step_records):
                    logger.info(f"  Step {i+1}:")
                    logger.info(f"    ID: {record['id']}")
                    logger.info(f"    Function: {record['function']}")
                    logger.info(f"    Input: {record['input']}")
                    logger.info(f"    All properties: {record['all_properties']}")
                    
                logger.info("✅ STEP nodes found with function properties")
                    
            else:
                logger.warning("⚠️  No STEP nodes found in database")
                
            # Check for specific discord_operator step
            logger.info("📊 Checking discord_operator step...")
            result = session.run("""
                MATCH (s:STEP {id: 'discord_operator'})
                RETURN s.id as step_id, 
                       s.function as function,
                       s.description as description
            """)
            
            discord_steps = list(result)
            if discord_steps:
                logger.info(f"Found discord_operator step:")
                for step in discord_steps:
                    logger.info(f"  {step['step_id']}: {step['function']} - {step['description']}")
            else:
                logger.warning("⚠️  No discord_operator step found")
                
        return True
        
    except Exception as e:
        logger.error(f"❌ Schema test failed: {e}")
        return False

def main():
    """Main test function"""
    logger.info("🚀 Starting Neo4j Schema Test")
    success = test_neo4j_schema()
    
    logger.info("=" * 50)
    if success:
        logger.info("🎉 Schema test completed!")
    else:
        logger.info("❌ Schema test failed.")
        
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 