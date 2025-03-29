import unittest
import logging
import json
import uuid
from LUNA.core.graph_engine import GraphWorkflowEngine
from LUNA.core.session_manager import get_session_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestConversationLoop(unittest.TestCase):
    def setUp(self):
        """Set up test environment and resources"""
        self.session_manager = get_session_manager()
        self.engine = GraphWorkflowEngine(session_manager=self.session_manager)
        self.session_id = str(uuid.uuid4())
        self.session_manager.create_session(self.session_id)
        logger.info(f"Created test session: {self.session_id}")
        
    def test_01_initial_greeting(self):
        """Test that initial greeting is processed correctly"""
        # Process workflow initially
        status = self.engine.process_workflow(self.session_id)
        logger.info(f"Initial workflow status: {status}")
        
        # Verify that workflow is in awaiting_input state
        self.assertEqual(status, "awaiting_input", 
                         "Workflow should be awaiting input after initialization")
        
        # Get current state
        state = self.session_manager.get_session_state(self.session_id)
        
        # Verify that root step is complete
        self.assertIn("root", state["workflow"], "Root step should exist in workflow")
        self.assertEqual(state["workflow"]["root"]["status"], "complete", 
                         "Root step should be marked as complete")
        
        # Verify that request step is awaiting input
        self.assertIn("request", state["workflow"], "Request step should exist in workflow")
        self.assertEqual(state["workflow"]["request"]["status"], "awaiting_input", 
                         "Request step should be awaiting input")
        
        # Verify that the request step has the correct prompt
        request_outputs = state["data"]["outputs"].get("request", {})
        self.assertIsInstance(request_outputs, dict, "Request outputs should be a dictionary")
        self.assertIn("prompt", request_outputs, "Request outputs should include prompt")
        self.assertEqual(request_outputs["prompt"], "GM! How can I help?", 
                         "Initial prompt should be set correctly")
        
        logger.info("Initial greeting test passed")
        
    def test_02_user_input_handling(self):
        """Test that user input is processed correctly"""
        # Set up initial state (process to awaiting input)
        self.engine.process_workflow(self.session_id)
        
        # Send user input
        test_message = "Hello, I need help with a problem"
        logger.info(f"Sending test message: {test_message}")
        try:
            status = self.engine.handle_user_input(self.session_id, test_message)
            logger.info(f"Status after user input: {status}")
            
            # Verify that status is active (processing continues)
            self.assertEqual(status, "active", "Workflow should be active after receiving input")
            
            # Get updated state
            state = self.session_manager.get_session_state(self.session_id)
            
            # Verify that request step is now complete
            self.assertEqual(state["workflow"]["request"]["status"], "complete", 
                             "Request step should be complete after input")
            
            # Verify that user input was stored
            self.assertIn("request", state["data"]["outputs"], "Request outputs should exist")
            self.assertEqual(state["data"]["outputs"]["request"]["response"], test_message, 
                             "User input should be stored correctly")
            
            logger.info("User input test passed")
        except Exception as e:
            self.fail(f"User input handling failed with error: {e}")
            
    def test_03_response_generation(self):
        """Test that response is generated correctly"""
        # Set up initial state and send user input
        self.engine.process_workflow(self.session_id)
        self.engine.handle_user_input(self.session_id, "Hello, I need help with a problem")
        
        # Resume workflow processing
        status = self.engine.process_workflow(self.session_id)
        logger.info(f"Status after processing: {status}")
        
        # Get updated state
        state = self.session_manager.get_session_state(self.session_id)
        
        # Verify that generate step is completed
        self.assertIn("generate", state["workflow"], "Generate step should exist in workflow")
        self.assertEqual(state["workflow"]["generate"]["status"], "complete", 
                         "Generate step should be complete")
        
        # Verify that generate outputs contain required fields
        self.assertIn("generate", state["data"]["outputs"], "Generate outputs should exist")
        generate_output = state["data"]["outputs"]["generate"]
        self.assertIn("response", generate_output, "Generate output should include response")
        self.assertIn("followup", generate_output, "Generate output should include followup")
        self.assertIn("merits_followup", generate_output, "Generate output should include merits_followup flag")
        
        logger.info("Response generation test passed")
        
    def test_04_reply_sending(self):
        """Test that reply is sent correctly"""
        # Set up initial state, send input, and process to reply step
        self.engine.process_workflow(self.session_id)
        self.engine.handle_user_input(self.session_id, "Hello, I need help with a problem")
        self.engine.process_workflow(self.session_id)
        
        # Get updated state
        state = self.session_manager.get_session_state(self.session_id)
        
        # Verify reply step is complete
        self.assertIn("reply", state["workflow"], "Reply step should exist in workflow")
        self.assertEqual(state["workflow"]["reply"]["status"], "complete", 
                         "Reply step should be complete")
        
        # Verify reply outputs
        self.assertIn("reply", state["data"]["outputs"], "Reply outputs should exist")
        self.assertIn("message", state["data"]["outputs"]["reply"], 
                      "Reply should include message")
        
        # Verify that message matches what was generated
        generate_response = state["data"]["outputs"]["generate"]["response"]
        reply_message = state["data"]["outputs"]["reply"]["message"]
        self.assertEqual(reply_message, generate_response, 
                         "Reply message should match generated response")
        
        logger.info("Reply sending test passed")
        
    def test_05_conditional_loop(self):
        """Test that workflow loops correctly based on merits_followup"""
        # Set up to test loop behavior
        self.engine.process_workflow(self.session_id)
        self.engine.handle_user_input(self.session_id, "Hello, I need help with a problem")
        status = self.engine.process_workflow(self.session_id)
        
        # Get state after first round
        state = self.session_manager.get_session_state(self.session_id)
        
        # Check if merits_followup is true or false
        merits_followup = state["data"]["outputs"]["generate"]["merits_followup"]
        logger.info(f"merits_followup value: {merits_followup}")
        
        if merits_followup:
            # Should loop back to request
            self.assertIn("request", state["workflow"], "Request step should exist in workflow")
            # The second time through, request should have a different prompt (the followup)
            second_prompt = state["data"]["outputs"]["request"].get("prompt", "")
            self.assertNotEqual(second_prompt, "GM! How can I help?", 
                                "Second prompt should be the followup, not the initial greeting")
            
            # Final status should be awaiting_input again for next user message
            self.assertEqual(status, "awaiting_input", 
                             "Workflow should be awaiting input after looping")
        else:
            # Should not loop back if merits_followup is false
            # Final status will depend on implementation, but it should not be awaiting_input
            self.assertNotEqual(status, "awaiting_input", 
                                "Workflow should not be awaiting input if merits_followup is false")
        
        logger.info(f"Conditional loop test passed - merits_followup was {merits_followup}")
        
    def test_06_variable_resolution(self):
        """Test that variables are resolved correctly between steps"""
        # Process through the first request
        self.engine.process_workflow(self.session_id)
        self.engine.handle_user_input(self.session_id, "Tell me about workflow engines")
        status = self.engine.process_workflow(self.session_id)
        
        # Get state
        state = self.session_manager.get_session_state(self.session_id)
        
        # Check variable resolution from request to generate
        user_input = state["data"]["outputs"]["request"]["response"]
        
        # Verify generate step received user input
        self.assertIn("user", state["data"]["outputs"]["generate"]["_input_vars"], 
                      "Generate step should have received user input")
        self.assertEqual(state["data"]["outputs"]["generate"]["_input_vars"]["user"], user_input, 
                         "User input should be passed correctly to generate step")
        
        # Check variable resolution from generate to reply
        generate_response = state["data"]["outputs"]["generate"]["response"]
        
        # Verify reply step received generate response
        self.assertEqual(state["data"]["outputs"]["reply"]["message"], generate_response, 
                         "Generate response should be passed correctly to reply step")
        
        logger.info("Variable resolution test passed")
        
    def tearDown(self):
        """Clean up test resources"""
        try:
            # Delete test session (if supported)
            # self.session_manager.delete_session(self.session_id)
            logger.info(f"Test complete for session: {self.session_id}")
        except:
            pass

if __name__ == "__main__":
    unittest.main() 