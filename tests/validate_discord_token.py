"""
Discord Token Validator

This script helps validate Discord bot token format and provides guidance.
"""

import os
import sys
import base64
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_discord_token():
    """Validate Discord token format and provide guidance"""
    logger.info("🔍 Discord Token Validation")
    logger.info("=" * 50)
    
    # Load environment
    env_file = project_root / '.env.local'
    if env_file.exists():
        load_dotenv(env_file)
        logger.info("✅ Loaded .env.local file")
    
    # Check for token
    token_vars = ['DISCORD_TOKEN', 'DISCORD_BOT_TOKEN', 'BOT_TOKEN']
    token = None
    token_var_name = None
    
    for var_name in token_vars:
        token = os.getenv(var_name)
        if token:
            token_var_name = var_name
            break
    
    if not token:
        logger.error("❌ No Discord token found in environment")
        logger.info("💡 Add your Discord token to .env.local:")
        logger.info("   DISCORD_TOKEN=your_bot_token_here")
        return False
    
    logger.info(f"✅ Found token in variable: {token_var_name}")
    logger.info(f"   Token length: {len(token)} characters")
    logger.info(f"   Token preview: {token[:20]}...{token[-10:] if len(token) > 30 else ''}")
    
    # Validate token format
    logger.info("\n🔍 Token Format Validation")
    
    # Discord tokens are typically 59-68 characters long
    if len(token) < 50:
        logger.warning("⚠️  Token seems too short (< 50 characters)")
        logger.warning("   Discord bot tokens are usually 59-68 characters")
    elif len(token) > 80:
        logger.warning("⚠️  Token seems too long (> 80 characters)")
        logger.warning("   Discord bot tokens are usually 59-68 characters")
    else:
        logger.info("✅ Token length looks reasonable")
    
    # Check if it starts with expected patterns
    if token.startswith('Bot '):
        logger.warning("⚠️  Token should NOT include 'Bot ' prefix")
        logger.warning("   Remove 'Bot ' from the beginning of your token")
        actual_token = token[4:]
        logger.info(f"   Actual token: {actual_token[:20]}...")
    else:
        logger.info("✅ Token format looks correct (no 'Bot ' prefix)")
    
    # Try to decode the first part (user ID) if it looks like base64
    try:
        # Discord tokens have 3 parts separated by dots
        parts = token.split('.')
        if len(parts) == 3:
            logger.info("✅ Token has correct structure (3 parts)")
            
            # First part is base64 encoded user ID
            try:
                decoded_id = base64.b64decode(parts[0] + '==').decode('utf-8')
                logger.info(f"   Bot ID from token: {decoded_id}")
            except:
                logger.warning("⚠️  Could not decode bot ID from token")
        else:
            logger.warning(f"⚠️  Token has {len(parts)} parts, expected 3")
            logger.warning("   Discord tokens should have format: ID.TIMESTAMP.HMAC")
    except Exception as e:
        logger.warning(f"⚠️  Error analyzing token structure: {e}")
    
    # Provide guidance
    logger.info("\n💡 Next Steps to Fix Your Bot:")
    logger.info("=" * 50)
    logger.info("1. Go to https://discord.com/developers/applications")
    logger.info("2. Select your bot application")
    logger.info("3. Go to the 'Bot' section")
    logger.info("4. Click 'Reset Token' to generate a new token")
    logger.info("5. Copy the new token immediately!")
    logger.info(f"6. Update {token_var_name} in your .env.local file")
    logger.info("7. Run the Discord permissions test again:")
    logger.info("   python tests/test_discord_permissions.py")
    
    logger.info("\n🔒 Security Reminder:")
    logger.info("   • Never share your bot token publicly")
    logger.info("   • Keep your .env.local file private")
    logger.info("   • Regenerate tokens if they're compromised")
    
    return True

def main():
    """Main validation function"""
    success = validate_discord_token()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 