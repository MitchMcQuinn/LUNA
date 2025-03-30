"""
Variable resolution system for the workflow engine.
"""

import logging
import re
import json

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
        return var_reference
    
    # For debugging
    logger.debug(f"Resolving variable reference: {var_reference}")
    
    # Extract default value if present
    default_value = None
    if '|' in var_reference:
        parts = var_reference.split('|', 1)
        var_reference = parts[0].strip()
        default_value = parts[1].strip()
        logger.debug(f"Found default value: {default_value}")
    
    # Check if this is a SESSION_ID variable reference
    if not '@{SESSION_ID}' in var_reference:
        return var_reference
    
    # Replace SESSION_ID with empty string and parse the path directly
    var_path = var_reference.replace('@{SESSION_ID}.', '')
    
    # Split the path into components
    path_parts = var_path.split('.')
    if len(path_parts) < 1:
        logger.warning(f"Invalid variable path: {var_path}")
        return default_value
    
    # First part is the step ID
    step_id = path_parts[0]
    logger.debug(f"Resolving from step: {step_id}")
    
    # Check for indexed access - e.g., step_id[2]
    index = None
    if '[' in step_id and ']' in step_id:
        match = re.search(r'(.+?)\[(\d+)\]', step_id)
        if match:
            step_id = match.group(1)
            try:
                index = int(match.group(2))
                logger.debug(f"Found indexed access: step={step_id}, index={index}")
            except ValueError:
                logger.warning(f"Invalid index format in {step_id}")
    
    # Check if outputs exist in session state
    if 'data' not in session_state or 'outputs' not in session_state['data']:
        logger.warning("Session state has no outputs section")
        return default_value
    
    if step_id not in session_state['data']['outputs']:
        logger.warning(f"Step {step_id} not found in outputs")
        return default_value
    
    # Get step output
    step_output = session_state['data']['outputs'][step_id]
    
    # Handle array-based outputs
    if isinstance(step_output, list):
        if not step_output:
            logger.warning(f"Step {step_id} has empty outputs array")
            return default_value
        
        # Get specific indexed item or most recent
        if index is not None:
            if 0 <= index < len(step_output):
                output = step_output[index]
                logger.debug(f"Using indexed output {index}")
            else:
                logger.warning(f"Index {index} out of range for step {step_id}")
                return default_value
        else:
            # Get most recent by default
            output = step_output[-1]
            logger.debug("Using most recent output")
    else:
        # Handle non-array format (backward compatibility)
        output = step_output
        logger.debug("Using non-array output")
    
    # Get field if specified
    if len(path_parts) > 1:
        # Extract field path
        field_path = path_parts[1:]
        current = output
        
        # Navigate through nested fields
        for field in field_path:
            if isinstance(current, dict) and field in current:
                current = current[field]
                logger.debug(f"Extracted field: {field}")
            else:
                logger.warning(f"Field '{field}' not found in output from step {step_id}")
                return default_value
        
        return current
    
    # Return the full output if no field specified
    return output

def resolve_template_string(template, session_state):
    """
    Resolve a template string containing embedded variable references.
    
    Args:
        template: String with embedded variables like "Text @{SESSION_ID}.step.field text"
        session_state: Current session state object
    
    Returns:
        String with all variable references replaced with their values
    """
    if not isinstance(template, str) or '@{SESSION_ID}' not in template:
        return template
    
    logger.debug(f"Resolving template string: {template}")
    
    # Pattern to match variable references: @{SESSION_ID}.step_id[index].field|default
    var_pattern = r'(@\{SESSION_ID\}(?:\.[a-zA-Z0-9_-]+)(?:\[\d+\])?(?:\.[a-zA-Z0-9_-]+)*(?:\|[^@\s]+)?)'
    
    # Find all variable references in the template
    matches = re.finditer(var_pattern, template)
    result = template
    
    # Process each match
    for match in matches:
        var_reference = match.group(0)
        logger.debug(f"Found embedded variable: {var_reference}")
        
        # Resolve the variable
        resolved_value = resolve_variable(var_reference, session_state)
        
        # If resolution failed and no default, return None
        if resolved_value is None:
            logger.warning(f"Failed to resolve embedded variable: {var_reference}")
            if '|' not in var_reference:
                return None
        
        # Convert resolved value to string for substitution
        if resolved_value is not None:
            if not isinstance(resolved_value, str):
                resolved_value = str(resolved_value)
            
            # Replace the variable reference with the resolved value
            result = result.replace(var_reference, resolved_value)
    
    logger.debug(f"Resolved template: {result}")
    return result

def resolve_inputs(input_spec, session_state):
    """
    Resolve all variables in an input specification
    
    Args:
        input_spec: Dictionary of input parameters
        session_state: Current session state
        
    Returns:
        Dictionary with resolved values or None if any required value couldn't be resolved
    """
    if not input_spec:
        return {}
    
    resolved = {}
    
    # Process input parameters
    for key, value in input_spec.items():
        # Handle nested dictionaries recursively
        if isinstance(value, dict):
            nested = resolve_inputs(value, session_state)
            if nested is None:
                logger.warning(f"Failed to resolve nested input for {key}")
                return None
            resolved[key] = nested
            continue
        
        # Handle list values
        if isinstance(value, list):
            resolved_list = []
            list_failed = False
            
            for item in value:
                if isinstance(item, str) and '@{SESSION_ID}' in item:
                    # Check if this is a template string with embedded variables
                    if re.search(r'[^@].*@\{SESSION_ID\}.*[^}]', item):
                        resolved_item = resolve_template_string(item, session_state)
                    else:
                        resolved_item = resolve_variable(item, session_state)
                    
                    if resolved_item is None:
                        list_failed = True
                        break
                    resolved_list.append(resolved_item)
                else:
                    resolved_list.append(item)
            
            if list_failed:
                return None
                
            resolved[key] = resolved_list
            continue
        
        # Handle string variable references
        if isinstance(value, str) and '@{SESSION_ID}' in value:
            # Check if this is a template string with embedded variables
            if re.search(r'[^@].*@\{SESSION_ID\}.*[^}]', value) or re.search(r'@\{SESSION_ID\}.*[^}].*@\{SESSION_ID\}', value):
                # Handle as template string with embedded variables
                resolved_value = resolve_template_string(value, session_state)
            else:
                # Handle as direct variable reference
                resolved_value = resolve_variable(value, session_state)
            
            if resolved_value is None:
                # For better debugging
                if '.' in value:
                    parts = value.split('@{SESSION_ID}.', 1)[1].split('.', 1)
                    step_id = parts[0]
                    field = parts[1] if len(parts) > 1 else None
                    
                    logger.warning(f"Failed to resolve '{key}': {value}")
                    logger.warning(f"Looking for: step={step_id}, field={field}")
                    
                    # Check step status
                    if step_id in session_state.get('workflow', {}):
                        status = session_state['workflow'][step_id]['status']
                        logger.warning(f"Step '{step_id}' status: {status}")
                    
                    # Show available outputs
                    outputs = session_state.get('data', {}).get('outputs', {}).get(step_id)
                    if outputs:
                        if isinstance(outputs, list):
                            logger.warning(f"Step has {len(outputs)} outputs")
                            if outputs and field and isinstance(outputs[-1], dict):
                                logger.warning(f"Latest output fields: {list(outputs[-1].keys())}")
                        else:
                            logger.warning(f"Step output (non-array): {json.dumps(outputs)[:200]}")
                
                return None
            
            resolved[key] = resolved_value
        else:
            # Use value as-is
            resolved[key] = value
    
    return resolved 