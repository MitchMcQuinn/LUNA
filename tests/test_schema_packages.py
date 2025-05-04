"""
Tests for the schema packages functionality in generate.py
"""

import sys
import unittest
import json
from unittest.mock import patch, MagicMock

# Add the parent directory to the path to import modules
sys.path.append('.')

class TestSchemaPackages(unittest.TestCase):
    """Test the schema packages functionality in generate.py"""

    @patch('utils.generate.openai')
    def test_schema_name_loading(self, mock_openai):
        """Test that schema_name parameter correctly loads a schema package"""
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
        
        # Call generate with schema_name
        result = generate(
            model="gpt-4o",
            temperature=0.7,
            schema_name="reimbursement",
            user="I need a reimbursement"
        )
        
        # Check that the schema was loaded correctly
        self.assertTrue(mock_openai.chat.completions.create.called)
        
        # Get the args that were passed to the openai create call
        call_args = mock_openai.chat.completions.create.call_args[1]
        
        # Check that the schema was correctly loaded and applied
        self.assertIn("functions", call_args)
        self.assertEqual(call_args["functions"][0]["name"], "generate_response")
        
        schema = call_args["functions"][0]["parameters"]
        self.assertIn("properties", schema)
        self.assertIn("reimbursement_requests", schema["properties"])
        
        # Check the result
        self.assertTrue(result["is_complete"])
        self.assertEqual(result["response"], "Thank you for your reimbursement request.")
        self.assertEqual(len(result["reimbursement_requests"]), 1)
        self.assertEqual(result["reimbursement_requests"][0]["token"], "ETH")

if __name__ == "__main__":
    unittest.main() 