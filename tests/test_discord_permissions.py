"""
Discord Bot Permissions and Authentication Test

This test checks if the Discord bot has proper authentication and permissions
to read and write messages in Discord channels.
"""

import os
import sys
import logging
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DiscordPermissionTester:
    def __init__(self):
        self.bot_token = None
        self.test_channel_id = "1367880511711875194"  # The reimbursements channel from logs
        self.discord_api_base = "https://discord.com/api/v10"
        
    def load_environment(self):
        """Load Discord bot token from environment"""
        logger.info("🔍 Loading Discord bot token from environment")
        
        # Load environment variables
        env_file = project_root / '.env.local'
        if env_file.exists():
            load_dotenv(env_file)
            logger.info("✅ Loaded .env.local file")
        
        # Check for various possible token variable names
        token_vars = ['DISCORD_TOKEN', 'DISCORD_BOT_TOKEN', 'BOT_TOKEN']
        
        for var_name in token_vars:
            token = os.getenv(var_name)
            if token:
                self.bot_token = token
                logger.info(f"✅ Found Discord token in {var_name}")
                logger.info(f"   Token format: {token[:20]}...{token[-10:] if len(token) > 30 else ''}")
                return True
        
        logger.error("❌ No Discord bot token found")
        logger.error(f"   Checked variables: {token_vars}")
        return False
    
    def test_bot_authentication(self):
        """Test if the bot token is valid and can authenticate"""
        logger.info("🔐 Testing Discord bot authentication")
        
        if not self.bot_token:
            logger.error("❌ No bot token available for testing")
            return False
        
        headers = {
            'Authorization': f'Bot {self.bot_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Test with /users/@me endpoint to check token validity
            response = requests.get(f"{self.discord_api_base}/users/@me", headers=headers)
            
            logger.info(f"   Authentication response status: {response.status_code}")
            
            if response.status_code == 200:
                bot_info = response.json()
                logger.info("✅ Bot authentication successful!")
                logger.info(f"   Bot username: {bot_info.get('username')}")
                logger.info(f"   Bot ID: {bot_info.get('id')}")
                logger.info(f"   Bot verified: {bot_info.get('verified', False)}")
                return True
            elif response.status_code == 401:
                logger.error("❌ Invalid bot token - authentication failed")
                logger.error(f"   Response: {response.text}")
                return False
            else:
                logger.error(f"❌ Unexpected response: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing authentication: {e}")
            return False
    
    def test_channel_access(self):
        """Test if the bot can access the specific channel"""
        logger.info(f"📋 Testing channel access for channel {self.test_channel_id}")
        
        if not self.bot_token:
            logger.error("❌ No bot token available for testing")
            return False
        
        headers = {
            'Authorization': f'Bot {self.bot_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Test getting channel info
            response = requests.get(f"{self.discord_api_base}/channels/{self.test_channel_id}", headers=headers)
            
            logger.info(f"   Channel access response status: {response.status_code}")
            
            if response.status_code == 200:
                channel_info = response.json()
                logger.info("✅ Channel access successful!")
                logger.info(f"   Channel name: {channel_info.get('name')}")
                logger.info(f"   Channel type: {channel_info.get('type')}")
                logger.info(f"   Guild ID: {channel_info.get('guild_id')}")
                return True
            elif response.status_code == 403:
                logger.error("❌ Bot lacks permission to access this channel")
                logger.error(f"   Response: {response.text}")
                return False
            elif response.status_code == 404:
                logger.error("❌ Channel not found or bot not in guild")
                logger.error(f"   Response: {response.text}")
                return False
            else:
                logger.error(f"❌ Unexpected response: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing channel access: {e}")
            return False
    
    def test_message_permissions(self):
        """Test if the bot has permission to send messages"""
        logger.info(f"💬 Testing message send permissions for channel {self.test_channel_id}")
        
        if not self.bot_token:
            logger.error("❌ No bot token available for testing")
            return False
        
        headers = {
            'Authorization': f'Bot {self.bot_token}',
            'Content-Type': 'application/json'
        }
        
        # Test with a harmless test message
        test_message = {
            'content': '🧪 Discord bot permission test - this message confirms the bot can send messages!'
        }
        
        try:
            # Attempt to send a test message
            response = requests.post(
                f"{self.discord_api_base}/channels/{self.test_channel_id}/messages",
                headers=headers,
                json=test_message
            )
            
            logger.info(f"   Message send response status: {response.status_code}")
            
            if response.status_code == 200:
                message_info = response.json()
                logger.info("✅ Message send successful!")
                logger.info(f"   Message ID: {message_info.get('id')}")
                logger.info(f"   Message sent at: {message_info.get('timestamp')}")
                return True
            elif response.status_code == 403:
                logger.error("❌ Bot lacks permission to send messages in this channel")
                error_data = response.json() if response.content else {}
                logger.error(f"   Error code: {error_data.get('code')}")
                logger.error(f"   Error message: {error_data.get('message')}")
                return False
            elif response.status_code == 401:
                logger.error("❌ Unauthorized - invalid token or bot not authenticated")
                logger.error(f"   Response: {response.text}")
                return False
            else:
                logger.error(f"❌ Unexpected response: {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing message permissions: {e}")
            return False
    
    def test_message_reference_permissions(self):
        """Test if the bot can send message references (replies)"""
        logger.info(f"🔗 Testing message reference permissions for channel {self.test_channel_id}")
        
        if not self.bot_token:
            logger.error("❌ No bot token available for testing")
            return False
        
        headers = {
            'Authorization': f'Bot {self.bot_token}',
            'Content-Type': 'application/json'
        }
        
        # First, try to get recent messages to reference
        try:
            # Get recent messages
            response = requests.get(
                f"{self.discord_api_base}/channels/{self.test_channel_id}/messages?limit=1",
                headers=headers
            )
            
            if response.status_code != 200:
                logger.warning(f"⚠️  Could not fetch recent messages: {response.status_code}")
                logger.info("   Skipping message reference test")
                return True  # Not a critical failure
            
            messages = response.json()
            if not messages:
                logger.info("   No recent messages found, skipping reply test")
                return True
            
            reference_message_id = messages[0]['id']
            logger.info(f"   Using message {reference_message_id} as reference")
            
            # Test sending a reply
            test_reply = {
                'content': '🧪 Discord bot reply test - confirming bot can send message references!',
                'message_reference': {
                    'message_id': reference_message_id
                }
            }
            
            response = requests.post(
                f"{self.discord_api_base}/channels/{self.test_channel_id}/messages",
                headers=headers,
                json=test_reply
            )
            
            logger.info(f"   Reply send response status: {response.status_code}")
            
            if response.status_code == 200:
                logger.info("✅ Message reference (reply) successful!")
                return True
            else:
                logger.warning(f"⚠️  Reply failed: {response.status_code}")
                logger.warning(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing message reference permissions: {e}")
            return False
    
    def check_bot_scopes(self):
        """Check what scopes and permissions the bot has"""
        logger.info("🔍 Checking bot scopes and permissions")
        
        if not self.bot_token:
            logger.error("❌ No bot token available for testing")
            return False
        
        headers = {
            'Authorization': f'Bot {self.bot_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Get application info
            response = requests.get(f"{self.discord_api_base}/oauth2/applications/@me", headers=headers)
            
            if response.status_code == 200:
                app_info = response.json()
                logger.info("✅ Application info retrieved!")
                logger.info(f"   App name: {app_info.get('name')}")
                logger.info(f"   App ID: {app_info.get('id')}")
                
                if 'bot' in app_info:
                    bot_info = app_info['bot']
                    logger.info(f"   Bot public: {bot_info.get('public', 'Unknown')}")
                    logger.info(f"   Bot requires OAuth2 code grant: {bot_info.get('require_code_grant', 'Unknown')}")
                
                return True
            else:
                logger.warning(f"⚠️  Could not get application info: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error checking bot scopes: {e}")
            return False

def test_discord_permissions():
    """Main test function"""
    logger.info("🚀 Starting Discord Bot Permissions Test")
    logger.info("=" * 60)
    
    tester = DiscordPermissionTester()
    results = []
    
    # Test 1: Load environment
    logger.info("\n🔧 Test 1: Environment Setup")
    env_result = tester.load_environment()
    results.append(("Environment Setup", env_result))
    
    if not env_result:
        logger.error("❌ Cannot proceed without Discord bot token")
        return False
    
    # Test 2: Authentication
    logger.info("\n🔐 Test 2: Bot Authentication")
    auth_result = tester.test_bot_authentication()
    results.append(("Bot Authentication", auth_result))
    
    # Test 3: Channel Access
    logger.info("\n📋 Test 3: Channel Access")
    channel_result = tester.test_channel_access()
    results.append(("Channel Access", channel_result))
    
    # Test 4: Message Permissions
    logger.info("\n💬 Test 4: Message Send Permissions")
    message_result = tester.test_message_permissions()
    results.append(("Message Permissions", message_result))
    
    # Test 5: Reply Permissions
    logger.info("\n🔗 Test 5: Message Reference Permissions")
    reply_result = tester.test_message_reference_permissions()
    results.append(("Reply Permissions", reply_result))
    
    # Test 6: Bot Scopes
    logger.info("\n🔍 Test 6: Bot Scopes Check")
    scope_result = tester.check_bot_scopes()
    results.append(("Bot Scopes", scope_result))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 TEST RESULTS SUMMARY")
    logger.info("=" * 60)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"   {test_name}: {status}")
        if not result:
            all_passed = False
    
    logger.info("=" * 60)
    if all_passed:
        logger.info("🎉 All Discord permission tests passed!")
    else:
        logger.info("⚠️  Some Discord permission tests failed - check configuration")
    
    return all_passed

def main():
    """Main test runner"""
    success = test_discord_permissions()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 