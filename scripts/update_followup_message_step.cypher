// Check if the log_followup_session_message step exists
MATCH (s:STEP {id: 'log_followup_session_message'})
RETURN s.id, s.function, s.input;

// Update the log_followup_session_message step to use the code.py implementation
MATCH (s:STEP {id: 'log_followup_session_message'})
SET s.function = 'utils.code.code'
SET s.input = '{
  "file_path": "log_followup_session_message.py",
  "variables": {
    "session_id": "@{SESSION_ID}.lookup_channel_session.result.session_id",
    "message_id": "@{SESSION_ID}.lookup_channel_session.result.message_id",
    "response_id": "@{SESSION_ID}.send_followup_channel_session_message[0].response.messages[2]._message_id",
    "response_content": "@{SESSION_ID}.send_followup_channel_session_message[0].response.messages[2].content",
    "author_username": "bot",
    "created_at": "@{SESSION_ID}.send_followup_channel_session_message[0].response.messages[2].timestamp",
    "channel_id": "@{SESSION_ID}.initial.channel_id"
  }
}';

// If the step doesn't exist, we need to create it
// First check the workflow transitions to see where it should be inserted
MATCH (w:WORKFLOW {id: 'discord_operator'})-[:HAS_STEP]->(s1:STEP {id: 'send_followup_channel_session_message'})
MATCH (w)-[:HAS_STEP]->(s2)
WHERE NOT s1.id = s2.id
RETURN w.id, s1.id, s2.id;

// Create the step if it doesn't exist
MERGE (s:STEP {id: 'log_followup_session_message'})
ON CREATE SET 
  s.function = 'utils.code.code',
  s.input = '{
    "file_path": "log_followup_session_message.py",
    "variables": {
      "session_id": "@{SESSION_ID}.lookup_channel_session.result.session_id",
      "message_id": "@{SESSION_ID}.lookup_channel_session.result.message_id",
      "response_id": "@{SESSION_ID}.send_followup_channel_session_message[0].response.messages[2]._message_id",
      "response_content": "@{SESSION_ID}.send_followup_channel_session_message[0].response.messages[2].content",
      "author_username": "bot",
      "created_at": "@{SESSION_ID}.send_followup_channel_session_message[0].response.messages[2].timestamp",
      "channel_id": "@{SESSION_ID}.initial.channel_id"
    }
  }',
  s.name = 'Log Followup Message',
  s.description = 'Log the bot reply to the Neo4j database';

// Connect the step to the discord_operator workflow if it's not already connected
MATCH (w:WORKFLOW {id: 'discord_operator'})
MATCH (s:STEP {id: 'log_followup_session_message'})
MERGE (w)-[:HAS_STEP]->(s);

// Add transition from send_followup_channel_session_message to log_followup_session_message if it doesn't exist
MATCH (w:WORKFLOW {id: 'discord_operator'})
MATCH (s1:STEP {id: 'send_followup_channel_session_message'})
MATCH (s2:STEP {id: 'log_followup_session_message'})
MERGE (t:TRANSITION {id: 'send_followup_to_log_followup'})
MERGE (w)-[:HAS_TRANSITION]->(t)
MERGE (t)-[:FROM]->(s1)
MERGE (t)-[:TO]->(s2); 