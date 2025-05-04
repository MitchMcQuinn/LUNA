"""
Test nested session handling using the code utility

This test demonstrates how to create a nested session and interact with it
using the code utility instead of making API calls to a nested server.
"""

import unittest
import logging
import time
from core.session_manager import get_session_manager
from utils.code import code
from core.graph_workflow_engine import get_graph_workflow_engine

class TestNestedSessionCode(unittest.TestCase):
    def setUp(self):
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Setting up test")
        
        # Create a unique session ID for this test
        self.session_manager = get_session_manager()
        self.session_id = self.session_manager.create_session("default")
        self.logger.info(f"Created parent session with ID: {self.session_id}")
    
    def tearDown(self):
        # Clean up by deleting the sessions
        self.logger.info("Cleaning up test sessions")
        if hasattr(self, 'nested_session_id') and self.nested_session_id:
            self.session_manager.delete_session(self.nested_session_id)
            self.logger.info(f"Deleted nested session with ID: {self.nested_session_id}")
        
        if hasattr(self, 'session_id') and self.session_id:
            self.session_manager.delete_session(self.session_id)
            self.logger.info(f"Deleted parent session with ID: {self.session_id}")
    
    def test_nested_session_workflow(self):
        """Test creating a nested session and sending messages to it"""
        self.logger.info("Running nested session workflow test")
        
        # Step 1: Create a nested session
        self.logger.info("Creating nested session")
        create_result = code(
            file_path="create_session.py",
            variables={
                "workflow_id": "default",
                "initial_data": {
                    "test_key": "test_value",
                    "source_session": self.session_id
                }
            }
        )
        
        self.assertTrue('result' in create_result, "create_session.py did not return a result")
        self.assertTrue('session_id' in create_result['result'], "create_session.py did not return a session_id")
        
        # Store the nested session ID
        self.nested_session_id = create_result['result']['session_id']
        self.logger.info(f"Created nested session with ID: {self.nested_session_id}")
        
        # Step 2: Send a message to the nested session
        self.logger.info("Sending message to nested session")
        send_result = code(
            file_path="send_session_message.py",
            variables={
                "session_id": self.nested_session_id,
                "message": "Hello from the parent workflow!"
            }
        )
        
        self.assertTrue('result' in send_result, "send_session_message.py did not return a result")
        self.assertTrue('success' in send_result['result'], "send_session_message.py did not return a success flag")
        self.assertTrue(send_result['result']['success'], f"Sending message failed: {send_result['result'].get('error')}")
        
        self.logger.info(f"Message sent successfully to session {self.nested_session_id}")
        
        # Step 3: Wait a moment for processing to complete
        time.sleep(1)
        
        # Step 4: Get messages from the nested session
        self.logger.info("Getting messages from nested session")
        get_result = code(
            file_path="get_session_messages.py",
            variables={
                "session_id": self.nested_session_id
            }
        )
        
        self.assertTrue('result' in get_result, "get_session_messages.py did not return a result")
        self.assertTrue('success' in get_result['result'], "get_session_messages.py did not return a success flag")
        self.assertTrue(get_result['result']['success'], f"Getting messages failed: {get_result['result'].get('error')}")
        
        # Verify that the messages contain our sent message
        messages = get_result['result']['messages']
        self.assertGreater(len(messages), 0, "No messages were found in the nested session")
        
        # Find our user message
        user_messages = [msg for msg in messages if msg.get('role') == 'user' and msg.get('content') == "Hello from the parent workflow!"]
        self.assertEqual(len(user_messages), 1, "Could not find our sent user message")
        
        # Check for any assistant responses
        assistant_messages = [msg for msg in messages if msg.get('role') == 'assistant']
        self.logger.info(f"Found {len(assistant_messages)} assistant messages")
        
        for i, msg in enumerate(assistant_messages):
            self.logger.info(f"Assistant message {i+1}: {msg.get('content', '')[:100]}...")
        
        self.logger.info("Nested session test completed successfully")

if __name__ == '__main__':
    unittest.main() 