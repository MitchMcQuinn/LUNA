#!/usr/bin/env python
"""
Analyze workflow structure and transitions to debug variable resolution issues.
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
    """Main function to analyze workflow structure"""
    try:
        from core.session_manager import get_session_manager
        sm = get_session_manager()
        
        with sm.driver.get_session() as session:
            # Check workflow steps
            result = session.run("""
                MATCH (w:WORKFLOW {id: 'discord_operator'})-[:HAS_STEP]->(s:STEP)
                RETURN s.id as step_id, s.function as function
                ORDER BY s.id
            """)
            
            steps = list(result)
            logger.info(f"Found {len(steps)} steps in discord_operator workflow:")
            for step in steps:
                logger.info(f"Step: {step['step_id']} - Function: {step['function']}")
            
            # Check workflow transitions
            result = session.run("""
                MATCH (w:WORKFLOW {id: 'discord_operator'})-[:HAS_TRANSITION]->(t)
                MATCH (t)-[:FROM]->(s1)
                MATCH (t)-[:TO]->(s2)
                RETURN s1.id as from_step, s2.id as to_step, t.id as transition_id, t.condition as condition
                ORDER BY from_step, to_step
            """)
            
            transitions = list(result)
            logger.info(f"\nFound {len(transitions)} transitions in discord_operator workflow:")
            for t in transitions:
                logger.info(f"Transition {t['transition_id']}: {t['from_step']} -> {t['to_step']}")
                if t['condition']:
                    logger.info(f"  Condition: {t['condition']}")
            
            # Check specific steps related to message logging
            for step_id in ['lookup_followup_session_id', 'send_session_followup_message']:
                result = session.run("""
                    MATCH (s:STEP {id: $step_id})
                    RETURN s.id, s.function, s.input
                """, {"step_id": step_id})
                
                record = result.single()
                if record:
                    logger.info(f"\nStep: {record['s.id']}")
                    logger.info(f"Function: {record['s.function']}")
                    logger.info(f"Input: {record['s.input']}")
                else:
                    logger.info(f"\nStep {step_id} not found in database")
            
            # Also check the actual step that's replacing send_session_followup_message
            result = session.run("""
                MATCH (s:STEP)
                WHERE s.id CONTAINS 'followup' AND s.id CONTAINS 'message'
                RETURN s.id, s.function, s.input
            """)
            
            records = list(result)
            logger.info(f"\nFound {len(records)} followup message steps:")
            for record in records:
                logger.info(f"Step: {record['s.id']}")
                logger.info(f"Function: {record['s.function']}")
                logger.info(f"Input: {record['s.input']}")
                
    except Exception as e:
        logger.error(f"Error analyzing workflow: {str(e)}")
        
if __name__ == "__main__":
    main() 