#!/usr/bin/env python
"""
Check for the log_followup_session_message.py file and analyze workflow steps.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set up paths
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
os.chdir(parent_dir)

def main():
    """Main function to check for the file and analyze workflow"""
    # Check if log_followup_session_message.py exists
    tools_dir = Path(parent_dir) / "utils" / "tools"
    followup_file = tools_dir / "log_followup_session_message.py"
    
    logger.info(f"Checking for file: {followup_file}")
    
    if followup_file.exists():
        logger.info(f"File exists: {followup_file}")
        with open(followup_file, 'r') as f:
            content = f.read()
            logger.info(f"Content length: {len(content)}")
            logger.info(f"Content: \n{content}")
    else:
        logger.info(f"File DOES NOT exist: {followup_file}")
        
    # Check for related workflow steps in Neo4j
    try:
        from core.session_manager import get_session_manager
        sm = get_session_manager()
        
        with sm.driver.get_session() as session:
            # Check if step exists in workflow
            result = session.run("""
                MATCH (w:WORKFLOW)-[:HAS_STEP]->(s:STEP {id: 'log_followup_session_message'})
                RETURN w.id as workflow_id, s.id as step_id, s.function as function, s.input as input
            """)
            
            records = list(result)
            if records:
                logger.info(f"Found {len(records)} log_followup_session_message steps in workflows:")
                for record in records:
                    logger.info(f"  Workflow: {record['workflow_id']}")
                    logger.info(f"  Step ID: {record['step_id']}")
                    logger.info(f"  Function: {record['function']}")
                    logger.info(f"  Input: {record['input']}")
            else:
                logger.info("No log_followup_session_message steps found in any workflow")
                
            # Check what step is after lookup_channel_session in the discord_operator workflow
            result = session.run("""
                MATCH (w:WORKFLOW {id: 'discord_operator'})-[:HAS_STEP]->(s1:STEP {id: 'lookup_channel_session'})
                MATCH (w)-[:HAS_TRANSITION]->(t)-[:FROM]->(s1)
                MATCH (t)-[:TO]->(s2)
                RETURN s1.id as from_step, s2.id as to_step, t.condition as condition
            """)
            
            records = list(result)
            if records:
                logger.info(f"Steps after lookup_channel_session in the discord_operator workflow:")
                for record in records:
                    logger.info(f"  From: {record['from_step']} -> To: {record['to_step']}")
                    logger.info(f"  Condition: {record['condition']}")
            else:
                logger.info("No transitions found from lookup_channel_session")
                
    except Exception as e:
        logger.error(f"Error checking Neo4j: {e}")
        
if __name__ == "__main__":
    main() 