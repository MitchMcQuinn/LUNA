"""
Debug script to identify workflow parameter mapping issues
"""

import json
import logging
import re
import sys
from neo4j import GraphDatabase

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("debug")

# Neo4j connection details - adjust as needed
NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

def get_step_details(driver, step_id):
    """Get step details from Neo4j"""
    with driver.session() as session:
        result = session.run(
            """
            MATCH (s:STEP {id: $id})
            RETURN s.function as function, s.input as input
            """,
            id=step_id
        )
        record = result.single()
        if record:
            input_data = record["input"]
            function_name = record["function"]
            
            # Try to parse input as JSON if it's a string
            if isinstance(input_data, str):
                try:
                    input_data = json.loads(input_data)
                except:
                    pass
                    
            return {
                "function": function_name,
                "input": input_data
            }
        return None

def get_workflow_details(driver):
    """Get all steps and connections in the workflow"""
    with driver.session() as session:
        # Get all steps
        steps = session.run(
            """
            MATCH (s:STEP)
            RETURN s.id as id, s.function as function, s.input as input
            """
        ).data()
        
        # Get all connections
        connections = session.run(
            """
            MATCH (s1:STEP)-[r:NEXT]->(s2:STEP)
            RETURN s1.id as source, s2.id as target, r.conditions as conditions
            """
        ).data()
        
        return {"steps": steps, "connections": connections}

def build_sample_session_state():
    """Build a sample session state with request step output"""
    return {
        "id": "test-session",
        "workflow": {
            "root": {"status": "complete"},
            "request": {"status": "complete"},
            "generate": {"status": "active"},
            "reply": {"status": "pending"}
        },
        "data": {
            "outputs": {
                "request": [
                    {
                        "prompt": "GM! How can I help?",
                        "response": "Tell me about space"
                    }
                ]
            }
        }
    }

def debug_variable_resolution(var_reference, session_state):
    """Debug variable resolution process"""
    logger.info(f"Attempting to resolve: {var_reference}")
    
    # Extract default value if present
    default_value = None
    if "|" in var_reference:
        var_parts = var_reference.split("|", 1)
        var_reference = var_parts[0].strip()
        default_value = var_parts[1].strip()
        logger.info(f"Found default value: {default_value}")
    
    # Check if this is a variable reference
    if not var_reference.startswith('@{SESSION_ID}'):
        logger.info(f"Not a variable reference: {var_reference}")
        return var_reference
    
    # Extract the path after '@{SESSION_ID}.'
    if '.' not in var_reference:
        logger.info(f"Invalid variable reference (missing path): {var_reference}")
        return default_value
    
    # Get the path part after @{SESSION_ID}.
    path = var_reference.split('@{SESSION_ID}.', 1)[1]
    logger.info(f"Extracted path: {path}")
    
    # Split path into parts (step_id and field)
    path_parts = path.split('.', 1)
    logger.info(f"Path parts: {path_parts}")
    
    # First part is the step_id
    step_id = path_parts[0]
    logger.info(f"Referenced step: {step_id}")
    
    # Check for indexed access - e.g., step_id[2]
    index = None
    if '[' in step_id and ']' in step_id:
        match = re.search(r'(.+)\[(\d+)\]', step_id)
        if match:
            step_id = match.group(1)
            index = int(match.group(2))
            logger.info(f"Found indexed access: step_id={step_id}, index={index}")
    
    # Check if step exists in state
    if step_id in session_state.get("workflow", {}):
        step_status = session_state["workflow"][step_id]["status"]
        logger.info(f"Step {step_id} status: {step_status}")
    else:
        logger.warning(f"Step {step_id} not found in workflow state")
    
    # Get the step's outputs
    if 'data' not in session_state or 'outputs' not in session_state['data']:
        logger.warning(f"Session state missing data.outputs section")
        return default_value
    
    if step_id not in session_state['data']['outputs']:
        logger.warning(f"Step {step_id} not found in outputs")
        return default_value
    
    # Get the step output
    step_outputs = session_state['data']['outputs'][step_id]
    logger.info(f"Step {step_id} outputs: {step_outputs}")
    
    # Handle array-based outputs
    if isinstance(step_outputs, list):
        if not step_outputs:
            logger.warning(f"Step {step_id} has empty outputs array")
            return default_value
        
        # Use indexed access or most recent
        if index is not None:
            if 0 <= index < len(step_outputs):
                step_output = step_outputs[index]
                logger.info(f"Using indexed output {index} for step {step_id}")
            else:
                logger.warning(f"Index {index} out of range for step {step_id}")
                return default_value
        else:
            # Use most recent output
            step_output = step_outputs[-1]
            logger.info(f"Using most recent output for step {step_id}")
    else:
        # For backward compatibility, handle non-array outputs
        step_output = step_outputs
        logger.info(f"Using non-array output for step {step_id}")
    
    # If there's a field path, extract the field value
    if len(path_parts) > 1:
        field_path = path_parts[1].split('.')
        current_value = step_output
        
        for field in field_path:
            logger.info(f"Accessing field: {field}")
            if isinstance(current_value, dict) and field in current_value:
                current_value = current_value[field]
                logger.info(f"Field value: {current_value}")
            else:
                logger.warning(f"Field {field} not found in output for step {step_id}")
                if isinstance(current_value, dict):
                    logger.info(f"Available fields: {list(current_value.keys())}")
                return default_value
        
        logger.info(f"Final resolved value: {current_value}")
        return current_value
    else:
        # No field specified, return the entire step output
        logger.info(f"Returning full step output: {step_output}")
        return step_output

def debug_generate_function(user_input):
    """Debug the generate function with manual input"""
    from utils.generate import generate
    
    logger.info(f"Testing generate function with user input: '{user_input}'")
    result = generate(user=user_input)
    logger.info(f"Generate function result: {result}")
    return result

def manual_workflow_test():
    """Simulate the workflow with manual steps"""
    # Create a sample state
    session_state = build_sample_session_state()
    
    # Test request step
    logger.info("===== TESTING REQUEST STEP =====")
    request_output = session_state["data"]["outputs"]["request"][-1]
    logger.info(f"Request step output: {request_output}")
    
    try:
        # Import generate function
        from utils.generate import generate
        
        # Get the user input
        user_input = request_output.get("response")
        logger.info(f"User input from request: {user_input}")
        
        # Call generate directly
        logger.info("Calling generate function directly")
        result = generate(user=user_input)
        logger.info(f"Generate result: {result}")
        
        # Update session state
        session_state["data"]["outputs"]["generate"] = [result]
        
        # Test reply step (normally would use the generate output)
        logger.info("===== TESTING REPLY STEP =====")
        if isinstance(result, dict) and "response" in result:
            message = result["response"]
        elif isinstance(result, dict) and "message" in result:
            message = result["message"]
        else:
            message = str(result)
            
        logger.info(f"Message for reply: {message}")
        
        # Import reply function
        from utils.reply import reply
        
        # Call reply directly
        reply_result = reply(message=message)
        logger.info(f"Reply result: {reply_result}")
        
    except Exception as e:
        logger.error(f"Error in manual workflow test: {e}", exc_info=True)

def main():
    try:
        logger.info("Starting workflow debug script")
        
        # Connect to Neo4j
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        # Check the generate step configuration
        logger.info("===== CHECKING GENERATE STEP CONFIG =====")
        generate_step = get_step_details(driver, "generate")
        if generate_step:
            logger.info(f"Generate step function: {generate_step['function']}")
            logger.info(f"Generate step input: {generate_step['input']}")
            
            # Check input parameters
            if isinstance(generate_step['input'], dict):
                for key, value in generate_step['input'].items():
                    logger.info(f"Parameter '{key}': {value}")
                    
                    # Check if this is supposed to reference the request.response
                    if isinstance(value, str) and 'request.response' in value:
                        logger.info(f"Found reference to request.response in parameter '{key}'")
                        
                        # Test variable resolution
                        sample_state = build_sample_session_state()
                        resolved = debug_variable_resolution(value, sample_state)
                        logger.info(f"Resolved value: {resolved}")
                        
                        # Check if the key is what generate function expects ("user")
                        if key != "user":
                            logger.warning(f"Parameter key '{key}' doesn't match what generate function expects ('user')")
                            logger.info("This is likely the issue - the parameter mapping is incorrect in Neo4j")
        else:
            logger.error("Generate step not found in Neo4j database")
        
        # Get the workflow details
        logger.info("===== CHECKING WORKFLOW STRUCTURE =====")
        workflow = get_workflow_details(driver)
        logger.info(f"Found {len(workflow['steps'])} steps in workflow")
        for step in workflow['steps']:
            logger.info(f"Step ID: {step['id']}, Function: {step['function']}")
            if step['id'] == 'generate':
                logger.info(f"Generate step input: {step['input']}")
        
        logger.info(f"Found {len(workflow['connections'])} connections in workflow")
        for conn in workflow['connections']:
            logger.info(f"Connection: {conn['source']} -> {conn['target']}")
        
        # Run a manual workflow test
        logger.info("===== RUNNING MANUAL WORKFLOW TEST =====")
        manual_workflow_test()
        
        driver.close()
        logger.info("Debug script completed")
        
    except Exception as e:
        logger.error(f"Error in debug script: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 