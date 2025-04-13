// Delete existing workflow if any
MATCH (s:STEP) DETACH DELETE s;

// Create workflow steps
CREATE (root:STEP {
    id: 'root',
    description: 'Root node for conversation loop'
});

CREATE (request:STEP {
    id: 'request',
    function: 'utils.request.request',
    input: '{"prompt": "@{SESSION_ID}.generate.followup|GM! How can I help?"}',
    description: 'Get user input with dynamic prompt'
});

CREATE (generate:STEP {
    id: 'generate',
    function: 'utils.generate.generate',
    input: '{"model": "gpt-4o", "temperature": 0.7, "include_history": true, "system": "You are a helpful assistant engaged in an ongoing conversation. Maintain full context of the conversation history when responding. Reference previous messages when appropriate. Don\'t repeat information that has already been discussed unless it\'s to build upon it. Be INCREDIBLY brief.", "schema": {"type": "object", "properties": {"response": {"type": "string", "description": "A helpful and informative response to the user\'s query that directly addresses their question or request, building upon previous conversation context"}, "followup": {"type": "string", "description": "A natural followup question that builds on the conversation context and helps deepen the discussion"}, "merits_followup": {"type": "boolean", "description": "Whether the conversation warrants continuation - true if there are meaningful directions to explore, false if the conversation has reached a natural conclusion. If the user responds with a flat no then it is likely an end to the conversation, but this should be assessed within the conversational context."}, "is_moondao_question": {"type": "boolean", "description": "Whether the user\'s query is about Moondao. Return true if the query mentions Moondao or Moondao related topics such as governance, projects, members, citizenship, onboarding, voting, the senate, community circles, rewards, the constitution, or the DAO."}}, "required": ["response", "followup", "merits_followup", "is_moondao_question"]}, "user": "@{SESSION_ID}.request.response"}',
    description: 'Generate response and followup question with conversation history'
});

CREATE (reply:STEP {
    id: 'reply',
    function: 'utils.reply.reply',
    input: '{"message": "@{SESSION_ID}.generate.response"}',
    description: 'Send response to user'
});

CREATE (moondao_reply:STEP {
    id: 'moondao_reply',
    function: 'utils.reply.reply',
    input: '{"message": "THAT WAS A MOONDAO QUESTION! I LOVE MOONDAO! One moment please while I look up the answer..."}',
    description: 'Send MoonDAO response to user'
});

CREATE (send_farewell:STEP {
    id: 'send-farewell',
    function: 'utils.reply.reply',
    input: '{"message": "okay, GN!"}',
    description: 'Send farewell message'
});

// Create workflow connections
MATCH (root:STEP {id: 'root'})
MATCH (request:STEP {id: 'request'})
CREATE (root)-[:NEXT]->(request);

MATCH (request:STEP {id: 'request'})
MATCH (generate:STEP {id: 'generate'})
CREATE (request)-[:NEXT]->(generate);

// Create conditional paths from generate
MATCH (generate:STEP {id: 'generate'})
MATCH (moondao_reply:STEP {id: 'moondao_reply'})
CREATE (generate)-[:NEXT {conditions: ['[{"operator": "AND", "true": "@{SESSION_ID}.generate.merits_followup", "true": "@{SESSION_ID}.generate.is_moondao_question"}']}]->(moondao_reply);

MATCH (generate:STEP {id: 'generate'})
MATCH (send_farewell:STEP {id: 'send-farewell'})
CREATE (generate)-[:NEXT {conditions: ['[{"false": "@{SESSION_ID}.generate.merits_followup"}']}]->(send_farewell);

MATCH (generate:STEP {id: 'generate'})
MATCH (reply:STEP {id: 'reply'})
CREATE (generate)-[:NEXT {conditions: ['[{"operator": "AND", "true": "@{SESSION_ID}.generate.merits_followup", "false": "@{SESSION_ID}.generate.is_moondao_question"}']}]->(reply);

// Create loop back to request from reply and moondao_reply
MATCH (reply:STEP {id: 'reply'})
MATCH (request:STEP {id: 'request'})
CREATE (reply)-[:NEXT]->(request);

MATCH (moondao_reply:STEP {id: 'moondao_reply'})
MATCH (request:STEP {id: 'request'})
CREATE (moondao_reply)-[:NEXT]->(request); 