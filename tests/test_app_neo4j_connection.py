"""
Application-Specific Neo4j Connection Test

This test uses the exact same connection method as the main application
to diagnose any potential differences in how the connection is established.
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

def test_app_neo4j_connection():
    """Test Neo4j connection using the same method as the main application"""
    
    logger.info("🔍 Testing Neo4j connection using app's connection method")
    logger.info("=" * 60)
    
    # Load environment variables the same way the app does
    env_file = project_root / '.env.local'
    if env_file.exists():
        load_dotenv(env_file)
        logger.info("✅ Loaded .env.local file")
    else:
        logger.error("❌ .env.local file not found")
        return False
    
    # Check environment variables
    uri = os.environ.get("NEO4J_URI")
    username = os.environ.get("NEO4J_USERNAME")
    password = os.environ.get("NEO4J_PASSWORD")
    
    logger.info(f"   NEO4J_URI: {uri}")
    logger.info(f"   NEO4J_USERNAME: {username}")
    logger.info(f"   NEO4J_PASSWORD: {'*' * len(password) if password else 'Not set'}")
    
    if not all([uri, username, password]):
        logger.error("❌ Missing required environment variables")
        return False
    
    try:
        # Import the app's database module
        logger.info("📦 Importing core.database module...")
        from core.database import get_neo4j_driver
        
        logger.info("🔧 Getting Neo4j driver using app's method...")
        driver = get_neo4j_driver()
        
        logger.info("🔌 Testing connection with app's driver...")
        with driver.get_session() as session:
            result = session.run("RETURN 'Hello from app driver!' as message")
            record = result.single()
            
            if record:
                logger.info(f"✅ Connection successful: {record['message']}")
                
                # Test a query similar to what the app might run
                result = session.run("MATCH (n) RETURN count(n) as total_nodes")
                node_count = result.single()["total_nodes"]
                logger.info(f"📊 Total nodes in database: {node_count}")
                
                return True
            else:
                logger.error("❌ No result from test query")
                return False
                
    except ImportError as e:
        logger.error(f"❌ Failed to import core.database: {e}")
        logger.info("💡 This might indicate a circular import issue")
        return False
        
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        logger.info(f"💡 Error type: {type(e).__name__}")
        return False
    
    finally:
        # Clean up
        try:
            if 'driver' in locals():
                driver.close()
                logger.info("🔒 Driver connection closed")
        except:
            pass

def main():
    """Main test function"""
    logger.info("🚀 Starting App-Specific Neo4j Connection Test")
    success = test_app_neo4j_connection()
    
    logger.info("=" * 60)
    if success:
        logger.info("🎉 App's Neo4j connection is working correctly!")
    else:
        logger.info("❌ App's Neo4j connection has issues.")
        logger.info("💡 Try running the standalone test: python tests/test_neo4j_connection.py")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 