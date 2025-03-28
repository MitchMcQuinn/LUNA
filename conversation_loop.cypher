// Create the entire workflow graph in a single statement
CREATE 
    (root:STEP {
        id: 'root',
        description: 'Root node for conversation loop'
    })-[:NEXT]->(request:STEP {
        id: 'request',
        function: 'utils.request.request',
        input: '{"prompt": "@{SESSION_ID}.generate.followup|GM! How can I help?"}',
        description: 'Get user input with dynamic prompt'
    })-[:NEXT]->(generate:STEP {
        id: 'generate',
        function: 'utils.generate.generate',
        input: '{"model": "gpt-4o", "temperature": 0.7, "schema": {"type": "object", "properties": {"response": {"type": "string", "description": "A helpful and informative response to the user\'s query that directly addresses their question or request"}, "followup": {"type": "string", "description": "A natural followup question that builds on the conversation context and helps deepen the discussion"}, "merits_followup": {"type": "boolean", "description": "Whether the conversation warrants continuation - true if there are meaningful directions to explore, false if the conversation has reached a natural conclusion"}}, "required": ["response", "followup", "merits_followup"]}, "user": "@{SESSION_ID}.request.response"}',
        description: 'Generate response and followup question'
    })-[:NEXT]->(reply:STEP {
        id: 'reply',
        function: 'utils.reply.reply',
        input: '{"message": "@{SESSION_ID}.generate.response"}',
        description: 'Send response to user'
    }),
    (reply)-[:NEXT {
        conditions: ["@{SESSION_ID}.generate.merits_followup"]
    }]->(request); 