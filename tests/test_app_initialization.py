import unittest
import os
import logging
import json
import uuid
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Set Neo4j environment variables if not already set
if not os.environ.get("NEO4J_URI"):
    os.environ["NEO4J_URI"] = "bolt://localhost:7687"
if not os.environ.get("NEO4J_USERNAME"):
    os.environ["NEO4J_USERNAME"] = "neo4j"
if not os.environ.get("NEO4J_PASSWORD"):
    os.environ["NEO4J_PASSWORD"] = "password"  # Replace with your actual password

class TestAppInitialization(unittest.TestCase):
    """Test the app's initialization and display of greetings"""
    
    def test_app_creates_initial_greeting_message(self):
        """Test that the app displays the greeting message to the user"""
        from LUNA.core.graph_engine import GraphWorkflowEngine
        from LUNA.core.session_manager import get_session_manager
        from LUNA.core.utility_registry import get_utility_registry
        from LUNA.utils.request import request
        from LUNA.utils.generate import generate
        from LUNA.utils.reply import reply
        
        # Register utility functions
        registry = get_utility_registry()
        registry.register_utility("utils.request.request", request)
        registry.register_utility("utils.generate.generate", generate)
        registry.register_utility("utils.reply.reply", reply)
        
        # Mock Flask's render_template to inspect message handling
        with patch('flask.render_template') as mock_render:
            try:
                # Import the Flask app (which causes initialization)
                from LUNA.app import app
                
                # Get the session manager
                session_manager = get_session_manager()
                
                # Get the workflow engine
                engine = GraphWorkflowEngine(session_manager=session_manager)
                
                # Test create_session endpoint
                with app.test_client() as client:
                    # Make a request to create a session
                    response = client.post('/api/session', json={})
                    data = json.loads(response.data)
                    
                    # Verify the response contains session data
                    self.assertIn('session_id', data, "Response should include session_id")
                    self.assertIn('status', data, "Response should include status")
                    self.assertIn('awaiting_input', data, "Response should include awaiting_input field")
                    
                    # Verify the awaiting_input field is correctly set
                    self.assertIsNotNone(data['awaiting_input'], "awaiting_input should not be None")
                    self.assertIn('prompt', data['awaiting_input'], "awaiting_input should include prompt")
                    self.assertEqual(data['awaiting_input']['prompt'], "GM! How can I help?", 
                                    "Initial prompt should be the greeting")
                    
                    # Get the session state to verify internal state
                    session_id = data['session_id']
                    state = session_manager.get_session_state(session_id)
                    
                    # Check request step outputs
                    self.assertIn('data', state, "Session state should have data field")
                    self.assertIn('outputs', state['data'], "Session data should have outputs field")
                    self.assertIn('request', state['data']['outputs'], "Outputs should contain request step")
                    request_output = state['data']['outputs']['request']
                    self.assertIn('prompt', request_output, "Request output should have prompt field")
                    self.assertEqual(request_output['prompt'], "GM! How can I help?", 
                                    "Request prompt should be the greeting")
                    
                    logger.info("App initialization test passed")
                    
            except ImportError as e:
                logger.error(f"Failed to import app: {e}")
                raise
            
if __name__ == "__main__":
    unittest.main() 