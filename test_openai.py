"""
Test script to verify the OpenAI API key.
"""

import os
import sys
import logging
from dotenv import load_dotenv
import openai

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

def test_openai_api():
    """Test the OpenAI API key by making a simple request."""
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        logger.info(f"API key from environment: {api_key[:5]}...{api_key[-5:]}")
        
        # Create OpenAI client
        client = openai.OpenAI(api_key=api_key)
        
        # Make a simple request
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'API key works!' if you can read this."}],
            max_tokens=20
        )
        
        # Print response
        result = response.choices[0].message.content
        logger.info(f"API Response: {result}")
        print(f"\nAPI Response: {result}")
        
        return True
    except Exception as e:
        logger.error(f"Error testing OpenAI API: {e}")
        print(f"\nError: {e}")
        return False

if __name__ == "__main__":
    print("Testing OpenAI API key...")
    success = test_openai_api()
    if success:
        print("\nAPI key is valid and working!")
    else:
        print("\nAPI key test failed. Check logs for details.") 