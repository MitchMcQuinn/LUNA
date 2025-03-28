"""
Variable resolution system for the workflow engine.
"""

import logging
import re

logger = logging.getLogger(__name__)

def resolve_variable(var_reference, session_state):
    """
    Resolve a variable reference from session state
    
    Args:
        var_reference: String in format '@{SESSION_ID}.step_id.field|default_value'
        session_state: Current session state object
    
    Returns:
        Resolved value or None if not found
    """
    if not isinstance(var_reference, str):
        # Not a string, return as-is
        return var_reference
        
    # Special handling for SESSION_ID placeholder
    if "@{SESSION_ID}" in var_reference:
        session_id = session_state.get("id")
        if session_id:
            var_reference = var_reference.replace("@{SESSION_ID}", f"@{{{session_id}}}")
            logger.debug(f"Replaced SESSION_ID placeholder: {var_reference}")
            
    # Check if this has a default value (indicated by pipe character)
    default_value = None
    if '|' in var_reference:
        var_parts = var_reference.split('|', 1)
        var_reference = var_parts[0].strip()
        default_value = var_parts[1].strip()
        logger.debug(f"Found default value: '{default_value}' for variable: '{var_reference}'")
        
    # Check if this is a variable reference
    if not var_reference.startswith('@{'):
        return var_reference
    
    # Extract variable path - handles formats like:
    # 1. @{session_id}.step_id.field
    # 2. @{session_id}.step_id
    # Log the full variable reference for debugging
    logger.debug(f"Resolving variable: {var_reference}")
    print(f"DEBUG VAR - Resolving variable: {var_reference}")
    
    try:
        # Extract the session ID part from @{...}
        session_id_match = re.match(r'@\{([^}]+)\}', var_reference)
        if not session_id_match:
            logger.warning(f"Invalid variable reference format: {var_reference}")
            print(f"DEBUG VAR - Invalid variable reference format: {var_reference}")
            return default_value
            
        # Get the session ID
        session_id = session_id_match.group(1)
        
        # Get the property path after the closing brace
        property_path = var_reference[var_reference.find('}')+1:]
        if property_path.startswith('.'):
            property_path = property_path[1:]  # Remove leading dot
            
        # Split the path to get step_id and fields
        parts = property_path.split('.')
        if not parts or len(parts) == 0:
            logger.warning(f"No property path in variable: {var_reference}")
            print(f"DEBUG VAR - No property path in variable: {var_reference}")
            return default_value
            
        # First part is the step_id
        step_id = parts[0]
        logger.debug(f"Looking for step: {step_id} in session outputs")
        print(f"DEBUG VAR - Looking for step: {step_id} in session outputs")
        
        # Print available outputs for debugging
        print(f"DEBUG VAR - Available outputs: {list(session_state['data']['outputs'].keys())}")
        
        # Check if step exists in outputs
        if step_id not in session_state["data"]["outputs"]:
            logger.debug(f"Step {step_id} not found in session outputs")
            print(f"DEBUG VAR - Step {step_id} not found in session outputs")
            return default_value
            
        # Get the step output value
        value = session_state["data"]["outputs"][step_id]
        logger.debug(f"Step {step_id} output: {value}")
        print(f"DEBUG VAR - Step {step_id} output: {value}")
        
        # Navigate through the rest of the path if any
        if len(parts) > 1:
            for field in parts[1:]:
                if isinstance(value, dict) and field in value:
                    value = value[field]
                    logger.debug(f"Accessing field {field}: {value}")
                    print(f"DEBUG VAR - Accessing field {field}: {value}")
                else:
                    logger.warning(f"Field {field} not found in {value}")
                    print(f"DEBUG VAR - Field {field} not found in {value}")
                    return default_value
                    
        logger.debug(f"Resolved variable {var_reference} to {value}")
        print(f"DEBUG VAR - Resolved variable {var_reference} to {value}")
        return value
    except Exception as e:
        logger.error(f"Error resolving variable {var_reference}: {e}")
        print(f"DEBUG VAR - Error resolving variable {var_reference}: {e}")
        return default_value

def resolve_inputs(input_spec, session_state):
    """
    Resolve all variables in an input specification
    
    Args:
        input_spec: Dictionary of input parameters
        session_state: Current session state
        
    Returns:
        Dictionary with resolved values or None if any required value couldn't be resolved
    """
    resolved = {}
    
    # Log what we're trying to resolve
    logger.debug(f"Resolving input spec: {input_spec}")
    
    for key, value in input_spec.items():
        resolved_value = resolve_variable(value, session_state)
        
        # Check if resolution failed for a required input
        if resolved_value is None and isinstance(value, str) and value.startswith('@{'):
            # Get variable parts to check specifically if this is a response field that exists but is None
            # This handles the case where get-question has a response field with None value
            var_reference = value
            if '|' in var_reference:
                var_parts = var_reference.split('|', 1)
                var_reference = var_parts[0].strip()
            
            # Extract step_id and field from the reference
            session_id_match = re.match(r'@\{([^}]+)\}', var_reference)
            if session_id_match:
                property_path = var_reference[var_reference.find('}')+1:]
                if property_path.startswith('.'):
                    property_path = property_path[1:]  # Remove leading dot
                
                parts = property_path.split('.')
                if len(parts) >= 2:
                    step_id = parts[0]
                    field = parts[1]
                    
                    # Check if the field exists and is explicitly None (as opposed to not existing)
                    if (step_id in session_state["data"]["outputs"] and 
                        isinstance(session_state["data"]["outputs"][step_id], dict) and
                        field in session_state["data"]["outputs"][step_id] and
                        session_state["data"]["outputs"][step_id][field] is None):
                        
                        # If this is a 'response' field with None value, signal that we need user input
                        if field == 'response':
                            # For response fields specifically, indicate we need user input
                            # by returning None for the entire input set
                            logger.info(f"Found response field in {step_id} with None value, awaiting user input")
                            return None
            
            logger.warning(f"Failed to resolve required input {key}: {value}")
            return None
            
        resolved[key] = resolved_value
        
    logger.debug(f"Resolved inputs: {resolved}")    
    return resolved 