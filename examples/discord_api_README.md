# Using Discord API with LUNA

This guide explains how to use Discord's API through LUNA's API utility to send messages to Discord channels.

## Prerequisites

1. **Discord Bot Token**: You need a bot token from Discord
   - Create an application in the [Discord Developer Portal](https://discord.com/developers/applications)
   - Go to the "Bot" tab and create a bot
   - Copy the token and add it to your `.env.local` file as `DISCORD_TOKEN`

2. **Bot Permissions**: Your bot needs proper permissions
   - At minimum, it needs `Send Messages` permission
   - For embeds, it also needs `Embed Links` permission
   - Invite the bot to your server with these permissions

3. **Channel ID**: You need the ID of the channel where you want to send messages
   - Enable Developer Mode in Discord settings (User Settings → Advanced → Developer Mode)
   - Right-click on a channel and select "Copy ID"

## Basic Message Example

This example sends a simple text message to a Discord channel:

```cypher
CREATE (send_message:STEP {
  id: 'send-discord-message',
  function: 'utils.api.api',
  input: '{"method": "POST", "url": "https://discord.com/api/v10/channels/YOUR_CHANNEL_ID/messages", "headers": {"Authorization": "Bot $DISCORD_TOKEN", "Content-Type": "application/json"}, "json_data": {"content": "Hello from LUNA!"}}'
})
```

## Rich Embed Example

This example sends a message with a rich embed:

```cypher
CREATE (send_embed:STEP {
  id: 'send-discord-embed',
  function: 'utils.api.api',
  input: '{"method": "POST", "url": "https://discord.com/api/v10/channels/YOUR_CHANNEL_ID/messages", "headers": {"Authorization": "Bot $DISCORD_TOKEN", "Content-Type": "application/json"}, "json_data": {"embeds": [{"title": "Announcement", "description": "This is an important announcement", "color": 3447003, "fields": [{"name": "Field 1", "value": "Value 1", "inline": true}, {"name": "Field 2", "value": "Value 2", "inline": true}], "footer": {"text": "Sent via LUNA"}}]}}'
})
```

## Discord Embed Structure

Discord embeds can include:

- **title**: The title of the embed
- **description**: The main content text
- **url**: A clickable URL for the title
- **color**: A decimal color value (convert hex to decimal)
- **fields**: Array of objects with `name`, `value`, and `inline` properties
- **author**: Object with `name`, `url`, and `icon_url`
- **footer**: Object with `text` and `icon_url`
- **timestamp**: ISO8601 timestamp
- **thumbnail**: Object with `url`
- **image**: Object with `url`

## Common Issues and Troubleshooting

1. **401 Unauthorized**: Check your bot token is correct and properly formatted with `Bot ` prefix
2. **403 Forbidden**: Make sure the bot has permissions in the channel
3. **404 Not Found**: Double-check the channel ID is correct
4. **Embed not showing**: Check the embed structure follows Discord's requirements
5. **Rate limiting**: Discord API has rate limits - handle them by checking for 429 status codes

## Complete Workflow Examples

See the example workflows:
- `discord_message_example.cypher` - Basic message sending
- `discord_embed_example.cypher` - Rich embed message sending

These examples demonstrate the full workflow from collecting user input to sending the message and handling the response. 