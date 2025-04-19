"""
Test script with mock generate function.
"""

import os
import sys
import logging
import json
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

# Import utilities
from LUNA.utils.request import request
from LUNA.utils.reply import reply
from mock_generate import mock_generate

def test_workflow():
    """Test the complete workflow with mock generate function"""
    
    # 1. Initial greeting - simulate what happens at the root step
    greeting = "GM! How can I help?"
    request_result = request(prompt=greeting)
    logger.info(f"STEP 1 (ROOT + REQUEST): Request result: {json.dumps(request_result, indent=2)}")
    
    # 2. User input - simulate handle_user_input
    user_message = "Tell me about workflow engines"
    request_output = {"response": user_message}
    logger.info(f"USER INPUT: {user_message}")
    
    # 3. Generate step - use our mock function
    schema = {
        "type": "object",
        "properties": {
            "response": {"type": "string", "description": "A helpful response"},
            "followup": {"type": "string", "description": "A followup question"},
            "merits_followup": {"type": "boolean", "description": "Whether to continue"}
        },
        "required": ["response", "followup", "merits_followup"]
    }
    generate_result = mock_generate(user=user_message, schema=schema)
    logger.info(f"STEP 2 (GENERATE): Generate result: {json.dumps(generate_result, indent=2)}")
    
    # 4. Reply step
    reply_result = reply(message=generate_result["response"])
    logger.info(f"STEP 3 (REPLY): Reply result: {json.dumps(reply_result, indent=2)}")
    
    # 5. Check for loop - should we go back to request?
    if generate_result.get("merits_followup", False):
        followup_request = request(prompt=generate_result["followup"])
        logger.info(f"LOOP BACK: Next request with followup: {json.dumps(followup_request, indent=2)}")
    
    return {
        "request": request_result,
        "generate": generate_result,
        "reply": reply_result
    }

if __name__ == "__main__":
    logger.info("Testing workflow with mock generate function:")
    results = test_workflow()
    logger.info("Workflow test complete - this is what should happen in the real workflow") 