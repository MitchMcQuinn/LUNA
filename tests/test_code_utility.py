"""
Test script for the code execution utility.
"""

import os
import sys
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.code import code

def test_basic_execution():
    """Test basic code execution without variables"""
    
    # Simple code that sets a result variable
    code_snippet = """
# Calculate a result
x = 10
y = 20
result = {"sum": x + y, "product": x * y}
"""
    
    # Execute the code
    response = code(code_snippet)
    
    # Print the result
    logger.info(f"Basic execution result: {json.dumps(response, indent=2)}")
    assert response["result"] == {"sum": 30, "product": 200}
    assert response["error"] is None
    
    return response

def test_variable_resolution():
    """Test code execution with variable resolution"""
    
    # Mock session state
    session_state = {
        "data": {
            "outputs": {
                "data_step": [
                    {"numbers": [5, 10, 15], "text": "Hello world"}
                ]
            }
        }
    }
    
    # Code with variable references
    code_snippet = """
# Get data from previous step
numbers = @{SESSION_ID}.data_step.numbers
message = @{SESSION_ID}.data_step.text

# Process the data
result = {
    "processed_numbers": [n * 2 for n in numbers],
    "message_length": len(message),
    "message_upper": message.upper()
}
"""
    
    # Execute the code with session state
    response = code(code_snippet, session_id="test-session", session_state=session_state)
    
    # Print the result
    logger.info(f"Variable resolution result: {json.dumps(response, indent=2)}")
    assert response["result"]["processed_numbers"] == [10, 20, 30]
    assert response["result"]["message_length"] == 11
    assert response["result"]["message_upper"] == "HELLO WORLD"
    
    return response

def test_env_vars():
    """Test code execution with environment variables"""
    
    # Set a test environment variable
    os.environ["TEST_VAR"] = "test_value"
    
    # Code that uses environment variables
    code_snippet = """
# Access environment variables
env_value = os.environ.get("TEST_VAR", "not found")

# Use directly provided env vars
direct_value = TEST_VAR if "TEST_VAR" in globals() else "not provided"

result = {
    "from_os_environ": env_value,
    "from_direct_access": direct_value
}
"""
    
    # Execute the code with environment variables
    response = code(code_snippet, env_vars=["TEST_VAR"])
    
    # Print the result
    logger.info(f"Environment variable result: {json.dumps(response, indent=2)}")
    assert response["result"]["from_os_environ"] == "test_value"
    assert response["result"]["from_direct_access"] == "test_value"
    
    return response

def test_error_handling():
    """Test error handling in code execution"""
    
    # Code with an error
    code_snippet = """
# This will cause a division by zero error
x = 10
y = 0
result = {"quotient": x / y}
"""
    
    # Execute the code
    response = code(code_snippet)
    
    # Print the result
    logger.info(f"Error handling result: {response['error']}")
    assert response["result"] is None
    assert "division by zero" in response["error"]
    assert response["traceback"] is not None
    
    return response

def test_invalid_json_result():
    """Test handling of non-JSON-serializable results"""
    
    # Code that produces a non-serializable result
    code_snippet = """
# Create a complex object with circular reference
class CircularReference:
    def __init__(self):
        self.myself = self

# This will fail JSON serialization
result = CircularReference()
"""
    
    # Execute the code
    response = code(code_snippet)
    
    # Print the result
    logger.info(f"Invalid JSON result: {response['error']}")
    assert response["result"] is None
    assert "not JSON serializable" in response["error"]
    
    return response

def run_all_tests():
    """Run all test cases"""
    
    tests = [
        test_basic_execution,
        test_variable_resolution,
        test_env_vars,
        test_error_handling,
        test_invalid_json_result
    ]
    
    results = {}
    for test in tests:
        logger.info(f"\n=== Running test: {test.__name__} ===")
        try:
            result = test()
            results[test.__name__] = "PASS"
        except Exception as e:
            logger.error(f"Test failed: {e}")
            results[test.__name__] = f"FAIL: {str(e)}"
    
    # Print summary
    logger.info("\n=== Test Results ===")
    for test_name, result in results.items():
        logger.info(f"{test_name}: {result}")

if __name__ == "__main__":
    run_all_tests() 