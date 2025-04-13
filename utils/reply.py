"""
Reply utilities for workflow responses.
"""

import logging
import uuid
import time
import re
import os

logger = logging.getLogger(__name__)

def reply(message=None, content=None, llm_response=None, end_session=False, **kwargs):
    """
    Send a message to the user.
    
    Args:
        message: Primary message text to send
        content: Alternative message content (lower priority than message)
        llm_response: Response from the LLM (used if no direct message provided)
        end_session: Whether to end the session after this message
        **kwargs: Additional parameters to include in the result
        
    Returns:
        Result containing the message
    """
    # Determine which text to use in priority order
    if message:
        text = message
        logger.info("Using primary message for response")
    elif llm_response:
        text = llm_response
        logger.info("Using LLM response as fallback")
    else:
        text = content
        logger.info("Using content text")
    
    if not text:
        logger.warning("No message content provided to reply")
        text = "I don't have a response to provide at this time."
    
    # Return the result (app.py will handle adding to message history)
    result = {
        "message": text,
        "content": text,
        "end_session": end_session
    }
    
    # Add any extra fields
    for key, value in kwargs.items():
        result[key] = value
        
    return result

def format_reply(content, format_type="text", **kwargs):
    """
    Format a reply in a specific format
    
    Args:
        content: The content to format
        format_type: Format type (text, markdown, html)
        **kwargs: Additional formatting options
        
    Returns:
        Formatted response
    """
    if format_type == "markdown":
        return {
            "message": content,
            "format": "markdown"
        }
    elif format_type == "html":
        return {
            "message": content,
            "format": "html"
        }
    else:
        return {
            "message": content,
            "format": "text"
        }

def end_workflow(message=None):
    """
    End the workflow with an optional message
    
    Args:
        message: Final message to display
        
    Returns:
        End workflow response
    """
    return {
        "message": message,
        "end_conversation": True
    } 