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
        session_id = session_manager.create_session(workflow_id)
        
        # Store session ID in Flask session
        session['workflow_session_id'] = session_id
        
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
                            awaiting_input = outputs[-1]  # Get the most recent output
                        else:
                            # Backward compatibility for non-array outputs
                            awaiting_input = outputs
                    break
        else:
            logger.warning(f"Workflow completed immediately with status: {status}")
            
        # Check step outputs
        if "outputs" in state["data"]:
            for step_id, output in state["data"]["outputs"].items():
                logger.info(f"Output for step {step_id}: {json.dumps(output, default=str)}")
        
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
        session_manager = get_session_manager()
        state = session_manager.get_session_state(session_id)
        logger.info(f"Session state workflow steps: {list(state['workflow'].keys())}")
        
        # Initialize messages list if it doesn't exist
        if "messages" not in state["data"]:
            state["data"]["messages"] = []
        
        # Ensure user message is in the messages list - with deduplication
        user_message = {"role": "user", "content": message}
        
        # Check if this exact user message already exists
        user_msg_exists = False
        for existing_msg in state["data"]["messages"]:
            if existing_msg.get("role") == "user" and existing_msg.get("content") == message:
                user_msg_exists = True
                break
                
        if not user_msg_exists:
            state["data"]["messages"].append(user_message)
            logger.info(f"Added user message to conversation history: {message[:50]}")
        
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
                                RETURN s.utility as utility, s.function as function
                                """,
                                id=step_id
                            )
                            record = result.single()
                            if record:
                                # Use function if available, otherwise utility for compatibility
                                function_value = record["function"]
                                if function_value is None:
                                    function_value = record["utility"]
                                if function_value:
                                    step_functions[step_id] = function_value
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
                for step_id in state["workflow"]:
                    if step_id == "reply" or "reply" in step_id.lower():
                        logger.info(f"Found reply step: {step_id}")
                        logger.info(f"  Status: {state['workflow'][step_id]['status']}")
                        logger.info(f"  Last executed: {state['workflow'][step_id].get('last_executed', 'never')}")
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
                for step_id in state["workflow"]:
                    if step_id == "generate" or "generate" in step_id.lower():
                        logger.info(f"Found generate step: {step_id}")
                        logger.info(f"  Status: {state['workflow'][step_id]['status']}")
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
                                    "content": output[field]
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
                                    "content": output["response"]
                                }
                                logger.info(f"Found response in {step_id}.response (generate function)")
        
        # If no response was found and no error was detected, generate a generic fallback
        if not assistant_response:
            logger.warning(f"No response found in workflow outputs")
            assistant_response = {
                "role": "assistant",
                "content": "I'm sorry, I couldn't generate a response. Please try again."
            }
        
        # Add the response to messages, with proper deduplication
        assistant_content = assistant_response["content"]
        
        # Check if this EXACT response already exists (avoid same response being added multiple times)
        assistant_msg_exists = False
        for idx, existing_msg in enumerate(state["data"]["messages"]):
            if existing_msg.get("role") == "assistant" and existing_msg.get("content") == assistant_content:
                assistant_msg_exists = True
                # If it's not the last message, move it to the end to maintain conversation flow
                if idx < len(state["data"]["messages"]) - 1:
                    state["data"]["messages"].append(existing_msg)
                    state["data"]["messages"].pop(idx)
                break
                
        if not assistant_msg_exists:
            # Add message with unique ID for tracking
            assistant_response["_message_id"] = str(uuid.uuid4())[:8]
            assistant_response["timestamp"] = time.time()
            state["data"]["messages"].append(assistant_response)
            logger.info(f"Added new assistant response: {assistant_content[:50]}...")
            
            # Update the state with the new message atomically
            def update_messages(current_state):
                # Find if this exact message exists
                for existing_msg in current_state["data"]["messages"]:
                    if existing_msg.get("role") == "assistant" and existing_msg.get("content") == assistant_content:
                        logger.info(f"Skipping duplicate assistant message during update")
                        return current_state
                
                # Add if not found
                current_state["data"]["messages"].append(assistant_response.copy())
                return current_state
            
            session_manager.update_session_state(session_id, update_messages)
        
        # ===== PROMPT MESSAGE HANDLING =====
        # Check if we're awaiting input and add the prompt as a message
        # This is the main source of duplicates, needs careful handling
        awaiting_input = None
        if status == "awaiting_input":
            # Find the step that's awaiting input
            for step_id, info in state["workflow"].items():
                if info["status"] == "awaiting_input":
                    if step_id in state["data"]["outputs"]:
                        outputs = state["data"]["outputs"][step_id]
                        
                        # Handle array-based outputs
                        if isinstance(outputs, list) and outputs:
                            awaiting_input = outputs[-1]  # Get most recent
                        else:
                            awaiting_input = outputs
                            
                        # Add the prompt as a message if it exists and is not already there
                        if awaiting_input and isinstance(awaiting_input, dict):
                            prompt_fields = ["prompt", "query", "message", "content", "text"]
                            for field in prompt_fields:
                                if field in awaiting_input and awaiting_input[field]:
                                    prompt_content = awaiting_input[field]
                                    
                                    # Check if this EXACT prompt content already exists in messages
                                    prompt_exists = False
                                    for existing_msg in state["data"]["messages"]:
                                        if existing_msg.get("role") == "assistant" and existing_msg.get("content") == prompt_content:
                                            logger.info(f"PROMPT_SKIP: Skipping duplicate prompt: '{prompt_content[:50]}...'")
                                            prompt_exists = True
                                            break
                                    
                                    if not prompt_exists:
                                        # Create a new prompt message with unique ID
                                        prompt_message = {
                                            "role": "assistant", 
                                            "content": prompt_content,
                                            "_prompt_id": str(uuid.uuid4())[:8],  # Add unique ID for tracking
                                            "timestamp": time.time()  # Add timestamp for ordering
                                        }
                                        
                                        # Add the prompt to messages
                                        state["data"]["messages"].append(prompt_message)
                                        logger.info(f"PROMPT_ADD: Added unique prompt message: '{prompt_content[:50]}...'")
                                        
                                        # Update state with prompt message atomically
                                        def update_with_prompt(current_state):
                                            # Check again if this exact prompt exists
                                            for existing_msg in current_state["data"]["messages"]:
                                                if existing_msg.get("role") == "assistant" and existing_msg.get("content") == prompt_content:
                                                    logger.info(f"PROMPT_SKIP_UPDATE: Prompt was added by another process")
                                                    return current_state
                                            
                                            # Add if still not found
                                            current_state["data"]["messages"].append(prompt_message.copy())
                                            logger.info(f"PROMPT_UPDATE: Added prompt in session update")
                                            return current_state
                                        
                                        session_manager.update_session_state(session_id, update_with_prompt)
                                    break
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
                            awaiting_input = outputs[-1]  # Get the most recent output
                        else:
                            # Backward compatibility for non-array outputs
                            awaiting_input = outputs
                        
                        # DO NOT add prompt to messages here - only return it in awaiting_input
                        # This prevents duplicate prompts since the POST endpoint already handles it
                        logger.info(f"GET: Found awaiting_input but not adding prompt to avoid duplicates")
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