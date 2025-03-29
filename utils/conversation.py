"""
Conversation history utilities for working with workflow session data.
"""

import logging

logger = logging.getLogger(__name__)

def get_conversation_history(data=None):
    """
    Extract and format conversation history from session data
    
    Args:
        data: Session data dictionary containing messages array
        
    Returns:
        List of formatted conversation messages ready for LLM context
    """
    if not data or not isinstance(data, dict):
        logger.warning("No valid data provided for conversation history")
        return []
        
    # Extract messages from data structure
    messages = data.get("messages", [])
    
    if not messages or not isinstance(messages, list):
        logger.warning(f"No messages found in data or invalid format: {type(messages)}")
        return []
    
    # Filter to include only standard message types with role and content
    # Strip internal metadata fields (starting with _)
    formatted_messages = []
    for msg in messages:
        if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
            # Create clean message with only required fields
            formatted_msg = {
                "role": msg["role"],
                "content": msg["content"]
            }
            formatted_messages.append(formatted_msg)
    
    logger.info(f"Extracted {len(formatted_messages)} conversation messages")
    return formatted_messages 