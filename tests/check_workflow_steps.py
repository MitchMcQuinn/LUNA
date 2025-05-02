#!/usr/bin/env python
"""
Check for workflow steps and missing files in the tools directory.
"""

import os
import sys
import json
import logging
from pathlib import Path
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

def main():
    """Main function to check workflow steps and missing files"""
    # Check tools directory for existing and missing files
    tools_dir = Path(parent_dir) / "utils" / "tools"
    logger.info(f"Checking tools directory: {tools_dir}")
    
    # List of tools to check for
    tools_to_check = [
        "log_initial_session_message.py",
        "log_followup_session_message.py",
        "lookup_channel_session.py",
        "lookup_followup_session_id.py",
        "send_session_followup_message.py"
    ]
    
    for tool in tools_to_check:
        tool_path = tools_dir / tool
        if tool_path.exists():
            logger.info(f"✅ Tool exists: {tool}")
            # Check file size to see if it's empty
            size = tool_path.stat().st_size
            logger.info(f"   Size: {size} bytes")
            if size == 0:
                logger.warning(f"   ⚠️ File is empty")
        else:
            logger.warning(f"❌ Tool DOES NOT exist: {tool}")
    
    # Check Neo4j database for workflow configuration
    try:
        from core.session_manager import get_session_manager
        sm = get_session_manager()
        
        with sm.driver.get_session() as session:
            # Get all steps in the discord_operator workflow
            result = session.run("""
                MATCH (w:WORKFLOW {id: 'discord_operator'})-[:HAS_STEP]->(s:STEP)
                RETURN s.id as step_id, s.function as function, s.input as input
                ORDER BY s.id
            """)
            
            steps = list(result)
            logger.info(f"Found {len(steps)} steps in discord_operator workflow:")
            for step in steps:
                step_id = step['step_id']
                function = step['function']
                input_data = step['input']
                
                logger.info(f"\nStep ID: {step_id}")
                logger.info(f"Function: {function}")
                logger.info(f"Input: {input_data}")
                
                # Parse input if it's a JSON string
                if input_data and isinstance(input_data, str):
                    try:
                        input_json = json.loads(input_data)
                        if 'file_path' in input_json:
                            file_path = input_json['file_path']
                            file_exists = (tools_dir / file_path).exists()
                            logger.info(f"References file: {file_path} - Exists: {file_exists}")
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse input as JSON")
                
    except Exception as e:
        logger.error(f"Error checking Neo4j: {e}")
        
if __name__ == "__main__":
    main() 