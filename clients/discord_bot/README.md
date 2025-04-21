# LUNA Discord Bot

A Discord bot that integrates with the LUNA graph-based workflow engine.

## Features

- Listens to messages in all channels the bot has access to
- Captures comprehensive data about messages, authors, members, and channels
- Forwards all data to LUNA workflows for processing
- Maintains separate sessions for each Discord channel
- Responds back to Discord with LUNA's responses

## Setup

1. **Prerequisites**
   - Node.js 16.9.0 or higher
   - Discord Bot Token (from your env.local file)
   - LUNA API running and accessible

2. **Installation**
   ```bash
   # Navigate to the discord_bot directory
   cd clients/discord_bot
   
   # Install dependencies
   npm install
   ```

3. **Configuration**
   - Edit the `.env` file and add your Discord token:
     ```
     # Discord Bot Token
     DISCORD_BOT_TOKEN=your_discord_bot_token_here
     
     # LUNA API Endpoint
     LUNA_API_URL=http://localhost:5000/api
     
     # Workflow ID - should match your existing workflow
     LUNA_WORKFLOW_ID=discord-root
     ```

4. **Running the Bot**
   ```bash
   # Make sure you're in the discord_bot directory
   npm start
   ```

## Creating a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" tab and click "Add Bot"
4. Under the "Token" section, click "Reset Token" and copy the token
5. Enable the following Privileged Gateway Intents:
   - MESSAGE CONTENT INTENT
   - SERVER MEMBERS INTENT
6. Go to the "OAuth2" tab, then "URL Generator"
7. Select the following scopes:
   - bot
8. Select the following bot permissions:
   - Read Messages/View Channels
   - Send Messages
   - Read Message History
9. Copy the generated URL and open it in your browser to add the bot to your server

## Integration with LUNA

This bot communicates with LUNA using the RESTful API. For each channel, it:

1. Creates a new LUNA session or reuses an existing one
2. Sends messages with rich context data including:
   - Message content, ID, timestamps, and attachments
   - Author information (username, ID, etc.)
   - Member details (roles, nickname, etc.)
   - Channel information (name, type, etc.)
   - Guild (server) details
3. Processes LUNA's responses and replies in the Discord channel

## LUNA Workflow Requirements

Your LUNA workflow should:

1. Accept incoming messages in the format provided by this bot
2. Process the rich context data as needed
3. Generate responses that the bot will relay back to Discord

The bot maintains separate sessions for each channel, allowing for context-aware conversations.

## Troubleshooting

- **Bot doesn't respond**: Check that your token is correct and the bot has the necessary permissions.
- **LUNA connection issues**: Verify that the LUNA API is running and accessible at the URL specified in your .env file.
- **Message processing errors**: Check the console logs for detailed error information.

## Example Workflow

To create a basic Discord bot LUNA workflow, you would need to define a workflow in Neo4j that:

1. Accepts messages and context from Discord
2. Processes the message content
3. Generates appropriate responses
4. Returns those responses to the bot 