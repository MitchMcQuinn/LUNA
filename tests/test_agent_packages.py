"""
Tests for the agent packages functionality in generate.py
"""

import sys
import unittest
import json
from unittest.mock import patch, MagicMock

# Add the parent directory to the path to import modules
sys.path.append('.')

class TestAgentPackages(unittest.TestCase):
    """Test the agent packages functionality in generate.py"""

    def test_load_agent(self):
        """Test that agent configurations can be loaded properly"""
        from utils.agents import load_agent
        
        # Load the agent config
        agent_config = load_agent("reimbursement_processor")
        
        # Verify the agent configuration has the expected fields
        self.assertIn("model", agent_config)
        self.assertIn("temperature", agent_config)
        self.assertIn("system", agent_config)
        
        # Verify specific values
        self.assertEqual(agent_config["model"], "gpt-4o")
        self.assertEqual(agent_config["temperature"], 0.7)
        self.assertTrue("reimbursement" in agent_config["system"].lower())
        
        return agent_config

    @patch('utils.generate.openai')
    def test_agent_with_generate(self, mock_openai):
        """Test that the agent parameter works with the generate function"""
        # Setup mock response
        mock_response = MagicMock()
        mock_completion = MagicMock()
        mock_function_call = MagicMock()
        
        mock_function_call.arguments = json.dumps({
            "response": "Thank you for your reimbursement request.",
            "is_complete": True,
            "reimbursement_requests": [
                {
                    "blockchain_address": "0x123",
                    "person": "John Doe",
                    "description": "Test",
                    "amount": 100,
                    "token": "ETH",
                    "chain": "ETH"
                }
            ]
        })
        
        mock_completion.function_call = mock_function_call
        mock_response.choices = [MagicMock(message=mock_completion)]
        mock_openai.chat.completions.create.return_value = mock_response
        
        # Import the generate function
        from utils.generate import generate
        
        # Call generate with agent and schema_name
        result = generate(
            agent="reimbursement_processor",
            schema_name="reimbursement",
            include_history=True,  # Explicitly set include_history
            user="I need a reimbursement"
        )
        
        # Check that the right model was used
        call_args = mock_openai.chat.completions.create.call_args[1]
        self.assertEqual(call_args["model"], "gpt-4o")
        
        # Check that the system message was applied
        found_system_message = False
        for msg in call_args["messages"]:
            if msg["role"] == "system":
                found_system_message = True
                self.assertTrue("reimbursement" in msg["content"].lower())
        self.assertTrue(found_system_message)
        
        # Check that the result is correctly formatted
        self.assertTrue(result["is_complete"])
        self.assertEqual(result["response"], "Thank you for your reimbursement request.")
        self.assertEqual(len(result["reimbursement_requests"]), 1)
        self.assertEqual(result["reimbursement_requests"][0]["token"], "ETH")
        
    @patch('utils.generate.openai')
    def test_include_history_not_applied_from_agent(self, mock_openai):
        """Test that include_history from the agent config is not applied automatically"""
        # Setup mock response
        mock_response = MagicMock()
        mock_completion = MagicMock()
        mock_completion.content = "Test response"
        mock_response.choices = [MagicMock(message=mock_completion)]
        mock_openai.chat.completions.create.return_value = mock_response
        
        # Import the generate function
        from utils.generate import generate
        
        # Call generate with agent but without specifying include_history
        generate(
            agent="reimbursement_processor",
            user="Test include_history"
        )
        
        # Check that history was not included (default is False)
        call_args = mock_openai.chat.completions.create.call_args[1]
        self.assertEqual(len(call_args["messages"]), 2)  # system + user, no history
        
    @patch('utils.generate.openai')
    def test_agent_override(self, mock_openai):
        """Test that agent values can be overridden"""
        # Setup mock response
        mock_response = MagicMock()
        mock_completion = MagicMock()
        mock_function_call = MagicMock()
        
        mock_function_call.arguments = json.dumps({"result": "test"})
        mock_completion.function_call = mock_function_call
        mock_response.choices = [MagicMock(message=mock_completion)]
        mock_openai.chat.completions.create.return_value = mock_response
        
        # Import the generate function
        from utils.generate import generate
        
        # Call generate with agent and override temperature
        generate(
            agent="reimbursement_processor",
            temperature=0.1,  # Override the agent's temperature
            user="Test override"
        )
        
        # Check that our temperature was used, not the agent's
        call_args = mock_openai.chat.completions.create.call_args[1]
        self.assertEqual(call_args["temperature"], 0.1)

if __name__ == "__main__":
    unittest.main() 