"""
Direct test script for the generate function
"""

import os
import sys
import logging
import json

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("debug_generate")

def main():
    try:
        # Ensure we're in the right directory
        if not os.path.exists("utils/generate.py"):
            logger.error("utils/generate.py not found. Make sure you're running this from the LUNA directory.")
            return 1
        
        # Import the generate function
        logger.info("Importing generate function")
        sys.path.append(".")
        from utils.generate import generate
        
        # Test user parameter
        logger.info("===== TEST 1: user parameter =====")
        result = generate(user="Tell me about space")
        logger.info(f"Result with explicit 'user' parameter: {json.dumps(result, default=str)[:500]}")
        
        # Test response parameter (incorrect)
        logger.info("===== TEST 2: response parameter =====")
        result = generate(response="Tell me about space")
        logger.info(f"Result with incorrect 'response' parameter: {json.dumps(result, default=str)[:500]}")
        
        # Test different parameter names
        logger.info("===== TEST 3: different parameter name tests =====")
        test_params = [
            ("prompt", "Tell me about space"),
            ("message", "Tell me about space"),
            ("text", "Tell me about space"),
            ("query", "Tell me about space"),
            ("input", "Tell me about space")
        ]
        
        for param_name, param_value in test_params:
            logger.info(f"Testing parameter '{param_name}'")
            params = {param_name: param_value}
            result = generate(**params)
            success = "SUCCESS" if not (isinstance(result, dict) and "error" in result) else "FAILED"
            logger.info(f"Result with '{param_name}' parameter: {success}")
            logger.info(f"Output: {json.dumps(result, default=str)[:200]}...")
        
        # Test with complete parameter set
        logger.info("===== TEST 4: complete parameter set =====")
        result = generate(
            model="gpt-4o-mini",
            temperature=0.7,
            system="You are a helpful assistant",
            user="Tell me about space",
            include_history=False
        )
        logger.info(f"Result with complete parameter set: {json.dumps(result, default=str)[:500]}")
        
        # Test with **kwargs unpacking
        logger.info("===== TEST 5: kwargs unpacking =====")
        kwargs = {
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "user": "Tell me about space"
        }
        result = generate(**kwargs)
        logger.info(f"Result with kwargs unpacking: {json.dumps(result, default=str)[:500]}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error in debug script: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 