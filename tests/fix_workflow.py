#!/usr/bin/env python
"""
Script to fix the path conditions in the workflow for the reimbursement request flow.
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
# Add parent directory (project root) to path
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
os.chdir(parent_dir)  # Change to project root directory

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

def fix_path_conditions():
    """Fix the path conditions in the workflow for the reimbursement request flow."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        logger.info("=== FIXING PATH CONDITIONS ===")
        
        # Update the path condition from generate_reimbursement_request to request-reimbursement
        # From: {"false":"@{SESSION_ID}.generate_reimbursement_request.is_complete"}
        # To: {"false":"@{SESSION_ID}.generate_reimbursement_request.reimbursement_requests[0].is_complete"}
        logger.info("Updating path condition for generate_reimbursement_request -> request-reimbursement")
        
        result = session.run("""
            MATCH (source:STEP {id: 'generate_reimbursement_request'})-[r:NEXT]->(target:STEP {id: 'request-reimbursement'})
            SET r.condition = $condition
            RETURN r
        """, condition='[{"false":"@{SESSION_ID}.generate_reimbursement_request.reimbursement_requests[0].is_complete"}]')
        
        if result.single():
            logger.info("Successfully updated path condition for generate_reimbursement_request -> request-reimbursement")
        else:
            logger.warning("Failed to update path condition for generate_reimbursement_request -> request-reimbursement")
        
        # Update the path condition from generate_reimbursement_request to reply_reimbursement_request
        # From: {"true":"@{SESSION_ID}.generate_reimbursement_request.is_complete"}
        # To: {"true":"@{SESSION_ID}.generate_reimbursement_request.reimbursement_requests[0].is_complete"}
        logger.info("Updating path condition for generate_reimbursement_request -> reply_reimbursement_request")
        
        result = session.run("""
            MATCH (source:STEP {id: 'generate_reimbursement_request'})-[r:NEXT]->(target:STEP {id: 'reply_reimbursement_request'})
            SET r.condition = $condition
            RETURN r
        """, condition='[{"true":"@{SESSION_ID}.generate_reimbursement_request.reimbursement_requests[0].is_complete"}]')
        
        if result.single():
            logger.info("Successfully updated path condition for generate_reimbursement_request -> reply_reimbursement_request")
        else:
            logger.warning("Failed to update path condition for generate_reimbursement_request -> reply_reimbursement_request")
        
        logger.info("Path condition fixes complete!")

if __name__ == "__main__":
    fix_path_conditions() 