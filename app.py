"""
Flask web application for the Neo4j Graph-Based Workflow Engine.
"""

import os
import sys
import json
import uuid
import logging
import time
from flask import Flask, request, jsonify, render_template, session
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get application paths
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)  # Add current directory to path

# Load environment variables - check multiple possible locations
logger.info(f"Trying to load environment variables...")
env_paths = [
    os.path.join(script_dir, '.env.local'),  # LUNA/.env.local
    os.path.join(os.path.dirname(script_dir), '.env.local'),  # Root .env.local
    os.path.join(script_dir, '.env'),  # LUNA/.env
    os.path.join(os.path.dirname(script_dir), '.env')  # Root .env
]

for env_path in env_paths:
    if os.path.exists(env_path):
        logger.info(f"Loading environment from: {env_path}")
        load_dotenv(env_path)
        break
else:
    logger.warning("No environment file found")

# Log OpenAI API key status (masked for security)
api_key = os.environ.get("OPENAI_API_KEY")
if api_key:
    masked_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:]
    logger.info(f"OPENAI_API_KEY is set: {masked_key}")
else:
    logger.warning("OPENAI_API_KEY is not set in environment")

# Configure template and static paths
template_dir = os.path.join(script_dir, 'templates')
static_dir = os.path.join(script_dir, 'static')

# Create directories if they don't exist
os.makedirs(template_dir, exist_ok=True)
os.makedirs(static_dir, exist_ok=True)

# Initialize Flask app
app = Flask(__name__, 
            template_folder=template_dir,
            static_folder=static_dir)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default-secret-key")

try:
    # Import core components
    logger.info("Importing core components...")
    from core.graph_engine import get_graph_workflow_engine
    from core.session_manager import get_session_manager
    
    # Initialize database
    logger.info("Initializing database...")
    try:
        from main import init_database
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Could not initialize database: {e}")
        
except Exception as e:
    logger.error(f"Error during initialization: {e}")
    import traceback
    logger.error(traceback.format_exc())

@app.route('/')
def index():
    """Render the main conversation UI"""
    return render_template('index.html')

@app.route('/api/session', methods=['POST'])
def create_session():
    """Create a new workflow session"""
    try:
        session_manager = get_session_manager()
        workflow_id = request.json.get('workflow_id', 'default')
        initial_data = request.json.get('initial_data', {})
        
        # Create session
        session_id = session_manager.create_session(workflow_id)
        
        # Store session ID in Flask session
        session['workflow_session_id'] = session_id
        
        # If initial data was provided, update the session state
        if initial_data:
            logger.info(f"Adding initial data to session {session_id}: {json.dumps(initial_data, default=str)}")
            
            def update_with_initial_data(current_state):
                # Initialize data structure if needed
                if "data" not in current_state:
                    current_state["data"] = {}
                if "outputs" not in current_state["data"]:
                    current_state["data"]["outputs"] = {}
                
                # Add each top-level key in initial_data as a separate step output
                # This makes them directly accessible via @{SESSION_ID}.key.subkey
                for key, value in initial_data.items():
                    current_state["data"]["outputs"][key] = value
                
                # Also add the entire initial_data object as an "initial" step output
                # This allows accessing via @{SESSION_ID}.initial.key.subkey
                current_state["data"]["outputs"]["initial"] = initial_data
                
                logger.info(f"Updated session state with initial data for keys: {list(initial_data.keys())}")
                return current_state
            
            session_manager.update_session_state(session_id, update_with_initial_data)
        
        # Start the workflow
        engine = get_graph_workflow_engine()
        logger.info(f"Starting workflow with session {session_id}")
        status = engine.process_workflow(session_id)
        logger.info(f"Workflow initial process status: {status}")
        
        # Get session state
        state = session_manager.get_session_state(session_id)
        logger.info(f"Session workflow steps: {list(state['workflow'].keys())}")
        logger.info(f"Session step statuses: {[(s, state['workflow'][s]['status']) for s in state['workflow']]}")
        
        # Check if the workflow is waiting for input
        awaiting_input = None
        if status == "awaiting_input":
            # Find the step that's awaiting input
            for step_id, info in state["workflow"].items():
                if info["status"] == "awaiting_input":
                    if step_id in state["data"]["outputs"]:
                        outputs = state["data"]["outputs"][step_id]
                        
                        # Handle array-based outputs (get most recent)
                        if isinstance(outputs, list) and outputs:
                            await_data = outputs[-1]  # Get the most recent output
                        else:
                            # Backward compatibility for non-array outputs
                            await_data = outputs
                        
                        # Add the prompt to the messages array if not already there
                        if await_data and isinstance(await_data, dict):
                            prompt_fields = ["prompt", "query", "message", "content", "text"]
                            prompt_content = None
                            
                            for field in prompt_fields:
                                if field in await_data and await_data[field]:
                                    prompt_content = await_data[field]
                                    break
                                    
                            if prompt_content:
                                # Create a prompt message
                                prompt_message = {
                                    "role": "assistant", 
                                    "content": prompt_content,
                                    "_prompt_id": str(uuid.uuid4())[:8],
                                    "timestamp": time.time()
                                }
                                
                                # Add the prompt message if not already in messages
                                def update_with_prompt(current_state):
                                    if "data" not in current_state:
                                        current_state["data"] = {}
                                    if "messages" not in current_state["data"]:
                                        current_state["data"]["messages"] = []
                                        
                                    # Check if this prompt is already in messages to avoid duplication
                                    prompt_already_added = False
                                    for msg in current_state["data"]["messages"]:
                                        if msg.get("role") == "assistant" and msg.get("content") == prompt_content:
                                            prompt_already_added = True
                                            break
                                            
                                    if not prompt_already_added:
                                        current_state["data"]["messages"].append(prompt_message)
                                        logger.info(f"Added initial prompt message: '{prompt_content[:50]}...'")
                                    else:
                                        logger.info(f"Initial prompt already in messages, not adding duplicate")
                                    
                                    return current_state
                                
                                session_manager.update_session_state(session_id, update_with_prompt)
                                
                                # Get updated state with the prompt message
                                state = session_manager.get_session_state(session_id)
                        
                        # Create awaiting_input object without prompt content (already in messages)
                        awaiting_input = {}
                        
                        # Only include non-prompt fields
                        if await_data:
                            for key, value in await_data.items():
                                # Skip prompt fields that are already in messages
                                if key not in ["prompt", "query", "message", "content", "text"]:
                                    awaiting_input[key] = value
                            
                            # Keep options data for UI
                            if "options" in await_data:
                                awaiting_input["options"] = await_data["options"]
                        break
        else:
            logger.warning(f"Workflow completed immediately with status: {status}")
            
        # Check step outputs
        if "outputs" in state["data"]:
            # First, get function names for steps that have outputs
            step_functions = {}
            with get_graph_workflow_engine().session_manager.driver.get_session() as db_session:
                for step_id in state["data"]["outputs"]:
                    result = db_session.run(
                        """
                        MATCH (s:STEP {id: $id})
                        RETURN s.function as function
                        """,
                        id=step_id
                    )
                    record = result.single()
                    if record and record["function"]:
                        step_functions[step_id] = record["function"]
            
            # Now process outputs, using function property to identify reply steps
            for step_id, output in state["data"]["outputs"].items():
                logger.info(f"Output for step {step_id}: {json.dumps(output, default=str)}")
                
                # Add messages from completed reply steps (identified by function property)
                is_reply_step = (
                    step_id in step_functions and 
                    step_functions[step_id] and 
                    "reply" in step_functions[step_id].lower()
                )
                
                if is_reply_step:
                    logger.info(f"Found reply step: {step_id} with function: {step_functions.get(step_id)}")
                    # Handle array-based outputs (get most recent)
                    if isinstance(output, list) and output:
                        output = output[-1]  # Get the most recent output
                    
                    if isinstance(output, dict):
                        message_content = None
                        for field in ["message", "content", "response"]:
                            if field in output and output[field]:
                                message_content = output[field]
                                break
                                
                        if message_content:
                            # Create message object
                            message_obj = {
                                "role": "assistant",
                                "content": message_content,
                                "_message_id": str(uuid.uuid4())[:8],
                                "timestamp": time.time()
                            }
                            
                            # Add the message if not already in messages
                            def update_with_message(current_state):
                                if "data" not in current_state:
                                    current_state["data"] = {}
                                if "messages" not in current_state["data"]:
                                    current_state["data"]["messages"] = []
                                    
                                # Check if this message is already in messages
                                message_already_added = False
                                for msg in current_state["data"]["messages"]:
                                    if msg.get("role") == "assistant" and msg.get("content") == message_content:
                                        message_already_added = True
                                        break
                                        
                                if not message_already_added:
                                    current_state["data"]["messages"].append(message_obj)
                                    logger.info(f"Added message from reply step {step_id}: '{message_content[:50]}...'")
                                else:
                                    logger.info(f"Message already in messages, not adding duplicate")
                                
                                return current_state
                            
                            session_manager.update_session_state(session_id, update_with_message)
                            
                            # Get updated state with the message
                            state = session_manager.get_session_state(session_id)
        
        # Initialize messages list if it doesn't exist
        if "messages" not in state["data"]:
            state["data"]["messages"] = []
        
        # Get the current messages
        messages = state["data"].get("messages", [])
        logger.info(f"Initial messages count: {len(messages)}")
        
        return jsonify({
            'session_id': session_id,
            'status': status,
            'messages': messages,
            'awaiting_input': awaiting_input
        })
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/<session_id>/message', methods=['POST'])
def send_message(session_id):
    """Send a message to the workflow"""
    try:
        # Log received message
        message = request.json.get('message', '')
        logger.info(f"Received message for session {session_id}: {message}")
        
        engine = get_graph_workflow_engine()
        
        # Handle user input with the response field
        logger.info(f"Handling user input for session {session_id}")
        status = engine.handle_user_input(session_id, message)
        logger.info(f"Status after handling input: {status}")
        
        # Add timestamps to ensure chronological ordering
        current_time = time.time()
        
        # Add ONLY the user message to the messages array
        user_message = {
            "role": "user", 
            "content": message,
            "_message_id": str(uuid.uuid4())[:8],
            "timestamp": current_time
        }
        
        # Add just the user message
        def update_with_user_message(current_state):
            if "data" not in current_state:
                current_state["data"] = {}
            if "messages" not in current_state["data"]:
                current_state["data"]["messages"] = []
            
            # Add user message
            current_state["data"]["messages"].append(user_message)
            return current_state
        
        # Update state with user message only
        session_manager = get_session_manager()
        session_manager.update_session_state(session_id, update_with_user_message)
        logger.info(f"Added user message to session state")
        
        # Continue processing the workflow until completion or awaiting input
        if status == "active":
            logger.info(f"Processing workflow after user input")
            processing_start = time.time()
            
            # Add debugging for path evaluation
            logger.info("===== PATH EVALUATION DEBUG =====")
            try:
                with get_graph_workflow_engine().session_manager.driver.get_session() as debug_session:
                    # Check paths from generate step
                    result = debug_session.run("""
                        MATCH (s:STEP {id: 'generate'})-[r:NEXT]->(t:STEP {id: 'reply'})
                        RETURN r.condition as condition, r.conditions as conditions, r.operator as operator
                    """)
                    record = result.single()
                    if record:
                        conditions = record.get("conditions") or record.get("condition") or "None"
                        operator = record.get("operator") or "default"
                        logger.info(f"Path from generate to reply exists with:")
                        logger.info(f"  Conditions: {conditions}")
                        logger.info(f"  Operator: {operator}")
                        
                        # Try to parse conditions
                        try:
                            if isinstance(conditions, str) and (conditions.startswith('[') or conditions.startswith('{')):
                                parsed_conditions = json.loads(conditions)
                                logger.info(f"  Parsed conditions: {json.dumps(parsed_conditions)}")
                        except Exception as e:
                            logger.error(f"  Error parsing conditions: {e}")
                    else:
                        logger.warning("No direct path from generate to reply found")
                    
                    # Check state of workflow steps
                    state = get_session_manager().get_session_state(session_id)
                    logger.info(f"Current workflow step statuses:")
                    for step_id, info in state["workflow"].items():
                        logger.info(f"  {step_id}: {info['status']}")
            except Exception as e:
                logger.error(f"Error during path evaluation debug: {e}")
            logger.info("================================")
            
            # Process with timeout protection
            max_iterations = 20
            iteration = 0
            while status == "active" and iteration < max_iterations:
                logger.info(f"Processing workflow iteration {iteration+1}")
                status = engine.process_workflow(session_id)
                logger.info(f"Status after processing: {status}")
                iteration += 1
                
                # Break if taking too long
                if time.time() - processing_start > 30:  # 30 seconds max processing time
                    logger.warning(f"Processing timeout reached for session {session_id}")
                    break
                    
            if iteration >= max_iterations:
                logger.warning(f"Reached maximum workflow processing iterations for session {session_id}")
        
        # Get updated session state
        state = session_manager.get_session_state(session_id)
        logger.info(f"Session state workflow steps: {list(state['workflow'].keys())}")
        
        # Get response based on the updated state
        assistant_response = None
        
        # Check for any generated response
        for step_id, info in state["workflow"].items():
            # First check for errors in any step
            if info.get("status") == "error":
                error_message = info.get("error", "An unknown error occurred")
                logger.warning(f"Found error in step {step_id}: {error_message}")
                assistant_response = {
                    "role": "assistant", 
                    "content": f"I'm sorry, I encountered an error processing your request. Please try again."
                }
                # Break early to prioritize error messages
                break
                
        # If no error was found, look for actual responses
        if not assistant_response:
            # Get functions for each step to determine their type
            step_functions = {}
            with get_graph_workflow_engine().session_manager.driver.get_session() as session:
                for step_id in state["workflow"]:
                    if step_id in state["data"]["outputs"]:
                        try:
                            result = session.run(
                                """
                                MATCH (s:STEP {id: $id})
                                RETURN s.function as function
                                """,
                                id=step_id
                            )
                            record = result.single()
                            if record and record["function"]:
                                step_functions[step_id] = record["function"]
                        except Exception as e:
                            logger.warning(f"Error retrieving function for step {step_id}: {e}")

            # Check in the standard places for a response
            if "data" in state and "outputs" in state["data"]:
                # Find all steps with reply functions and sort by last_executed timestamp
                reply_steps = []
                for step_id, function_name in step_functions.items():
                    if function_name and "reply" in function_name.lower() and step_id in state["data"]["outputs"]:
                        # Get the timestamp when this step was last executed
                        last_executed = state["workflow"].get(step_id, {}).get("last_executed", 0)
                        reply_steps.append((step_id, last_executed))
                
                # Sort reply steps by timestamp (most recent first)
                reply_steps.sort(key=lambda x: x[1], reverse=True)
                logger.info(f"Found {len(reply_steps)} reply steps, sorted by timestamp: {reply_steps}")
                
                # Add specific debug for reply step analysis
                logger.info("===== REPLY STEP DEBUG INFO =====")
                for step_id, function_name in step_functions.items():
                    if function_name and "reply" in function_name.lower():
                        logger.info(f"Found reply step: {step_id}")
                        logger.info(f"  Function: {function_name}")
                        logger.info(f"  Status: {state['workflow'].get(step_id, {}).get('status', 'unknown')}")
                        logger.info(f"  Last executed: {state['workflow'].get(step_id, {}).get('last_executed', 'never')}")
                        if step_id in state["data"]["outputs"]:
                            logger.info(f"  Has output: Yes")
                            try:
                                outputs = state["data"]["outputs"][step_id]
                                if isinstance(outputs, list):
                                    logger.info(f"  Outputs count: {len(outputs)}")
                                    if outputs:
                                        logger.info(f"  Latest output: {json.dumps(outputs[-1], default=str)[:200]}")
                                else:
                                    logger.info(f"  Output: {json.dumps(outputs, default=str)[:200]}")
                            except Exception as e:
                                logger.error(f"  Error getting reply outputs: {e}")
                        else:
                            logger.info(f"  Has output: No")
                
                # Also check generate step for merits_followup value
                for step_id, function_name in step_functions.items():
                    if function_name and "generate" in function_name.lower():
                        logger.info(f"Found generate step: {step_id}")
                        logger.info(f"  Function: {function_name}")
                        logger.info(f"  Status: {state['workflow'].get(step_id, {}).get('status', 'unknown')}")
                        if step_id in state["data"]["outputs"]:
                            try:
                                outputs = state["data"]["outputs"][step_id]
                                if isinstance(outputs, list) and outputs:
                                    latest = outputs[-1]
                                    logger.info(f"  merits_followup: {latest.get('merits_followup', 'NOT FOUND')}")
                            except Exception as e:
                                logger.error(f"  Error checking merits_followup: {e}")
                logger.info("==================================")
                
                # Process reply functions in order of recency
                for step_id, timestamp in reply_steps:
                    outputs = state["data"]["outputs"][step_id]
                    
                    # Handle array-based outputs (get most recent)
                    if isinstance(outputs, list) and outputs:
                        output = outputs[-1]  # Get the most recent output
                    else:
                        # Backward compatibility for non-array outputs
                        output = outputs
                        
                    if isinstance(output, dict):
                        for field in ["message", "content", "response"]:
                            if field in output and output[field]:
                                assistant_response = {
                                    "role": "assistant",
                                    "content": output[field],
                                    "_message_id": str(uuid.uuid4())[:8],
                                    "timestamp": current_time + 1
                                }
                                logger.info(f"Found response in {step_id}.{field} (reply function, executed at {timestamp})")
                                break
                        if assistant_response:
                            break
                
                # If no reply function found, check for generate functions
                if not assistant_response:
                    for step_id, function_name in step_functions.items():
                        if function_name and "generate" in function_name.lower() and step_id in state["data"]["outputs"]:
                            outputs = state["data"]["outputs"][step_id]
                            
                            # Handle array-based outputs (get most recent)
                            if isinstance(outputs, list) and outputs:
                                output = outputs[-1]  # Get the most recent output
                            else:
                                # Backward compatibility for non-array outputs
                                output = outputs
                                
                            if isinstance(output, dict) and "response" in output:
                                assistant_response = {
                                    "role": "assistant",
                                    "content": output["response"],
                                    "_message_id": str(uuid.uuid4())[:8],
                                    "timestamp": current_time + 1
                                }
                                logger.info(f"Found response in {step_id}.response (generate function)")
        
        # If no response was found and no error was detected, generate a generic fallback
        if not assistant_response:
            logger.warning(f"No response found in workflow outputs")
            assistant_response = {
                "role": "assistant",
                "content": "I'm sorry, I couldn't generate a response. Please try again.",
                "_message_id": str(uuid.uuid4())[:8],
                "timestamp": current_time + 1
            }
        
        # Add the assistant response to messages
        def update_with_assistant_response(current_state):
            if "data" not in current_state:
                current_state["data"] = {}
            if "messages" not in current_state["data"]:
                current_state["data"]["messages"] = []
            
            current_state["data"]["messages"].append(assistant_response)
            return current_state
        
        session_manager.update_session_state(session_id, update_with_assistant_response)
        logger.info(f"Added assistant response to messages array")
        
        # Get updated state with the messages
        state = session_manager.get_session_state(session_id)
        
        # Check if we're awaiting input and prepare prompt information
        awaiting_input = None
        if status == "awaiting_input":
            # Find the step that's awaiting input
            for step_id, info in state["workflow"].items():
                if info["status"] == "awaiting_input":
                    if step_id in state["data"]["outputs"]:
                        outputs = state["data"]["outputs"][step_id]
                        
                        # Handle array-based outputs
                        if isinstance(outputs, list) and outputs:
                            await_data = outputs[-1]  # Get most recent
                        else:
                            await_data = outputs
                            
                        # Add the prompt as a message if it exists and hasn't been added yet
                        if await_data and isinstance(await_data, dict):
                            prompt_fields = ["prompt", "query", "message", "content", "text"]
                            prompt_content = None
                            
                            for field in prompt_fields:
                                if field in await_data and await_data[field]:
                                    prompt_content = await_data[field]
                                    break
                                    
                            if prompt_content:
                                # Create a prompt message with later timestamp
                                prompt_message = {
                                    "role": "assistant", 
                                    "content": prompt_content,
                                    "_prompt_id": str(uuid.uuid4())[:8],
                                    "timestamp": current_time + 2  # Ensure prompt comes last
                                }
                                
                                # Add the prompt message
                                def update_with_prompt(current_state):
                                    if "data" not in current_state:
                                        current_state["data"] = {}
                                    if "messages" not in current_state["data"]:
                                        current_state["data"]["messages"] = []
                                        
                                    # Check if this exact prompt is already in messages to avoid duplication
                                    prompt_already_added = False
                                    for msg in current_state["data"]["messages"]:
                                        if msg.get("role") == "assistant" and msg.get("content") == prompt_content:
                                            prompt_already_added = True
                                            break
                                            
                                    if not prompt_already_added:
                                        current_state["data"]["messages"].append(prompt_message)
                                        logger.info(f"Added prompt message: '{prompt_content[:50]}...'")
                                    else:
                                        logger.info(f"Prompt already exists in messages, not adding duplicate")
                                    
                                    return current_state
                                
                                session_manager.update_session_state(session_id, update_with_prompt)
                                
                                # Get updated state with the prompt message
                                state = session_manager.get_session_state(session_id)
                        
                        # Create awaiting_input object without prompt content (already in messages)
                        awaiting_input = {}
                        
                        # Only include non-prompt fields
                        if await_data:
                            for key, value in await_data.items():
                                # Skip prompt fields that are already in messages
                                if key not in ["prompt", "query", "message", "content", "text"]:
                                    awaiting_input[key] = value
                            
                            # Keep options data for UI
                            if "options" in await_data:
                                awaiting_input["options"] = await_data["options"]
                        break
        
        # Return messages and current status
        return jsonify({
            'status': status,
            'messages': state["data"]["messages"],
            'awaiting_input': awaiting_input
        })
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get session state"""
    try:
        session_manager = get_session_manager()
        state = session_manager.get_session_state(session_id)
        
        if not state:
            return jsonify({'error': 'Session not found'}), 404
       
        # Get messages from session
        messages = state.get("data", {}).get("messages", [])
        
        # Check current status
        engine = get_graph_workflow_engine()
        status = engine.process_workflow(session_id)
        
        # Get functions for steps that have outputs
        step_functions = {}
        with get_graph_workflow_engine().session_manager.driver.get_session() as db_session:
            # Get all step functions
            for step_id in state.get("workflow", {}):
                result = db_session.run(
                    """
                    MATCH (s:STEP {id: $id})
                    RETURN s.function as function
                    """,
                    id=step_id
                )
                record = result.single()
                if record and record["function"]:
                    step_functions[step_id] = record["function"]
        
        # Check if the workflow is waiting for input
        awaiting_input = None
        
        if status == "awaiting_input":
            # Find the step that's awaiting input
            for step_id, info in state["workflow"].items():
                if info["status"] == "awaiting_input":
                    if step_id in state["data"]["outputs"]:
                        outputs = state["data"]["outputs"][step_id]
                        
                        # Handle array-based outputs (get most recent)
                        if isinstance(outputs, list) and outputs:
                            await_data = outputs[-1]  # Get the most recent output
                        else:
                            # Backward compatibility for non-array outputs
                            await_data = outputs
                        
                        # Add the prompt to messages if not already there
                        if await_data and isinstance(await_data, dict):
                            prompt_fields = ["prompt", "query", "message", "content", "text"]
                            prompt_content = None
                            
                            for field in prompt_fields:
                                if field in await_data and await_data[field]:
                                    prompt_content = await_data[field]
                                    break
                                    
                            if prompt_content:
                                # Check if the prompt is already in messages
                                prompt_already_added = False
                                for msg in state["data"]["messages"]:
                                    if msg.get("role") == "assistant" and msg.get("content") == prompt_content:
                                        prompt_already_added = True
                                        break
                                        
                                if not prompt_already_added:
                                    # Create a prompt message
                                    prompt_message = {
                                        "role": "assistant", 
                                        "content": prompt_content,
                                        "_prompt_id": str(uuid.uuid4())[:8],
                                        "timestamp": time.time()
                                    }
                                    
                                    # Add the message
                                    def update_with_prompt(current_state):
                                        if "data" not in current_state:
                                            current_state["data"] = {}
                                        if "messages" not in current_state["data"]:
                                            current_state["data"]["messages"] = []
                                        
                                        current_state["data"]["messages"].append(prompt_message)
                                        return current_state
                                    
                                    session_manager.update_session_state(session_id, update_with_prompt)
                                    
                                    # Get updated state with the prompt message
                                    state = session_manager.get_session_state(session_id)
                                    messages = state.get("data", {}).get("messages", [])
                                    logger.info(f"Added prompt message: '{prompt_content[:50]}...'")
                                else:
                                    logger.info(f"Prompt already exists in messages, not adding duplicate")
                        
                        # Create awaiting_input object without prompt content (already in messages)
                        awaiting_input = {}
                        
                        # Only include non-prompt fields
                        if await_data:
                            for key, value in await_data.items():
                                # Skip prompt fields that are already in messages
                                if key not in ["prompt", "query", "message", "content", "text"]:
                                    awaiting_input[key] = value
                            
                            # Keep options data for UI
                            if "options" in await_data:
                                awaiting_input["options"] = await_data["options"]
                        
                        logger.info(f"GET: Found awaiting_input, sending options but not prompt")
                        break
                 
        return jsonify({
            'session_id': session_id,
            'status': status,
            'messages': messages,
            'awaiting_input': awaiting_input
        })
        
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'ok',
        'version': '0.1.0'
    })

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=debug, host='0.0.0.0', port=port) 