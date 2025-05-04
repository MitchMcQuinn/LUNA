"""
Test for the reimbursement schema functionality
"""

import unittest
import sys
import json

# Add the parent directory to the path
sys.path.append('.')

class TestReimbursementSchema(unittest.TestCase):
    """Test the reimbursement schema package"""
    
    def test_load_schema(self):
        """Test that the reimbursement schema can be loaded properly"""
        from utils.schemas import load_schema
        
        # Load the schema
        schema = load_schema("reimbursement")
        
        # Verify key parts of the schema
        self.assertIn("properties", schema)
        self.assertIn("reimbursement_requests", schema["properties"])
        self.assertIn("items", schema["properties"]["reimbursement_requests"])
        
        # Check that the token enum has the correct values
        token_props = schema["properties"]["reimbursement_requests"]["items"]["properties"]["token"]
        self.assertEqual(set(token_props["enum"]), {"ETH", "DAI", "USDT", "USDC"})
        self.assertNotIn("None", token_props["enum"])
        
        # Check that the chain enum has the correct values
        chain_props = schema["properties"]["reimbursement_requests"]["items"]["properties"]["chain"]
        self.assertEqual(set(chain_props["enum"]), {"ETH", "BASE", "ARB"})
        self.assertNotIn("None", chain_props["enum"])
        
        # Verify additionalProperties is a Python boolean, not a JSON string
        add_props = schema["properties"]["reimbursement_requests"]["items"]["additionalProperties"]
        self.assertIsInstance(add_props, bool)
        self.assertEqual(add_props, False)
        
        # Print the schema for inspection
        print(json.dumps(schema, indent=2))
        
        return schema
        
    def test_schema_with_generate(self):
        """Test that the schema works with the generate function"""
        from utils.generate import generate
        import openai
        import unittest.mock as mock
        
        # Test the generate function with the schema_name parameter
        with mock.patch('utils.generate.openai') as mock_openai:
            # Setup mock response
            mock_response = mock.MagicMock()
            mock_completion = mock.MagicMock()
            mock_completion.content = "Thank you for your reimbursement request."
            mock_response.choices = [mock.MagicMock(message=mock_completion)]
            mock_openai.chat.completions.create.return_value = mock_response
            
            # Call generate with schema_name
            generate(
                model="gpt-4o-mini",
                temperature=0.7,
                schema_name="reimbursement",
                user="I need to be reimbursed 1.5 ETH"
            )
            
            # Verify that openai.chat.completions.create was called
            mock_openai.chat.completions.create.assert_called_once()
            
            # Get the arguments that were passed
            call_args = mock_openai.chat.completions.create.call_args[1]
            
            # Verify schema was included in the request
            self.assertIn("functions", call_args)
            
            # Extract the schema that was sent to the API
            api_schema = call_args["functions"][0]["parameters"]
            
            # Make sure token enum does NOT include "None"
            token_enum = api_schema["properties"]["reimbursement_requests"]["items"]["properties"]["token"]["enum"]
            self.assertNotIn("None", token_enum)
            self.assertEqual(set(token_enum), {"ETH", "DAI", "USDT", "USDC"})
            
            # Make sure chain enum does NOT include "None"
            chain_enum = api_schema["properties"]["reimbursement_requests"]["items"]["properties"]["chain"]["enum"]
            self.assertNotIn("None", chain_enum)
            self.assertEqual(set(chain_enum), {"ETH", "BASE", "ARB"})
            
            # Print what was sent to the API
            print("Schema sent to API:")
            print(json.dumps(api_schema, indent=2))
        
if __name__ == "__main__":
    unittest.main() 