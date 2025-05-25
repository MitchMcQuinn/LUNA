"""
Python code execution utility for workflow steps.

This utility allows executing Python code snippets as part of a workflow,
with variable resolution from session state and environment variable access.
The executed code should return JSON-serializable data for workflow integration.
"""

import json
import logging
import os
import sys
import traceback
from dotenv import load_dotenv
from core.variable_resolver import resolve_variable, resolve_template_string

logger = logging.getLogger(__name__)

# Load environment variables
env_path = os.path.join(os.getcwd(), '.env.local')
if os.path.exists(env_path):
    logger.info(f"Loading environment variables from {env_path}")
    load_dotenv(env_path)
else:
    logger.warning(f"Environment file {env_path} not found")

def sanitize_neo4j_values(values):
    """
    Sanitize values for Neo4j parameterized queries.
    This function recursively handles dictionaries, lists, and scalar values
    to ensure they are safe to use as parameters in Neo4j queries.
    
    Args:
        values: The value or dictionary of values to sanitize
        
    Returns:
        Sanitized values that can be safely used in Neo4j parameterized queries
    """
    if isinstance(values, dict):
        return {k: sanitize_neo4j_values(v) for k, v in values.items()}
    elif isinstance(values, list):
        return [sanitize_neo4j_values(v) for v in values]
    elif isinstance(values, str):
        # String values are already safely handled by the Neo4j driver's parameterized queries
        # We just need to ensure they're valid strings
        return values
    elif values is None:
        return None
    elif isinstance(values, (int, float, bool)):
        return values
    else:
        # Convert any other types to strings
        return str(values)

def code(code=None, file_path=None, session_id=None, session_state=None, env_vars=None, variables=None, **kwargs):
    """
    Execute Python code with variable resolution from session state.
    
    Args:
        code (str): Python code to execute (either this or file_path must be provided)
        file_path (str): Path to a file containing the code to execute.
                         If only a filename is provided (no directory path),
                         it will automatically look in utils/tools/ directory.
        session_id (str): Current session ID
        session_state (dict): Session state for variable resolution
        env_vars (list): List of environment variable names to make available
        variables (dict): Pre-resolved variables to inject into the code's global namespace
        **kwargs: Additional variables to expose to the code
        
    Returns:
        dict: JSON-serializable result containing:
            - result: Output from the executed code
            - error: Error message if execution failed (optional)
            - traceback: Error traceback if execution failed (optional)
            
    Examples:
        # Simple example using just a filename:
        result = code(file_path="text_analysis.py", session_id="abc123")
        
        # The above will automatically look for the file in utils/tools/text_analysis.py
        
        # Example with pre-resolved variables:
        result = code(
            file_path="send_message.py", 
            variables={
                "channel_id": "1234567890", 
                "message_content": "Hello world"
            }
        )
    """
    logger.info(f"Executing Python code for session {session_id}")
    
    # Initialize the result structure
    result = {
        "result": None,
        "error": None,
        "traceback": None
    }
    
    try:
        # Load code from file if path is provided
        if file_path and not code:
            logger.info(f"Loading code from file: {file_path}")
            try:
                # Handle different path formats
                full_path = None
                
                # Case 1: Production path with luna-api/ prefix (e.g., "luna-api/utils/tools/create_session.py")
                if file_path.startswith("luna-api/"):
                    # Remove the luna-api/ prefix and use the rest as relative path
                    relative_path = file_path[9:]  # Remove "luna-api/" prefix
                    
                    # Check if we're already in the luna-api directory (production case)
                    current_dir = os.getcwd()
                    if current_dir.endswith("luna-api"):
                        # We're already in luna-api, so just use the relative path
                        full_path = os.path.join(current_dir, relative_path)
                        logger.info(f"Production path detected (in luna-api dir), using: {full_path}")
                    else:
                        # We're not in luna-api, so add it to the path (local development case)
                        full_path = os.path.join(current_dir, "luna-api", relative_path)
                        logger.info(f"Production path detected (not in luna-api dir), using: {full_path}")
                        
                        # If that doesn't exist, try without the luna-api prefix (fallback)
                        if not os.path.exists(full_path):
                            full_path = os.path.join(current_dir, relative_path)
                            logger.info(f"Fallback: trying without luna-api prefix: {full_path}")
                
                # Case 2: Just a filename (e.g., "create_session.py")
                elif os.path.basename(file_path) == file_path:
                    # If it's just a filename, assume it's in utils/tools
                    tools_path = os.path.join(os.getcwd(), "utils", "tools", file_path)
                    if os.path.exists(tools_path):
                        full_path = tools_path
                        logger.info(f"Using tools directory for file: {full_path}")
                    else:
                        # Fall back to normal path resolution if not found in tools
                        full_path = os.path.join(os.getcwd(), file_path)
                        logger.info(f"File not found in tools, trying root: {full_path}")
                
                # Case 3: Absolute path
                elif os.path.isabs(file_path) and os.path.exists(file_path):
                    full_path = file_path
                    logger.info(f"Using absolute path: {full_path}")
                
                # Case 4: Relative path from project root
                else:
                    full_path = os.path.join(os.getcwd(), file_path)
                    logger.info(f"Using relative path from root: {full_path}")
                
                # Check if path exists
                if not os.path.exists(full_path):
                    raise FileNotFoundError(f"Code file not found: {file_path} (resolved to: {full_path})")
                
                # Read the file
                with open(full_path, 'r') as file:
                    code = file.read()
                
                # Strip outer quotes if they exist
                if code.startswith("'") and code.endswith("'"):
                    code = code[1:-1].strip()
                
                logger.info(f"Successfully loaded code from {full_path}")
            except Exception as e:
                error_msg = f"Error loading code file: {str(e)}"
                logger.error(error_msg)
                return {
                    "result": None,
                    "error": error_msg,
                    "traceback": traceback.format_exc()
                }
        elif not code:
            error_msg = "No code or file path provided"
            logger.error(error_msg)
            return {
                "result": None,
                "error": error_msg
            }
        
        # Step 1: Process the code for template variables first
        # This will handle any non-code template strings like "Hello @{SESSION_ID}.name"
        if session_state and "@{SESSION_ID}" in code:
            logger.info("Processing template variables in code")
            lines = code.split('\n')
            processed_lines = []
            
            for line in lines:
                if "@{SESSION_ID}" in line:
                    # Check if this appears to be a string rather than a variable assignment
                    if ('"' in line or "'" in line) and "@{SESSION_ID}" in line.split('=')[-1]:
                        # Don't resolve variables in string literals, we'll handle those at runtime
                        processed_lines.append(line)
                    else:
                        # This is likely a variable assignment, so resolve it directly
                        processed_line = resolve_template_string(line, session_state)
                        if processed_line is None:
                            # Failed to resolve, keep original
                            processed_lines.append(line)
                        else:
                            processed_lines.append(processed_line)
                else:
                    processed_lines.append(line)
            
            code = '\n'.join(processed_lines)
            logger.info("Completed template variable processing")
        
        # Step 2: Now resolve code variables that represent actual code values
        resolved_code = code
        if session_state and "@{SESSION_ID}" in resolved_code:
            logger.info("Resolving variables in code")
            resolved_code = resolve_code_variables(resolved_code, session_state)
        
        # Step 3: Set up execution environment with env vars
        execution_env = {}
        
        # Add requested environment variables
        if env_vars:
            for var_name in env_vars:
                if var_name in os.environ:
                    execution_env[var_name] = os.environ[var_name]
                    logger.info(f"Added environment variable: {var_name}")
                else:
                    logger.warning(f"Environment variable not found: {var_name}")
        
        # Add any pre-resolved variables from the input
        if variables:
            logger.info(f"Adding {len(variables)} pre-resolved variables to execution environment")
            for var_name, var_value in variables.items():
                # If the variable value is a template string, resolve it
                if isinstance(var_value, str) and "@{SESSION_ID}" in var_value and session_state:
                    resolved_value = resolve_variable(var_value, session_state)
                    if resolved_value is not None:
                        execution_env[var_name] = resolved_value
                        logger.info(f"Added resolved variable: {var_name}")
                    else:
                        logger.warning(f"Failed to resolve variable: {var_name} = {var_value}")
                        execution_env[var_name] = var_value
                else:
                    execution_env[var_name] = var_value
                    logger.info(f"Added variable: {var_name}")
        
        # Add any additional kwargs to the execution environment
        execution_env.update(kwargs)
        
        # Step 4: Execute the code
        logger.info("Executing Python code")
        exec_globals = {
            "__builtins__": __builtins__,
            "json": json,
            "os": os,
            "sys": sys,
            "result": None,  # Will hold the result
            "sanitize_neo4j_values": sanitize_neo4j_values,  # Make sanitize function available
            **execution_env
        }
        
        # Properly indent the user code for the try block
        # Add 4 spaces to each line of the user code
        indented_code = "\n".join("    " + line for line in resolved_code.split("\n"))
        
        # Adjust the code to capture the returned value
        exec_code = f"""
try:
    # User code
{indented_code}
except Exception as e:
    # Capture the exception
    import traceback
    __error__ = str(e)
    __traceback__ = traceback.format_exc()
    result = None
"""
        
        # Execute the code
        exec(exec_code, exec_globals)
        
        # Step 5: Process the result
        if "__error__" in exec_globals:
            # Handle execution error
            result["error"] = exec_globals["__error__"]
            result["traceback"] = exec_globals["__traceback__"]
            logger.error(f"Code execution failed: {result['error']}")
        elif "result" in exec_globals and exec_globals["result"] is not None:
            # Get the result variable
            code_result = exec_globals["result"]
            
            # Ensure result is JSON serializable
            try:
                # Test JSON serialization
                json.dumps(code_result)
                result["result"] = code_result
            except (TypeError, OverflowError) as e:
                try:
                    # Attempt to convert to string representation if not JSON serializable
                    logger.warning(f"Result not directly JSON serializable, converting to string: {str(e)}")
                    if isinstance(code_result, dict):
                        # For dictionaries, try to convert non-serializable values to strings
                        serializable_dict = {}
                        for k, v in code_result.items():
                            try:
                                # Test if this value is serializable
                                json.dumps(v)
                                serializable_dict[k] = v
                            except (TypeError, OverflowError):
                                # Convert to string if not serializable
                                serializable_dict[k] = str(v)
                        result["result"] = serializable_dict
                    else:
                        # For other types, convert to string
                        result["result"] = str(code_result)
                    
                    # Verify the conversion worked
                    json.dumps(result["result"])
                except Exception as conv_error:
                    result["error"] = f"Result could not be made JSON serializable: {str(conv_error)}"
                    logger.error(result["error"])
        else:
            # No result was explicitly set
            result["error"] = "Code execution did not produce a 'result' variable"
            logger.warning(result["error"])
        
        return result
    
    except Exception as e:
        # Handle any errors in our utility itself
        logger.exception("Error in code execution utility")
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
        return result

# Keep the execute function as an alias for backwards compatibility
execute = code

def resolve_code_variables(code, session_state):
    """
    Resolve variable references in Python code.
    
    Args:
        code (str): Python code with variable references
        session_state (dict): Current session state
        
    Returns:
        str: Code with variables resolved
    """
    import re
    # Find variable references in the code
    var_pattern = r'@\{SESSION_ID\}(?:\.[a-zA-Z0-9_-]+)(?:\[\d+\])?(?:\.[a-zA-Z0-9_-]+)*(?:\|[^@\s]+)?'
    
    # Find all variable references in the code
    matches = list(re.finditer(var_pattern, code))
    
    # Process each match, starting from the end to avoid offset issues
    for match in reversed(matches):
        var_reference = match.group(0)
        logger.info(f"Found variable reference: {var_reference}")
        
        try:
            # Resolve the variable using the core variable resolver
            resolved_value = resolve_variable(var_reference, session_state)
            
            # Convert the value to a Python literal representation
            if resolved_value is None:
                # Check if default value is provided
                if '|' in var_reference:
                    default_value = var_reference.split('|')[-1]
                    logger.info(f"Using default value: {default_value}")
                    python_value = default_value
                else:
                    logger.warning(f"Variable {var_reference} resolved to None with no default")
                    python_value = "None"
            elif isinstance(resolved_value, (str, bool, int, float, list, dict, tuple)):
                # For basic types, use repr to get a valid Python literal
                python_value = repr(resolved_value)
            else:
                # For complex objects, convert to str
                python_value = repr(str(resolved_value))
            
            # Replace the variable reference with the Python literal
            code = code[:match.start()] + python_value + code[match.end():]
            logger.info(f"Resolved to: {python_value}")
            
        except Exception as e:
            logger.error(f"Error resolving variable {var_reference}: {e}")
            
            # Check if default value is provided
            if '|' in var_reference:
                default_value = var_reference.split('|')[-1]
                logger.info(f"Using default value due to error: {default_value}")
                code = code[:match.start()] + default_value + code[match.end():]
            else:
                # Replace with None if no default
                logger.warning(f"Replacing unresolvable variable with None")
                code = code[:match.start()] + "None" + code[match.end():]
    
    return code
