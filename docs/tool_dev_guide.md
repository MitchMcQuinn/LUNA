# LUNA Tool Development Guide

## Introduction

This guide explains how to create Python tools that integrate with the LUNA workflow system. Tools are Python scripts that can be executed as part of a workflow step, with access to session state, variable resolution, and environment variables.

## Basic Tool Structure

A LUNA tool is a Python script that follows these key principles:

1. **JSON-Serializable Results**: All tool outputs must be JSON-serializable
2. **Variable Resolution**: Tools can access workflow variables using the `@{SESSION_ID}` syntax
3. **Error Handling**: Tools should provide clear error messages and handle failures gracefully

### Example Basic Tool

```python
# utils/tools/example_tool.py

def process_data(input_data):
    """
    Example tool that processes input data and returns a result.
    
    Args:
        input_data: Input data from workflow step
        
    Returns:
        dict: JSON-serializable result
    """
    try:
        # Process the input data
        result = {
            "processed": True,
            "input_length": len(input_data),
            "timestamp": time.time()
        }
        
        return result
        
    except Exception as e:
        # Return error information in a structured way
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "success": False
        }
```

## Working with Variables

### Accessing Workflow Variables

Tools can access workflow variables using the `@{SESSION_ID}` syntax. The system will automatically resolve these variables before execution.

```python
# Example of using workflow variables
def analyze_message(message_data):
    """
    Example tool that uses workflow variables.
    """
    # The system will resolve these variables before execution
    channel_name = "@{SESSION_ID}.initial.channel.name"
    author_name = "@{SESSION_ID}.initial.author.username"
    
    result = {
        "analysis": {
            "channel": channel_name,
            "author": author_name,
            "message_length": len(message_data)
        }
    }
    
    return result
```

### Variable Resolution Rules

1. **Basic Syntax**: `@{SESSION_ID}.step_id.field`
2. **Indexed Access**: `@{SESSION_ID}.step_id[2].field` (access specific output)
3. **Default Values**: `@{SESSION_ID}.step_id.field|default_value`
4. **Template Strings**: `"Hello @{SESSION_ID}.user.name!"`

## Result Structure

### Required Format

All tool results must be JSON-serializable and follow this basic structure:

```python
{
    "success": bool,          # Required: Indicates if the operation succeeded
    "data": {                # Optional: Main result data
        # Tool-specific data
    },
    "metadata": {            # Optional: Additional information
        "timestamp": float,   # Recommended: Execution timestamp
        "version": str,      # Optional: Tool version
        "context": dict      # Optional: Execution context
    },
    "error": {              # Required if success=False
        "message": str,      # Error message
        "code": str,        # Optional: Error code
        "details": dict     # Optional: Additional error details
    }
}
```

### Example Result

```python
def process_file(file_path):
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        return {
            "success": True,
            "data": {
                "content": content,
                "length": len(content)
            },
            "metadata": {
                "timestamp": time.time(),
                "file_path": file_path
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "message": f"Failed to process file: {str(e)}",
                "code": "FILE_PROCESS_ERROR",
                "details": {
                    "file_path": file_path,
                    "error_type": type(e).__name__
                }
            }
        }
```

## Environment Variables

Tools can access environment variables through the `env_vars` parameter:

```python
def process_with_env():
    """
    Example tool using environment variables.
    """
    # Access environment variables
    api_key = os.environ.get('API_KEY')
    
    if not api_key:
        return {
            "success": False,
            "error": {
                "message": "API_KEY environment variable not set"
            }
        }
    
    # Use the API key
    result = call_api(api_key)
    
    return {
        "success": True,
        "data": result
    }
```

## Best Practices

### 1. Error Handling

Always implement proper error handling:

```python
def safe_operation():
    try:
        # Operation that might fail
        result = risky_operation()
        return {
            "success": True,
            "data": result
        }
    except SpecificError as e:
        return {
            "success": False,
            "error": {
                "message": f"Specific error occurred: {str(e)}",
                "code": "SPECIFIC_ERROR"
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "message": f"Unexpected error: {str(e)}",
                "code": "UNEXPECTED_ERROR"
            }
        }
```

### 2. Input Validation

Validate inputs before processing:

```python
def validate_input(input_data):
    """
    Example of input validation.
    """
    if not isinstance(input_data, dict):
        return {
            "success": False,
            "error": {
                "message": "Input must be a dictionary",
                "code": "INVALID_INPUT"
            }
        }
    
    required_fields = ['field1', 'field2']
    missing_fields = [field for field in required_fields if field not in input_data]
    
    if missing_fields:
        return {
            "success": False,
            "error": {
                "message": f"Missing required fields: {', '.join(missing_fields)}",
                "code": "MISSING_FIELDS"
            }
        }
    
    return {
        "success": True,
        "data": input_data
    }
```

### 3. Performance Considerations

- Use efficient data structures
- Implement caching where appropriate
- Handle large data sets carefully

```python
def process_large_data(data):
    """
    Example of handling large data efficiently.
    """
    try:
        # Process in chunks if data is large
        chunk_size = 1000
        results = []
        
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            processed_chunk = process_chunk(chunk)
            results.extend(processed_chunk)
            
        return {
            "success": True,
            "data": {
                "results": results,
                "total_processed": len(results)
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "message": f"Error processing data: {str(e)}"
            }
        }
```

## Testing Your Tool

### 1. Create Test Cases

```python
# tests/tools/test_example_tool.py

def test_basic_operation():
    result = process_data({"test": "data"})
    assert result["success"] == True
    assert "input_length" in result["data"]

def test_error_handling():
    result = process_data(None)
    assert result["success"] == False
    assert "error" in result
```

### 2. Test Variable Resolution

```python
def test_variable_resolution():
    # Mock session state
    session_state = {
        "data": {
            "outputs": {
                "previous_step": [{
                    "field": "value"
                }]
            }
        }
    }
    
    # Test variable resolution
    result = tool_using_variables(session_state)
    assert result["success"] == True
```

## Integration with Workflow

### 1. Step Configuration

Example workflow step using your tool:

```json
{
    "function": "utils.tools.example_tool",
    "input": {
        "data": "@{SESSION_ID}.previous_step.data",
        "config": {
            "option": "value"
        }
    }
}
```

### 2. Conditional Paths

Tools can influence workflow paths through their results:

```json
{
    "condition": [
        {
            "operator": "AND",
            "true": "@{SESSION_ID}.tool_step.success",
            "false": "@{SESSION_ID}.tool_step.error"
        }
    ]
}
```

## Common Patterns

### 1. Data Transformation

```python
def transform_data(input_data):
    """
    Example data transformation tool.
    """
    try:
        transformed = {
            "original": input_data,
            "processed": process(input_data),
            "metadata": {
                "timestamp": time.time(),
                "version": "1.0"
            }
        }
        
        return {
            "success": True,
            "data": transformed
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "message": f"Transformation failed: {str(e)}"
            }
        }
```

### 2. API Integration

```python
def api_integration(params):
    """
    Example API integration tool.
    """
    try:
        response = call_api(params)
        
        return {
            "success": True,
            "data": {
                "response": response,
                "status": "success"
            },
            "metadata": {
                "timestamp": time.time(),
                "api_version": "1.0"
            }
        }
    except APIError as e:
        return {
            "success": False,
            "error": {
                "message": f"API error: {str(e)}",
                "code": "API_ERROR",
                "details": {
                    "status_code": e.status_code,
                    "response": e.response
                }
            }
        }
```

## Configuring Code Steps in the Graph

When creating a workflow step that executes your tool, you need to configure it properly in the Neo4j graph. Here's how to set up a code step:

### Basic Step Configuration

```json
{
    "id": "process_data_step",           // Unique identifier for the step
    "function": "utils.tools.process_data",  // Path to your tool function
    "input": {                           // Input parameters for your tool
        "data": "@{SESSION_ID}.previous_step.data",
        "config": {
            "option": "value"
        }
    }
}
```

### Complete Step Example

Here's a complete example of a step configuration in Neo4j:

```cypher
CREATE (step:STEP {
    id: 'process_data_step',
    function: 'utils.code.code',
    input: {
        data: '@{SESSION_ID}.previous_step.data',
        config: {
            option: 'value',
            timeout: 5000
        }
    }
})
```

### Step Properties Explained

1. **id** (Required)
   - Unique identifier for the step
   - Used in variable references: `@{SESSION_ID}.process_data_step.result`
   - Should be descriptive but concise
   - Example: `process_data_step`, `analyze_message_step`

2. **function** (Required)
   - Path to your tool function
   - Format: `utils.tools.module_name.function_name`
   - Must match the actual path in your codebase
   - Example: `utils.tools.text_analysis.analyze_sentiment`

3. **input** (Required)
   - Dictionary of input parameters
   - Can include variable references
   - Supports nested structures
   - Example:
   ```json
   {
       "text": "@{SESSION_ID}.initial.message.content",
       "options": {
           "language": "en",
           "threshold": 0.5
       }
   }
   ```



## Conclusion

When developing tools for the LUNA system:
1. Ensure all results are JSON-serializable
2. Implement proper error handling
3. Use the variable resolution system effectively
4. Follow the standard result structure
5. Test thoroughly with various inputs
6. Document your tool's requirements and behavior

Remember that tools are part of a larger workflow system, so they should be:
- Reliable and predictable
- Well-documented
- Easy to debug
- Efficient in resource usage
- Compatible with the variable resolution system
