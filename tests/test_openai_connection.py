"""
OpenAI API Connection Test

This test checks the connectivity to the OpenAI API using the API key
from the .env.local file. It performs various connection checks to help
diagnose any API connectivity issues.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OpenAIConnectionTester:
    def __init__(self):
        self.api_key = None
        self.client = None
        
    def load_environment(self):
        """Load environment variables from .env.local file"""
        env_file = project_root / '.env.local'
        
        if not env_file.exists():
            logger.error(f"❌ Environment file not found: {env_file}")
            logger.info("💡 Please create a .env.local file with your OpenAI API key")
            logger.info("   You can copy sample.env.local as a template")
            return False
            
        # Load environment variables
        load_dotenv(env_file)
        
        self.api_key = os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            logger.error("❌ OPENAI_API_KEY not found in environment variables")
            logger.info("💡 Please add OPENAI_API_KEY to your .env.local file")
            return False
            
        # Mask the API key for display
        masked_key = f"{self.api_key[:7]}...{self.api_key[-4:]}" if len(self.api_key) > 11 else "***"
        
        logger.info("✅ Environment variables loaded successfully")
        logger.info(f"   API Key: {masked_key}")
        logger.info(f"   Key Length: {len(self.api_key)} characters")
        
        return True
        
    def test_api_key_format(self):
        """Test if the API key format looks correct"""
        try:
            logger.info("🔍 Validating API key format...")
            
            if not self.api_key.startswith('sk-'):
                logger.error("❌ API key should start with 'sk-'")
                logger.info("💡 Make sure you're using a valid OpenAI API key")
                return False
                
            if len(self.api_key) < 40:
                logger.warning("⚠️  API key seems shorter than expected")
                logger.info("💡 OpenAI API keys are typically 51+ characters")
                
            logger.info("✅ API key format looks correct")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error validating API key: {e}")
            return False
            
    def test_client_creation(self):
        """Test creating an OpenAI client instance"""
        try:
            logger.info("🔧 Creating OpenAI client...")
            import openai
            
            # Set the API key
            openai.api_key = self.api_key
            
            # For newer versions of openai package, use the client approach
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                logger.info("✅ OpenAI client created successfully (v1.0+ style)")
            except ImportError:
                # Fallback for older versions
                self.client = openai
                logger.info("✅ OpenAI client configured successfully (legacy style)")
                
            return True
            
        except ImportError as e:
            logger.error(f"❌ Failed to import openai package: {e}")
            logger.info("💡 Install with: pip install openai")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error creating OpenAI client: {e}")
            return False
            
    def test_api_connection(self):
        """Test actual connection to the OpenAI API"""
        if not self.client:
            logger.error("❌ No OpenAI client available for connection test")
            return False
            
        try:
            logger.info("🔌 Testing OpenAI API connection...")
            
            # Test with a simple completion request
            if hasattr(self.client, 'chat') and hasattr(self.client.chat, 'completions'):
                # New client style (v1.0+)
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "user", "content": "Say 'Hello from LUNA!' if you can read this."}
                    ],
                    max_tokens=20,
                    temperature=0
                )
                
                if response and response.choices:
                    message = response.choices[0].message.content.strip()
                    logger.info(f"✅ API connection successful!")
                    logger.info(f"   Response: {message}")
                    logger.info(f"   Model used: {response.model}")
                    logger.info(f"   Tokens used: {response.usage.total_tokens}")
                    return True
                    
            else:
                # Legacy client style
                response = self.client.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "user", "content": "Say 'Hello from LUNA!' if you can read this."}
                    ],
                    max_tokens=20,
                    temperature=0
                )
                
                if response and response.choices:
                    message = response.choices[0].message.content.strip()
                    logger.info(f"✅ API connection successful!")
                    logger.info(f"   Response: {message}")
                    logger.info(f"   Model used: {response.model}")
                    logger.info(f"   Tokens used: {response.usage.total_tokens}")
                    return True
                    
            logger.error("❌ Unexpected API response format")
            return False
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if "authentication" in error_msg or "invalid api key" in error_msg:
                logger.error(f"❌ Authentication failed: {e}")
                logger.info("💡 Possible issues:")
                logger.info("   - API key is invalid or expired")
                logger.info("   - API key doesn't have required permissions")
                
            elif "quota" in error_msg or "billing" in error_msg:
                logger.error(f"❌ Quota/billing issue: {e}")
                logger.info("💡 Possible issues:")
                logger.info("   - API quota exceeded")
                logger.info("   - Billing issue with your OpenAI account")
                
            elif "rate limit" in error_msg:
                logger.error(f"❌ Rate limit exceeded: {e}")
                logger.info("💡 Try again in a moment")
                
            else:
                logger.error(f"❌ API request failed: {e}")
                
            return False
            
    def test_model_availability(self):
        """Test available models"""
        if not self.client:
            return False
            
        try:
            logger.info("📊 Checking available models...")
            
            if hasattr(self.client, 'models'):
                # New client style
                models = self.client.models.list()
                model_names = [model.id for model in models.data if 'gpt' in model.id]
            else:
                # Legacy client style
                models = self.client.Model.list()
                model_names = [model.id for model in models.data if 'gpt' in model.id]
                
            if model_names:
                logger.info(f"   Available GPT models: {len(model_names)}")
                for model in sorted(model_names)[:5]:  # Show first 5
                    logger.info(f"     • {model}")
                if len(model_names) > 5:
                    logger.info(f"     ... and {len(model_names) - 5} more")
            else:
                logger.warning("⚠️  No GPT models found")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to list models: {e}")
            return False
            
    def run_full_test(self):
        """Run the complete test suite"""
        logger.info("🚀 Starting OpenAI Connection Test")
        logger.info("=" * 50)
        
        success = True
        
        # Test 1: Load environment
        if not self.load_environment():
            return False
            
        # Test 2: Validate API key format
        if not self.test_api_key_format():
            success = False
            
        # Test 3: Create client
        if success and not self.test_client_creation():
            success = False
            
        # Test 4: Test API connection
        if success and not self.test_api_connection():
            success = False
            
        # Test 5: Check available models
        if success:
            self.test_model_availability()
            
        logger.info("=" * 50)
        if success:
            logger.info("🎉 All tests passed! OpenAI connection is working correctly.")
        else:
            logger.info("❌ Some tests failed. Please check the error messages above.")
            
        return success

def main():
    """Main test function"""
    tester = OpenAIConnectionTester()
    success = tester.run_full_test()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 