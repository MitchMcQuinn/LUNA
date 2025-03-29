"""
Reply utilities for workflow responses.
"""

import logging

logger = logging.getLogger(__name__)

def reply(message=None, content=None, end_session=False, **kwargs):
    """
    Send a message to the user.
    
    Args:
        message: Message text to send
        content: Alternative message content (lower priority than message)
        end_session: Whether to end the session after this message
        **kwargs: Additional parameters to include in the result
        
    Returns:
        Result containing the message
    """
    # Use either message or content
    text = message or content
    
    if not text:
        logger.warning("No message content provided to reply")
        text = "I don't have a response to provide at this time."
        
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