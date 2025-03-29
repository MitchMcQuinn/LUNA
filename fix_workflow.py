"""
Script to fix the workflow parameters in Neo4j
"""

import json
import logging
import sys
from neo4j import GraphDatabase

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fix_workflow")

# Neo4j connection details - adjust as needed
NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

def get_step_input(driver, step_id):
    """Get step input configuration from Neo4j"""
    with driver.session() as session:
        result = session.run(
            """
            MATCH (s:STEP {id: $id})
            RETURN s.input as input
            """,
            id=step_id
        )
        record = result.single()
        if record:
            input_data = record["input"]
            
            # Try to parse input as JSON if it's a string
            if isinstance(input_data, str):
                try:
                    input_data = json.loads(input_data)
                except:
                    pass
                    
            return input_data
        return None

def update_step_input(driver, step_id, new_input):
    """Update step input configuration in Neo4j"""
    with driver.session() as session:
        result = session.run(
            """
            MATCH (s:STEP {id: $id})
            SET s.input = $input
            RETURN s.id as id
            """,
            id=step_id,
            input=json.dumps(new_input) if isinstance(new_input, dict) else new_input
        )
        record = result.single()
        return record is not None

def fix_generate_step(driver):
    """Fix the input parameters for the generate step"""
    # Get current input
    current_input = get_step_input(driver, "generate")
    if not current_input:
        logger.error("Generate step not found in Neo4j database")
        return False
        
    logger.info(f"Current generate step input: {current_input}")
    
    # Check if input is a dictionary
    if not isinstance(current_input, dict):
        logger.error(f"Generate step input is not a dictionary: {type(current_input)}")
        return False
    
    # Check for any parameter that might be referencing request.response
    fixed = False
    new_input = dict(current_input)  # Make a copy
    
    for key, value in current_input.items():
        if isinstance(value, str) and "request.response" in value:
            logger.info(f"Found request.response reference in parameter '{key}': {value}")
            
            # If the key is not 'user', we need to fix it
            if key != "user":
                # Store the value
                ref_value = value
                
                # Remove the old key
                new_input.pop(key)
                
                # Add with correct key
                new_input["user"] = ref_value
                
                logger.info(f"Fixed parameter mapping: '{key}' -> 'user'")
                fixed = True
                break
    
    # If no fixes were needed, check if user parameter exists at all
    if not fixed and "user" not in new_input:
        for key, value in current_input.items():
            if isinstance(value, str) and "request" in value:
                # This might be trying to reference the request step
                logger.info(f"Found potential request reference in parameter '{key}': {value}")
                
                # Add proper user parameter
                new_input["user"] = "@{SESSION_ID}.request.response"
                
                logger.info(f"Added 'user' parameter with value: @{{SESSION_ID}}.request.response")
                fixed = True
                break
    
    # Update the step input if changes were made
    if fixed:
        logger.info(f"Updating generate step input to: {new_input}")
        if update_step_input(driver, "generate", new_input):
            logger.info("Successfully updated generate step input")
            return True
        else:
            logger.error("Failed to update generate step input")
            return False
    else:
        logger.info("No changes needed for generate step input")
        return True

def fix_reply_step(driver):
    """Fix the input parameters for the reply step"""
    # Get current input
    current_input = get_step_input(driver, "reply")
    if not current_input:
        logger.error("Reply step not found in Neo4j database")
        return False
        
    logger.info(f"Current reply step input: {current_input}")
    
    # Check if input is a dictionary
    if not isinstance(current_input, dict):
        logger.error(f"Reply step input is not a dictionary: {type(current_input)}")
        return False
    
    # Check for any parameter that might be using generate.response
    fixed = False
    new_input = dict(current_input)  # Make a copy
    
    # Find any parameter referencing generate step
    for key, value in current_input.items():
        if isinstance(value, str) and "generate" in value:
            logger.info(f"Found generate reference in parameter '{key}': {value}")
            
            if "generate.response" in value and key != "message":
                # Remove the old key
                new_input.pop(key)
                
                # Add with correct key
                new_input["message"] = value
                
                logger.info(f"Fixed parameter mapping: '{key}' -> 'message'")
                fixed = True
                break
    
    # Check if we need to adjust the field being referenced
    for key, value in list(new_input.items()):
        if isinstance(value, str) and "generate.response" in value:
            # Check if generate.response exists in the output
            logger.info("Checking if we need to update reference from generate.response")
            
            # Update to also try generate.message as fallback
            if "|" not in value:
                new_value = value + "|@{SESSION_ID}.generate.message"
                new_input[key] = new_value
                logger.info(f"Updated {key} to use fallback: {new_value}")
                fixed = True
    
    # Update the step input if changes were made
    if fixed:
        logger.info(f"Updating reply step input to: {new_input}")
        if update_step_input(driver, "reply", new_input):
            logger.info("Successfully updated reply step input")
            return True
        else:
            logger.error("Failed to update reply step input")
            return False
    else:
        logger.info("No changes needed for reply step input")
        return True

def fix_request_step(driver):
    """Fix the input parameters for the request step"""
    # Get current input
    current_input = get_step_input(driver, "request")
    if not current_input:
        logger.warning("Request step not found in Neo4j database")
        return False
        
    logger.info(f"Current request step input: {current_input}")
    return True  # No changes needed for request step typically

def main():
    try:
        logger.info("Starting workflow fix script")
        
        # Connect to Neo4j
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        # Fix generate step
        logger.info("===== FIXING GENERATE STEP =====")
        if fix_generate_step(driver):
            logger.info("Generate step fixed successfully")
        else:
            logger.error("Failed to fix generate step")
        
        # Fix reply step
        logger.info("===== FIXING REPLY STEP =====")
        if fix_reply_step(driver):
            logger.info("Reply step fixed successfully")
        else:
            logger.error("Failed to fix reply step")
        
        # Check request step
        logger.info("===== CHECKING REQUEST STEP =====")
        if fix_request_step(driver):
            logger.info("Request step is OK")
        else:
            logger.warning("Request step check failed")
        
        driver.close()
        logger.info("Workflow fix script completed")
        
    except Exception as e:
        logger.error(f"Error in fix script: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 