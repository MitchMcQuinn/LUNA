// Example workflow demonstrating using Discord API to post messages to a channel
// This workflow asks for a message to send, then posts it to a Discord channel using a bot

// Clear any existing workflow
MATCH (s:STEP) DETACH DELETE s;

// Create workflow steps
CREATE (root:STEP {
    id: 'root',
    description: 'Root node for Discord API example workflow'
});

CREATE (request_channel_id:STEP {
    id: 'request-channel-id',
    function: 'utils.request.request',
    input: '{"prompt": "Please enter the Discord channel ID where you want to send a message:"}',
    description: 'Get Discord channel ID from user'
});

CREATE (request_message:STEP {
    id: 'request-message',
    function: 'utils.request.request',
    input: '{"prompt": "What message would you like to send to the Discord channel?"}',
    description: 'Get message content from user'
});

CREATE (send_discord_message:STEP {
    id: 'send-discord-message',
    function: 'utils.api.api',
    input: '{"method": "POST", "url": "https://discord.com/api/v10/channels/@{SESSION_ID}.request-channel-id.response/messages", "headers": {"Authorization": "Bot $DISCORD_TOKEN", "Content-Type": "application/json"}, "json_data": {"content": "@{SESSION_ID}.request-message.response"}}',
    description: 'Send message to Discord channel using Discord API'
});

CREATE (process_response:STEP {
    id: 'process-response',
    function: 'utils.generate.generate',
    input: '{"model": "gpt-4o", "temperature": 0.7, "system": "You are a helpful assistant that confirms whether a Discord message was sent successfully.", "user": "I tried to send a message to Discord and received this API response:\\n\\n@{SESSION_ID}.send-discord-message.response\\n\\nPlease tell me if the message was sent successfully. If there was an error, explain what went wrong and how to fix it."}',
    description: 'Process Discord API response with LLM'
});

CREATE (reply_result:STEP {
    id: 'reply-result',
    function: 'utils.reply.reply',
    input: '{"message": "@{SESSION_ID}.process-response.response"}',
    description: 'Reply with result of sending the Discord message'
});

// Create workflow connections
MATCH (root:STEP {id: 'root'})
MATCH (request_channel_id:STEP {id: 'request-channel-id'})
CREATE (root)-[:NEXT]->(request_channel_id);

MATCH (request_channel_id:STEP {id: 'request-channel-id'})
MATCH (request_message:STEP {id: 'request-message'})
CREATE (request_channel_id)-[:NEXT]->(request_message);

MATCH (request_message:STEP {id: 'request-message'})
MATCH (send_discord_message:STEP {id: 'send-discord-message'})
CREATE (request_message)-[:NEXT]->(send_discord_message);

MATCH (send_discord_message:STEP {id: 'send-discord-message'})
MATCH (process_response:STEP {id: 'process-response'})
CREATE (send_discord_message)-[:NEXT]->(process_response);

MATCH (process_response:STEP {id: 'process-response'})
MATCH (reply_result:STEP {id: 'reply-result'})
CREATE (process_response)-[:NEXT]->(reply_result); 