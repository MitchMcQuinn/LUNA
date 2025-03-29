"""
Simple utility function tests.
"""

import sys
import os
import logging
import json
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Make sure modules can be imported
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

# Import utilities
from LUNA.utils.generate import generate
from LUNA.utils.request import request
from LUNA.utils.reply import reply

def test_request():
    """Test the request utility"""
    prompt = "GM! How can I help?"
    result = request(prompt=prompt)
    logger.info(f"Request result: {json.dumps(result, indent=2)}")
    return result

def test_generate():
    """Test the generate utility"""
    model = "gpt-3.5-turbo"  # Use a smaller model for testing
    temperature = 0.7
    user_input = "Tell me about workflow engines"
    schema = {
        "type": "object",
        "properties": {
            "response": {
                "type": "string", 
                "description": "A helpful and informative response to the user's query"
            },
            "followup": {
                "type": "string", 
                "description": "A natural followup question that builds on the conversation"
            },
            "merits_followup": {
                "type": "boolean", 
                "description": "Whether the conversation warrants continuation"
            }
        },
        "required": ["response", "followup", "merits_followup"]
    }
    
    # Try to generate a response
    try:
        result = generate(model=model, temperature=temperature, schema=schema, user=user_input)
        logger.info(f"Generate result: {json.dumps(result, indent=2)}")
        return result
    except Exception as e:
        logger.error(f"Error in generate: {e}")
        return {"error": str(e)}

def test_reply():
    """Test the reply utility"""
    message = "This is a test response"
    result = reply(message=message)
    logger.info(f"Reply result: {json.dumps(result, indent=2)}")
    return result

def test_complete_flow():
    """Test the complete flow from request to generate to reply"""
    # 1. Request
    request_result = test_request()
    logger.info("Step 1: Request completed")
    
    # 2. Generate
    user_input = "Tell me about workflow engines"
    logger.info(f"User input: {user_input}")
    generate_result = test_generate()
    logger.info("Step 2: Generate completed")
    
    # 3. Reply
    if "response" in generate_result:
        reply_result = reply(message=generate_result["response"])
    else:
        reply_result = reply(message="Sorry, I couldn't generate a proper response")
    logger.info("Step 3: Reply completed")
    
    return {
        "request": request_result,
        "generate": generate_result,
        "reply": reply_result
    }
    
if __name__ == "__main__":
    logger.info("Testing individual utilities:")
    logger.info("-" * 40)
    logger.info("Testing request utility:")
    test_request()
    
    logger.info("-" * 40)
    logger.info("Testing generate utility:")
    test_generate()
    
    logger.info("-" * 40)
    logger.info("Testing reply utility:")
    test_reply()
    
    logger.info("-" * 40)
    logger.info("Testing complete flow:")
    flow_results = test_complete_flow()
    logger.info("Testing complete") 