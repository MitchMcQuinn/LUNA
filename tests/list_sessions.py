#!/usr/bin/env python
"""
List session IDs from the Neo4j database.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set up paths
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
os.chdir(parent_dir)

# Load environment variables
env_path = os.path.join(os.getcwd(), '.env.local')
if os.path.exists(env_path):
    load_dotenv(env_path)
    logger.info(f"Loaded environment from: {env_path}")
else:
    logger.warning(f"No .env.local found at {env_path}")

# Import core components
try:
    from core.session_manager import get_session_manager
    logger.info("Successfully imported core components")
except ImportError as e:
    logger.error(f"Failed to import components: {e}")
    sys.exit(1)

def list_sessions():
    """List session IDs from the Neo4j database."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as db_session:
        print("\n=== SESSIONS WITH MESSAGES ===")
        result = db_session.run("""
            MATCH (s:SESSION)-[:HAS_MESSAGE]->(m:MESSAGE)
            RETURN DISTINCT s.id AS session_id, s.created_at as created_at
            ORDER BY s.created_at DESC
            LIMIT 5
        """)
        
        sessions_with_messages = list(result)
        for record in sessions_with_messages:
            print(f"- {record['session_id']} (created: {record['created_at']})")
        
        print("\n=== RECENT SESSIONS ===")
        result = db_session.run("""
            MATCH (s:SESSION)
            RETURN s.id AS session_id, s.created_at as created_at
            ORDER BY s.created_at DESC
            LIMIT 10
        """)
        
        recent_sessions = list(result)
        for record in recent_sessions:
            print(f"- {record['session_id']} (created: {record['created_at']})")
        
        print("\n=== SESSIONS WITH create_channel_session OUTPUT ===")
        result = db_session.run("""
            MATCH (s:SESSION)
            WHERE s.state CONTAINS 'create_channel_session'
            RETURN s.id AS session_id, s.created_at as created_at
            ORDER BY s.created_at DESC
            LIMIT 5
        """)
        
        create_channel_sessions = list(result)
        for record in create_channel_sessions:
            print(f"- {record['session_id']} (created: {record['created_at']})")

if __name__ == "__main__":
    list_sessions() 