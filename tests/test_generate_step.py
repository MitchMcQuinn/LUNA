"""
Test script to directly test the generate-answer step.
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set up path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)  # Add current directory to path

# Load environment
env_path = os.path.join(script_dir, '.env.local')
load_dotenv(env_path)

# Import our generating function
from utils.generate import generate

def test_generate_answer():
    """Directly test the generate-answer step with the input from the workflow."""
    
    # Input data exactly as it appears in the workflow
    input_data = {
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "system": "You are a helpful assistant specializing in explaining topics in a user-friendly way. Provide clear explanations that assume no prior knowledge. Maintain the conversation context and topic throughout your responses. Be super brief and concise. If the conversation has reached a natural conclusion or the user signals disinterest, set merits_followup to false.",
        "user": "Tell me about the weather",
        "include_history": True,
        "directly_set_reply": True,
        "schema": {
            "type": "object",
            "properties": {
                "response": {
                    "type": "string",
                    "description": "The main response to the user query"
                },
                "followup": {
                    "type": "string",
                    "description": "A question for the user that encourages them to continue to explore the subject. If merits_followup is false, this field can be empty."
                },
                "merits_followup": {
                    "type": "boolean",
                    "description": "Indicates whether the conversation should continue. Set to false if the topic has been fully explored or the user's question has been completely answered."
                }
            },
            "required": ["response", "merits_followup"]
        }
    }
    
    # Call generate function directly
    print("Calling generate function...")
    try:
        result = generate(**input_data)
        print("\nGenerate function result:")
        print(json.dumps(result, indent=2))
        
        # Check if result has a 'message' key
        if isinstance(result, dict) and "message" in result:
            print("\nMessage that would be displayed to user:")
            print(result["message"])
            return True
        else:
            print("\nWarning: Result doesn't have a 'message' key for display")
            return False
            
    except Exception as e:
        logger.error(f"Error in generate function: {e}")
        print(f"\nError: {e}")
        return False

if __name__ == "__main__":
    print("Testing generate-answer step directly...")
    success = test_generate_answer()
    if success:
        print("\nTest completed successfully!")
    else:
        print("\nTest completed with issues. Check logs for details.") 