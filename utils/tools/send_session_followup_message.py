from utils.api import api
import logging
import os

def main():
    """
    Send a message to Discord and return the details in a structured format
    for use by subsequent steps.
    """
    logger = logging.getLogger(__name__)
    
    # These variables will be injected by the code utility from the pre-resolved variables
    # in the step input, so we can directly access them by name
    logger.info(f"Using channel_id: {channel_id}")
    logger.info(f"Using content: {content}")
    logger.info(f"Using original_message_id: {message_id}")
    
    # Load Discord token from environment
    discord_token = os.getenv('DISCORD_TOKEN') or os.getenv('DISCORD_BOT_TOKEN') or os.getenv('BOT_TOKEN')
    if not discord_token:
        logger.error("No Discord token found in environment variables")
        return {
            "success": False,
            "error": "Discord token not configured in environment variables"
        }
    
    # Make the Discord API call with the resolved values
    discord_result = api(
        method="POST",
        url="https://discord.com/api/v10/channels/" + str(channel_id) + "/messages",
        headers={
            "Authorization": f"Bot {discord_token}",
            "Content-Type": "application/json"
        },
        json_data={
            "content": content,
            "message_reference": {
                "message_id": message_id
            }
        }
    )
    
    # Check if the API call was successful
    if discord_result["status_code"] != 200:
        logger.error(f"Discord API call failed: {discord_result}")
        return {
            "success": False,
            "error": f"Discord API call failed: {discord_result.get('error')}"
        }
    
    # Extract necessary data from the Discord response
    discord_response = discord_result["response"]
    bot_message_id = discord_response["id"]
    bot_message_content = discord_response["content"]
    timestamp = discord_response["timestamp"]
    
    logger.info(f"Successfully sent message with ID: {bot_message_id}")
    
    # Return a structured result with the fields matching exactly what lookup_followup_session_id.py expects
    return {
        "success": True,
        "error": None,
        "response": {
            "id": bot_message_id,
            "content": bot_message_content,
            "timestamp": timestamp
        }
    }

# Set the result for the workflow
result = main()

"""
Note on Variable Resolution:
Outputs from this script can be referenced in subsequent workflow steps using the following syntax:
- Most recent output: @{SESSION_ID}.step_id.success (returns True/False)
- Message ID: @{SESSION_ID}.step_id.response.id 
- Message content: @{SESSION_ID}.step_id.response.content
- Timestamp: @{SESSION_ID}.step_id.response.timestamp
- Error (if any): @{SESSION_ID}.step_id.error

For indexed access to a specific execution history entry:
- @{SESSION_ID}.step_id[index].field

Examples:
- @{SESSION_ID}.send_discord_message.success (boolean value)
- @{SESSION_ID}.send_discord_message.response.id (Discord message ID)
- @{SESSION_ID}.send_discord_message[0].response.timestamp (Timestamp from first execution)

If this step is named "send_followup" in your workflow, you would reference it as:
- @{SESSION_ID}.send_followup.response.id

Expected Configuration Format:
When configuring this script in a workflow step, provide the following input parameters:
{
  "function": "utils.code.code",
  "file_path": "send_session_followup_message.py",
  "variables": {
    "channel_id": "DISCORD_CHANNEL_ID", // Discord channel ID as string
    "content": "Your message content here", // Message content to send
    "message_id": "ORIGINAL_MESSAGE_ID" // ID of the message to reply to
  }
}

These variables can also use variable resolution syntax to reference outputs from previous steps:
{
  "function": "utils.code.code",
  "file_path": "send_session_followup_message.py",
  "variables": {
    "channel_id": "@{SESSION_ID}.get_channel.channel_id",
    "content": "@{SESSION_ID}.generate_response.text",
    "message_id": "@{SESSION_ID}.extract_message.id"
  }
}
"""
