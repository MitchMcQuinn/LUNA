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
                    logger.info(f"Step {step_id} is awaiting input")
                    if step_id in state["data"]["outputs"]:
                        awaiting_input = state["data"]["outputs"][step_id]
                        logger.info(f"Step {step_id} output: {json.dumps(awaiting_input, default=str)}")
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
        
        # SIMPLIFIED APPROACH: If we're awaiting input and have any step with output,
        # directly check if there's a greeting in any of the fields we can display
        greeting_fields = ["prompt", "query", "message", "content", "text"]
        greeting_message = None
        
        if awaiting_input:
            # First check the awaiting_input structure
            for field in greeting_fields:
                if field in awaiting_input and awaiting_input[field]:
                    greeting_message = awaiting_input[field]
                    logger.info(f"Found greeting in awaiting_input.{field}: {greeting_message}")
                    break
        
        # If we found a greeting, add it to messages
        if greeting_message:
            greeting = {
                'role': 'assistant',
                'content': greeting_message
            }
            
            # Only add if it's not already in messages
            if not any(m.get('role') == 'assistant' and m.get('content') == greeting_message for m in messages):
                messages.append(greeting)
                logger.info(f"Added greeting message: {greeting_message}")
                
                # Update session state with greeting
                def update_greeting(current_state):
                    if 'messages' not in current_state['data']:
                        current_state['data']['messages'] = []
                    current_state['data']['messages'].append(greeting)
                    return current_state
                
                session_manager.update_session_state(session_id, update_greeting)
        else:
            # Fallback to hardcoded greeting if we couldn't find one
            fallback_greeting = "GM! How can I help?"
            if not any(m.get('role') == 'assistant' for m in messages):
                messages.append({
                    'role': 'assistant',
                    'content': fallback_greeting
                })
                logger.info(f"Added fallback greeting: {fallback_greeting}")
                
                # Update session state with fallback greeting
                def update_greeting(current_state):
                    if 'messages' not in current_state['data']:
                        current_state['data']['messages'] = []
                    current_state['data']['messages'].append({
                        'role': 'assistant',
                        'content': fallback_greeting
                    })
                    return current_state
                
                session_manager.update_session_state(session_id, update_greeting)
        
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
        # This is required because handle_user_input now returns "active" to signal processing should continue
        if status == "active":
            logger.info(f"Processing workflow after user input")
            processing_start = time.time()
            
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
        
        # Ensure user message is in the messages list
        user_message = {"role": "user", "content": message}
        if not any(m.get("role") == "user" and m.get("content") == message for m in state["data"]["messages"]):
            state["data"]["messages"].append(user_message)
        
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
            # Check in the standard places for a response
            if "data" in state and "outputs" in state["data"]:
                # Try to find a reply step output first
                for step_id in ["reply", "provide-answer"]:
                    if step_id in state["data"]["outputs"]:
                        output = state["data"]["outputs"][step_id]
                        if isinstance(output, dict):
                            for field in ["message", "content", "response"]:
                                if field in output and output[field]:
                                    assistant_response = {
                                        "role": "assistant",
                                        "content": output[field]
                                    }
                                    logger.info(f"Found response in {step_id}.{field}")
                                    break
                            if assistant_response:
                                break
                
                # If no reply step found, check for a generate step
                if not assistant_response:
                    for step_id in ["generate", "generate-answer"]:
                        if step_id in state["data"]["outputs"]:
                            output = state["data"]["outputs"][step_id]
                            if isinstance(output, dict) and "response" in output:
                                assistant_response = {
                                    "role": "assistant",
                                    "content": output["response"]
                                }
                                logger.info(f"Found response in {step_id}.response")
                            
        # If no response was found and no error was detected, generate a generic fallback
        if not assistant_response:
            logger.warning(f"No response found in workflow outputs")
            assistant_response = {
                "role": "assistant",
                "content": "I'm sorry, I couldn't generate a response. Please try again."
            }
        
        # Add the response to messages if it's not already there
        if not any(m.get("role") == "assistant" and m.get("content") == assistant_response["content"] 
                 for m in state["data"]["messages"]):
            state["data"]["messages"].append(assistant_response)
            
            # Update the state with the new message
            def update_messages(current_state):
                if "messages" not in current_state["data"]:
                    current_state["data"]["messages"] = []
                # Ensure message isn't duplicated
                if not any(m.get("role") == assistant_response["role"] and m.get("content") == assistant_response["content"]
                         for m in current_state["data"]["messages"]):
                    current_state["data"]["messages"].append(assistant_response)
                return current_state
            
            session_manager.update_session_state(session_id, update_messages)
        
        # Return messages and current status
        return jsonify({
            'status': status,
            'messages': state["data"]["messages"],
            'awaiting_input': status == "awaiting_input"
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
                        awaiting_input = state["data"]["outputs"][step_id]
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