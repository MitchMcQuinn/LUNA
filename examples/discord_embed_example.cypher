// Example workflow demonstrating Discord API to post messages with rich embeds
// This workflow creates a nicely formatted message with title, description, and fields

// Clear any existing workflow
MATCH (s:STEP) DETACH DELETE s;

// Create workflow steps
CREATE (root:STEP {
    id: 'root',
    description: 'Root node for Discord embed example workflow'
});

CREATE (request_channel_id:STEP {
    id: 'request-channel-id',
    function: 'utils.request.request',
    input: '{"prompt": "Please enter the Discord channel ID where you want to send a message:"}',
    description: 'Get Discord channel ID from user'
});

CREATE (request_title:STEP {
    id: 'request-title',
    function: 'utils.request.request',
    input: '{"prompt": "What title would you like for your announcement?"}',
    description: 'Get title for the embed'
});

CREATE (request_description:STEP {
    id: 'request-description',
    function: 'utils.request.request',
    input: '{"prompt": "Please provide a description for your announcement:"}',
    description: 'Get description for the embed'
});

CREATE (create_embed:STEP {
    id: 'create-embed',
    function: 'utils.generate.generate',
    input: '{"model": "gpt-4o", "temperature": 0.7, "system": "You are a helpful assistant that formats data for Discord embeds. Your job is to take user input and create a JSON structure for a Discord embed with appropriate fields and formatting.", "user": "Please create a Discord embed JSON object with the following information:\\n\\nTitle: @{SESSION_ID}.request-title.response\\nDescription: @{SESSION_ID}.request-description.response\\n\\nAlso add 2-3 relevant fields based on the content, a footer with the current date, and choose an appropriate color hex code based on the content (blue for informational, green for success, red for warnings/alerts, purple for events). Format this as valid JSON that can be placed directly in a Discord API request\'s \'embeds\' array. Do not include any explanation, just return the JSON array with one embed object.", "schema": {"type": "object", "properties": {"embeds": {"type": "array", "description": "Array containing a single embed object formatted for Discord API"}}, "required": ["embeds"]}}',
    description: 'Generate Discord embed JSON'
});

CREATE (send_discord_embed:STEP {
    id: 'send-discord-embed',
    function: 'utils.api.api',
    input: '{"method": "POST", "url": "https://discord.com/api/v10/channels/@{SESSION_ID}.request-channel-id.response/messages", "headers": {"Authorization": "Bot $DISCORD_TOKEN", "Content-Type": "application/json"}, "json_data": @{SESSION_ID}.create-embed.embeds}',
    description: 'Send message with embed to Discord channel'
});

CREATE (process_response:STEP {
    id: 'process-response',
    function: 'utils.generate.generate',
    input: '{"model": "gpt-4o", "temperature": 0.7, "system": "You are a helpful assistant that confirms whether a Discord message was sent successfully.", "user": "I tried to send a Discord message with embeds and received this API response:\\n\\n@{SESSION_ID}.send-discord-embed.response\\n\\nPlease tell me if the message was sent successfully. If there was an error, explain what went wrong and how to fix it."}',
    description: 'Process Discord API response'
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
MATCH (request_title:STEP {id: 'request-title'})
CREATE (request_channel_id)-[:NEXT]->(request_title);

MATCH (request_title:STEP {id: 'request-title'})
MATCH (request_description:STEP {id: 'request-description'})
CREATE (request_title)-[:NEXT]->(request_description);

MATCH (request_description:STEP {id: 'request-description'})
MATCH (create_embed:STEP {id: 'create-embed'})
CREATE (request_description)-[:NEXT]->(create_embed);

MATCH (create_embed:STEP {id: 'create-embed'})
MATCH (send_discord_embed:STEP {id: 'send-discord-embed'})
CREATE (create_embed)-[:NEXT]->(send_discord_embed);

MATCH (send_discord_embed:STEP {id: 'send-discord-embed'})
MATCH (process_response:STEP {id: 'process-response'})
CREATE (send_discord_embed)-[:NEXT]->(process_response);

MATCH (process_response:STEP {id: 'process-response'})
MATCH (reply_result:STEP {id: 'reply-result'})
CREATE (process_response)-[:NEXT]->(reply_result); 