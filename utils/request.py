"""
Request utilities for workflow inputs.
"""

import logging

logger = logging.getLogger(__name__)

def request(prompt=None, options=None, query=None, response=None):
    """
    Request input from the user
    
    Args:
        prompt: Text prompt to display
        options: List of option choices
        query: Optional pre-filled question from a previous step
        response: Optional response if already provided
        
    Returns:
        Signal object indicating workflow should pause for input
    """
    # Enhanced logging to see exactly what's being returned
    logger.info(f"REQUEST UTILITY CALLED with: prompt={prompt}, query={query}")
    
    result = {
        "waiting_for_input": True,
        "prompt": prompt or query or "Input required:",
        "options": options,
        "query": query,
        "response": response
    }
    
    logger.info(f"REQUEST UTILITY RETURNING: {result}")
    return result
    
def confirm(message, confirm_text="Yes", cancel_text="No"):
    """
    Request a yes/no confirmation from the user
    
    Args:
        message: Message to show
        confirm_text: Text for confirmation option
        cancel_text: Text for cancel option
        
    Returns:
        Signal object with yes/no options
    """
    return request(
        prompt=message,
        options=[
            {"value": True, "text": confirm_text},
            {"value": False, "text": cancel_text}
        ]
    )
    
def select(prompt, choices, allow_custom=False):
    """
    Ask user to select from a list of choices
    
    Args:
        prompt: Text prompt to display
        choices: List of options (strings or {text, value} objects)
        allow_custom: Whether to allow custom input
        
    Returns:
        Signal object for selection
    """
    # Format choices consistently
    options = []
    
    for choice in choices:
        if isinstance(choice, str):
            options.append({"text": choice, "value": choice})
        elif isinstance(choice, dict) and "text" in choice:
            # Use existing dict, ensure it has value
            if "value" not in choice:
                choice["value"] = choice["text"]
            options.append(choice)
            
    return request(
        prompt=prompt,
        options={
            "choices": options,
            "allow_custom": allow_custom
        }
    ) 
def request_with_response(query=None, options=None, response=None):
    """
    Request input from the user, with response field
    
    Args:
        query: The question to ask
        options: Optional list of preset options
        response: Response from the user (when available)
        
    Returns:
        Request object with response field if available
    """
    result = {
        "waiting_for_input": True,
        "prompt": query,
        "options": options
    }
    
    # When a response is provided, include it
    if response:
        result["response"] = response
        logger.info(f"Request with response: {response}")
    
    return result
