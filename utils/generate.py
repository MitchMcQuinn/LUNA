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
    # Debug log the user input
    logger.info(f"DEBUG - User input received: '{user}'")
    logger.info(f"DEBUG - Is variable reference? {bool(isinstance(user, str) and '@{SESSION_ID}' in user)}")
    
    # Check if user input looks like an unresolved variable
    if user is not None and isinstance(user, str) and (user.startswith('@{') or user.startswith('${')) and ('}' in user):
        logger.error(f"User input appears to be an unresolved variable: {user}")
        error_response = {
            "error": "Unresolved variable in user input",
            "message": f"I'm sorry, I couldn't process that request: Variable {user} was not resolved"
        }
        
        # Add required schema fields with defaults if schema is provided
        if schema and "required" in schema and "properties" in schema:
            for field in schema["required"]:
                if field not in error_response and field in schema["properties"]:
                    prop_type = schema["properties"][field].get("type")
                    if prop_type == "boolean":
                        error_response[field] = False
                    elif prop_type == "string":
                        error_response[field] = f"Error: No {field}"
                    elif prop_type == "number" or prop_type == "integer":
                        error_response[field] = 0
                    else:
                        error_response[field] = None
            
            logger.warning(f"Added default values for required schema fields to error response: {list(error_response.keys())}")
        
        logger.error(f"Generation failed: {error_response}")
        return error_response
    
    # Check that we have required inputs
    if user is None:
        error_response = {
            "error": "Missing required user input",
            "message": "I'm sorry, I couldn't process that request: Missing user input"
        }
        
        # Add required schema fields with defaults if schema is provided
        if schema and "required" in schema and "properties" in schema:
            for field in schema["required"]:
                if field not in error_response and field in schema["properties"]:
                    prop_type = schema["properties"][field].get("type")
                    if prop_type == "boolean":
                        error_response[field] = False
                    elif prop_type == "string":
                        error_response[field] = f"Error: No {field}"
                    elif prop_type == "number" or prop_type == "integer":
                        error_response[field] = 0
                    else:
                        error_response[field] = None
            
            logger.warning(f"Added default values for required schema fields to error response: {list(error_response.keys())}")
        
        logger.error(f"Generation failed: {error_response}")
        return error_response
    
    try:
        import openai
        
        # Prepare messages
        messages = []
        
        # Add system message if provided
        if system:
            messages.append({"role": "system", "content": system})
        
        # Add conversation history if enabled
        if include_history:
            # Try to get history from kwargs
            history = kwargs.pop('history', None)
            if history:
                logger.info(f"Including conversation history ({len(history)} messages)")
                # If history is a string, try to parse it as JSON
                if isinstance(history, str):
                    try:
                        history = json.loads(history)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse history as JSON: {history[:100]}...")
                
                # Add each history message to the messages array
                if isinstance(history, list):
                    for msg in history:
                        if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                            # Skip any internal fields starting with underscore
                            cleaned_msg = {k: v for k, v in msg.items() 
                                          if not k.startswith('_') and k in ['role', 'content']}
                            messages.append(cleaned_msg)
                else:
                    logger.warning(f"History is not a list: {type(history)}")
        
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
                    
                    # Generic schema validation (field-agnostic)
                    if schema and "properties" in schema and "required" in schema:
                        missing_fields = []
                        for field in schema["required"]:
                            if field not in function_args:
                                missing_fields.append(field)
                                # Add reasonable defaults based on field type
                                if field in schema["properties"]:
                                    prop_type = schema["properties"][field].get("type")
                                    if prop_type == "boolean":
                                        function_args[field] = True
                                    elif prop_type == "string":
                                        function_args[field] = f"Default {field} value"
                                    elif prop_type == "number" or prop_type == "integer":
                                        function_args[field] = 0
                                    else:
                                        function_args[field] = None
                        
                        if missing_fields:
                            logger.warning(f"Model response missing required fields: {missing_fields}. Added defaults.")
                    
                    # Remove the special handling that references specific variable names
                    
                    logger.info(f"Function response fields: {list(function_args.keys())}")
                    
                    # Specifically log merits_followup value for debugging
                    if "merits_followup" in function_args:
                        logger.info(f"merits_followup value: {function_args['merits_followup']} (type: {type(function_args['merits_followup']).__name__})")
                    else:
                        logger.warning("merits_followup field is MISSING from response")
                    
                    # Log full response for debugging
                    logger.info(f"Full function response: {json.dumps(function_args, default=str)[:500]}")
                    
                    # Log the complete output
                    logger.info(f"GENERATION OUTPUT: {json.dumps(function_args, default=str)}")
                    return function_args
                except Exception as e:
                    error_response = {
                        "error": f"Failed to parse function response: {e}",
                        "message": "I'm sorry, there was an error processing the response."
                    }
                    logger.error(f"Generation failed: {error_response}")
                    return error_response
            else:
                # Direct text response
                text = completion.content
                logger.info(f"Generated text response: {text[:50]}...")
                
                # If directly setting reply, wrap in the expected format
                if directly_set_reply:
                    result = {
                        "response": text,
                        "message": text,
                        "content": text
                    }
                    logger.info(f"GENERATION OUTPUT: {json.dumps(result, default=str)}")
                    return result
                
                # If schema exists, create structured response following schema requirements
                if schema and "properties" in schema:
                    # Build response with text in "response" field if it exists in schema
                    structured_response = {}
                    
                    # Try to place the text in the most appropriate field
                    if "response" in schema["properties"]:
                        structured_response["response"] = text
                    elif "content" in schema["properties"]:
                        structured_response["content"] = text
                    elif "message" in schema["properties"]:
                        structured_response["message"] = text
                    else:
                        # Just use the first string property
                        for field, prop in schema["properties"].items():
                            if prop.get("type") == "string":
                                structured_response[field] = text
                                break
                    
                    # Add required fields with defaults based on their types
                    if "required" in schema:
                        for field in schema["required"]:
                            if field not in structured_response and field in schema["properties"]:
                                prop_type = schema["properties"][field].get("type")
                                if prop_type == "boolean":
                                    structured_response[field] = True
                                elif prop_type == "string":
                                    structured_response[field] = f"Default {field} value"
                                elif prop_type == "number" or prop_type == "integer":
                                    structured_response[field] = 0
                                else:
                                    structured_response[field] = None
                    
                    logger.info(f"Created structured response with fields: {list(structured_response.keys())}")
                    
                    # Add detailed logging for merits_followup in structured responses
                    if "merits_followup" in structured_response:
                        logger.info(f"merits_followup value: {structured_response['merits_followup']} (type: {type(structured_response['merits_followup']).__name__})")
                    else:
                        logger.warning("merits_followup field is MISSING from structured response")
                    
                    # Log full response for debugging
                    logger.info(f"Full structured response: {json.dumps(structured_response, default=str)[:500]}")
                    
                    # Log the complete output
                    logger.info(f"GENERATION OUTPUT: {json.dumps(structured_response, default=str)}")
                    return structured_response
                
                # No schema provided, return text as-is
                logger.info(f"GENERATION OUTPUT: {text}")
                return text
                
        except Exception as e:
            error_response = {
                "error": f"Text generation failed: {e}",
                "message": f"I'm sorry, I couldn't process that request: Text generation failed: {e}"
            }
            logger.error(f"Generation failed: {error_response}")
            return error_response
            
    except ImportError:
        error_response = {
            "error": "OpenAI package not installed",
            "message": "I'm sorry, I couldn't process that request: OpenAI package not installed"
        }
        logger.error(f"Generation failed: {error_response}")
        return error_response

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