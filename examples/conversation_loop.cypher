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
        input: '{"model": "gpt-4o", "temperature": 0.7, "include_history": true, "system": "You are a helpful assistant engaged in an ongoing conversation. Maintain full context of the conversation history when responding. Reference previous messages when appropriate. Don\'t repeat information that has already been discussed unless it\'s to build upon it. Be INCREDIBLY brief.", "schema": {"type": "object", "properties": {"response": {"type": "string", "description": "A helpful and informative response to the user\'s query that directly addresses their question or request, building upon previous conversation context"}, "followup": {"type": "string", "description": "A natural followup question that builds on the conversation context and helps deepen the discussion"}, "merits_followup": {"type": "boolean", "description": "Whether the conversation warrants continuation - true if there are meaningful directions to explore, false if the conversation has reached a natural conclusion. If the user responds with a flat no then it is likely an end to the conversation, but this should be assessed within the conversational context."}, "is_movie_question": {"type": "boolean", "description": "Whether the user\'s query is about a movie or actor. Return true if the query mentions or asks about any movie, film, actor, director, or other film-related topics."}}, "required": ["response", "followup", "merits_followup", "is_movie_question"]}, "user": "@{SESSION_ID}.request.response"}',
        description: 'Generate response and followup question with conversation history'
    }),
    (generate)-[:NEXT {
        condition: '[{"true":"@{SESSION_ID}.generate.merits_followup"}]'
    }]->(reply:STEP {
        id: 'reply',
        function: 'utils.reply.reply',
        input: '{"message": "@{SESSION_ID}.generate.response ...Followup? @{SESSION_ID}.generate.merits_followup"}',
        description: 'Send response to user'
    }),
    (generate)-[:NEXT {
        condition: '[{"false":"@{SESSION_ID}.generate.merits_followup"}]'
    }]->(send_farewell:STEP {
        id: 'send-farewell',
        function: 'utils.reply.reply',
        input: '{"message": "okay, GN!"}',
        description: 'Send farewell message'
    }),
    (reply)-[:NEXT]->(request); 