"""
Mock implementation of the generate utility for testing.
"""

import logging
import json
import os

logger = logging.getLogger(__name__)

def mock_generate(model="gpt-3.5-turbo", temperature=0.7, system=None, user=None, schema=None, **kwargs):
    """
    Mock implementation of the generate function that doesn't require an API key.
    
    Args:
        model: Model to use for generation
        temperature: Randomness of generation (0-1)
        system: System message for the model
        user: User message/prompt to send
        schema: JSON schema for structured output
        **kwargs: Additional parameters to pass to the model
        
    Returns:
        Mock response based on the input
    """
    logger.info(f"MOCK GENERATE called with model={model}, user={user}")
    
    # If no user input, return an error
    if user is None:
        return {
            "error": "Missing required user input",
            "message": "I couldn't process that request: Missing user input"
        }
    
    # Create a basic response
    if "workflow" in user.lower():
        response = {
            "response": "Workflow engines are software systems that automate and manage business processes. They coordinate the execution of tasks, handle dependencies between steps, and maintain state. Graph-based workflow engines like the one in this project use directed graphs to represent the flow of execution, with nodes representing tasks and edges representing transitions between tasks.",
            "followup": "Would you like to know more about how graph-based workflow engines differ from traditional workflow engines?",
            "merits_followup": True
        }
    else:
        response = {
            "response": f"Here's some information about {user}: This is a mock response because the OpenAI API key is not configured. In a real implementation, this would connect to an AI service to generate a proper response.",
            "followup": f"Would you like to know more about {user}?",
            "merits_followup": True
        }
    
    logger.info(f"MOCK GENERATE returning: {json.dumps(response, indent=2)}")
    return response

# Register this mock function
if __name__ == "__main__":
    # Test the mock function
    test_input = "Tell me about workflow engines"
    result = mock_generate(user=test_input)
    print(json.dumps(result, indent=2)) 