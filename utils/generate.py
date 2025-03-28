"""
LLM text generation utility functions.
"""

import os
import logging
import json

logger = logging.getLogger(__name__)

def generate(model="gpt-4o-mini", temperature=0.7, system=None, user=None, include_history=False, 
          directly_set_reply=False, schema=None, **kwargs):
    """
    Generate text using an AI model
    
    Args:
        model: Model to use for generation
        temperature: Randomness of generation (0-1)
        system: System message for the model
        user: User message/prompt to send
        include_history: Whether to include conversation history
        directly_set_reply: Whether to directly set reply in output
        schema: JSON schema for structured output
        **kwargs: Additional parameters to pass to the model
        
    Returns:
        Generated response (structured based on schema if provided)
    """
    # Check that we have required inputs
    if user is None:
        logger.error("Missing required user input for generation")
        return {
            "error": "Missing required user input",
            "message": "I'm sorry, I couldn't process that request: Missing user input"
        }
    
    try:
        import openai
        
        # Prepare messages
        messages = []
        
        # Add system message if provided
        if system:
            messages.append({"role": "system", "content": system})
        
        # Add user message - ensure it contains "json" word if using schema
        if schema and "json" not in user.lower():
            # Add JSON mention to user message for structured output
            user = f"{user} Please format your response as JSON."
            
        messages.append({"role": "user", "content": user})
        
        # Configure request parameters
        request_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        # Add function calling schema if provided
        if schema:
            request_params["response_format"] = {"type": "json_object"}
            if "functions" not in request_params:
                request_params["functions"] = [
                    {
                        "name": "generate_response",
                        "description": "Generate a response based on the schema",
                        "parameters": schema
                    }
                ]
            request_params["function_call"] = {"name": "generate_response"}
            
        # Add any additional parameters
        for key, value in kwargs.items():
            if key not in request_params:
                request_params[key] = value
        
        # Make the API call
        try:
            logger.info(f"Making OpenAI API call with model {model}")
            response = openai.chat.completions.create(**request_params)
            logger.info("OpenAI API call successful")
            
            # Extract content from the response
            completion = response.choices[0].message
            
            # Handle function calling responses
            if hasattr(completion, 'function_call') and completion.function_call:
                logger.info("Processing function call response")
                try:
                    function_args = json.loads(completion.function_call.arguments)
                    
                    # If directly setting reply, add special fields
                    if directly_set_reply and "response" in function_args:
                        function_args["message"] = function_args["response"]
                        function_args["content"] = function_args["response"]
                        
                    return function_args
                except Exception as e:
                    logger.error(f"Error parsing function call arguments: {e}")
                    return {
                        "error": f"Failed to parse function response: {e}",
                        "message": "I'm sorry, there was an error processing the response."
                    }
            else:
                # Direct text response
                text = completion.content
                logger.info(f"Generated text response: {text[:50]}...")
                
                # If directly setting reply, wrap in the expected format
                if directly_set_reply:
                    return {
                        "response": text,
                        "message": text,
                        "content": text,
                        "merits_followup": kwargs.get("merits_followup", True)
                    }
                    
                return text
                
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            return {
                "error": f"Text generation failed: {e}",
                "message": f"I'm sorry, I couldn't process that request: Text generation failed: {e}"
            }
            
    except ImportError:
        logger.error("OpenAI package not installed")
        return {
            "error": "OpenAI package not installed",
            "message": "I'm sorry, I couldn't process that request: OpenAI package not installed"
        }

def classify(text, categories, model="gpt-3.5-turbo", **kwargs):
    """
    Classify text into one of the provided categories
    
    Args:
        text: Text to classify
        categories: List of category names
        model: Model to use for classification
        
    Returns:
        Selected category
    """
    prompt = f"""Classify the following text into exactly one of these categories: {', '.join(categories)}
    
Text: {text}

Reply with just the category name, nothing else."""
    
    result = generate(prompt=prompt, model=model, max_tokens=50, temperature=0.3, **kwargs)
    
    # Clean up result to match a category
    result = result.strip().lower()
    
    # Find best match among categories
    for category in categories:
        if category.lower() in result:
            return category
    
    # Return raw result if no match
    return result

def extract_entities(text, entity_types, model="gpt-3.5-turbo", **kwargs):
    """
    Extract named entities from text
    
    Args:
        text: Source text
        entity_types: Dict mapping entity type names to descriptions
        model: Model to use
        
    Returns:
        Dict mapping entity types to lists of extracted values
    """
    type_descriptions = "\n".join([f"- {name}: {desc}" for name, desc in entity_types.items()])
    
    prompt = f"""Extract all entities of the following types from the text.
    
Entity types:
{type_descriptions}

Text: {text}

Format your response as a JSON object where keys are entity types and values are arrays of extracted entities."""

    schema = {
        "type": "object",
        "properties": {entity: {"type": "array", "items": {"type": "string"}} for entity in entity_types}
    }
    
    return generate(prompt=prompt, model=model, schema=schema, max_tokens=500, temperature=0.3, **kwargs) 