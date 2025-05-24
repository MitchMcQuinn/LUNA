"""
Neo4j Database Connection Test

This test checks the connectivity to the Neo4j database using credentials
from the .env.local file. It performs various connection checks to help
diagnose any database connectivity issues.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError, ConfigurationError

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Neo4jConnectionTester:
    def __init__(self):
        self.uri = None
        self.username = None
        self.password = None
        self.driver = None
        
    def load_environment(self):
        """Load environment variables from .env.local file"""
        env_file = project_root / '.env.local'
        
        if not env_file.exists():
            logger.error(f"❌ Environment file not found: {env_file}")
            logger.info("💡 Please create a .env.local file with your Neo4j credentials")
            logger.info("   You can copy sample.env.local as a template")
            return False
            
        # Load environment variables
        load_dotenv(env_file)
        
        self.uri = os.getenv('NEO4J_URI')
        self.username = os.getenv('NEO4J_USERNAME') 
        self.password = os.getenv('NEO4J_PASSWORD')
        
        # Check if all required variables are set
        missing_vars = []
        if not self.uri:
            missing_vars.append('NEO4J_URI')
        if not self.username:
            missing_vars.append('NEO4J_USERNAME')
        if not self.password:
            missing_vars.append('NEO4J_PASSWORD')
            
        if missing_vars:
            logger.error(f"❌ Missing environment variables: {', '.join(missing_vars)}")
            return False
            
        logger.info("✅ Environment variables loaded successfully")
        logger.info(f"   URI: {self.uri}")
        logger.info(f"   Username: {self.username}")
        logger.info(f"   Password: {'*' * len(self.password)}")
        
        return True
        
    def test_driver_creation(self):
        """Test creating a Neo4j driver instance"""
        try:
            logger.info("🔧 Testing driver creation...")
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password),
                max_connection_lifetime=3600
            )
            logger.info("✅ Driver created successfully")
            return True
            
        except ConfigurationError as e:
            logger.error(f"❌ Configuration error: {e}")
            logger.info("💡 Check your NEO4J_URI format (should be bolt://... or neo4j://...)")
            return False
            
        except Exception as e:
            logger.error(f"❌ Unexpected error creating driver: {e}")
            return False
            
    def test_connection(self):
        """Test actual connection to the database"""
        if not self.driver:
            logger.error("❌ No driver available for connection test")
            return False
            
        try:
            logger.info("🔌 Testing database connection...")
            
            # Test connection with a simple query
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                record = result.single()
                
                if record and record["test"] == 1:
                    logger.info("✅ Database connection successful!")
                    return True
                else:
                    logger.error("❌ Unexpected query result")
                    return False
                    
        except ServiceUnavailable as e:
            logger.error(f"❌ Service unavailable: {e}")
            logger.info("💡 Possible issues:")
            logger.info("   - Database server is not running")
            logger.info("   - Network connectivity problems")
            logger.info("   - Incorrect URI or port")
            return False
            
        except AuthError as e:
            logger.error(f"❌ Authentication failed: {e}")
            logger.info("💡 Possible issues:")
            logger.info("   - Incorrect username or password")
            logger.info("   - User doesn't have required permissions")
            return False
            
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
            
    def test_database_info(self):
        """Get basic database information"""
        if not self.driver:
            return False
            
        try:
            logger.info("📊 Getting database information...")
            
            with self.driver.session() as session:
                # Get Neo4j version
                result = session.run("CALL dbms.components() YIELD name, versions")
                components = list(result)
                
                for component in components:
                    if component["name"] == "Neo4j Kernel":
                        version = component["versions"][0] if component["versions"] else "Unknown"
                        logger.info(f"   Neo4j Version: {version}")
                        
                # Get database name
                result = session.run("CALL db.info()")
                db_info = result.single()
                if db_info:
                    logger.info(f"   Database Name: {db_info.get('name', 'Unknown')}")
                    
                # Count nodes and relationships
                result = session.run("MATCH (n) RETURN count(n) as node_count")
                node_count = result.single()["node_count"]
                
                result = session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
                rel_count = result.single()["rel_count"]
                
                logger.info(f"   Nodes: {node_count}")
                logger.info(f"   Relationships: {rel_count}")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to get database info: {e}")
            return False
            
    def cleanup(self):
        """Close the driver connection"""
        if self.driver:
            try:
                self.driver.close()
                logger.info("🔒 Driver connection closed")
            except Exception as e:
                logger.error(f"❌ Error closing driver: {e}")
                
    def run_full_test(self):
        """Run the complete test suite"""
        logger.info("🚀 Starting Neo4j Connection Test")
        logger.info("=" * 50)
        
        success = True
        
        # Test 1: Load environment
        if not self.load_environment():
            return False
            
        # Test 2: Create driver
        if not self.test_driver_creation():
            success = False
            
        # Test 3: Test connection
        if success and not self.test_connection():
            success = False
            
        # Test 4: Get database info
        if success:
            self.test_database_info()
            
        # Cleanup
        self.cleanup()
        
        logger.info("=" * 50)
        if success:
            logger.info("🎉 All tests passed! Neo4j connection is working correctly.")
        else:
            logger.info("❌ Some tests failed. Please check the error messages above.")
            
        return success

def main():
    """Main test function"""
    tester = Neo4jConnectionTester()
    success = tester.run_full_test()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 