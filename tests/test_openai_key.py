"""
Test script to verify OpenAI API key is set and working.
"""

import os
import logging
import sys
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

def test_openai_key():
    """Test if OpenAI API key is set and working"""
    # Look in multiple locations for the .env.local file
    possible_paths = [
        os.path.join(script_dir, '.env.local'),
        os.path.join(script_dir, 'LUNA', '.env.local'),
        os.path.join(script_dir, '.env'),
        os.environ.get('LUNA_ENV_PATH', '')
    ]
    
    loaded = False
    for path in possible_paths:
        if os.path.exists(path):
            logger.info(f"Loading environment variables from {path}")
            load_dotenv(path)
            loaded = True
    
    if not loaded:
        logger.warning("No environment file found")
        
    # Check if OPENAI_API_KEY is in environment
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable is not set")
        return False
        
    # Mask the key for logging
    masked_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:]
    logger.info(f"OPENAI_API_KEY is set: {masked_key}")
    
    # Print file locations for debugging
    logger.info(f"Current directory: {os.getcwd()}")
    logger.info(f"Script directory: {script_dir}")
    
    # Try to use the key with OpenAI's API
    try:
        import openai
        openai.api_key = api_key
        
        # Make a simple chat completion request
        logger.info("Testing API key with a simple request...")
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Say hello"}
            ],
            max_tokens=10
        )
        
        # Check if we got a valid response
        if hasattr(response, 'choices') and len(response.choices) > 0:
            message = response.choices[0].message.content
            logger.info(f"Received response from OpenAI API: {message}")
            return True
        else:
            logger.error(f"Unexpected response format: {response}")
            return False
            
    except ImportError:
        logger.error("OpenAI package not installed. Install it with: pip install openai")
        return False
    except Exception as e:
        logger.error(f"Error testing OpenAI API key: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_openai_key()
    if success:
        print("\n✅ SUCCESS: OpenAI API key is set and working correctly!\n")
    else:
        print("\n❌ ERROR: OpenAI API key is not set or not working correctly.\n")
        print("Make sure your API key is set in .env.local file like this:")
        print("OPENAI_API_KEY=your-api-key-here") 