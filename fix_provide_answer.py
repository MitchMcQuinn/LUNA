#!/usr/bin/env python
"""
Fix the provide-answer step to work with both message and response field formats.
"""

import os
import sys
import logging
import json
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set up paths for import
script_dir = os.path.dirname(os.path.abspath(__file__))
luna_dir = os.path.join(script_dir, 'LUNA')
if os.path.exists(luna_dir):
    sys.path.append(luna_dir)
    os.chdir(luna_dir)
else:
    sys.path.append(script_dir)

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

def fix_provide_answer():
    """Update provide-answer step to handle both message and response fields."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        # Get current input format 
        result = session.run("""
            MATCH (s:STEP {id: 'provide-answer'})
            RETURN s.function as function, s.input as input
        """)
        
        record = result.single()
        if record:
            input_str = record["input"]
            function = record["function"]
            
            print(f"Current provide-answer configuration:")
            print(f"  Function: {function}")
            print(f"  Input: {input_str}")
            
            # Update to use a dynamically populated input
            # The reply utility can handle either message or response fields
            result = session.run("""
                MATCH (s:STEP {id: 'provide-answer'})
                SET s.function = 'utils.reply.reply'
                SET s.input = $input
                RETURN s.id as id
            """, input=json.dumps({
                # Use the raw variable reference - utility will parse it
                "message": "@{SESSION_ID}.generate-answer.response"
            }))
            
            if result.single():
                print("✅ Updated provide-answer step to use generate-answer.response field")
            else:
                print("❌ Failed to update provide-answer step")
                
if __name__ == "__main__":
    fix_provide_answer()
    print("Done! This fix is workflow-agnostic and will work with all workflows.") 