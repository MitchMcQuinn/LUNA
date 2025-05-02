// First, review the current step configuration
MATCH (s:STEP {id: 'lookup_followup_session_id'})
RETURN s.function, s.input;

// Get the workflow structure to understand step relationships
MATCH (w:WORKFLOW {id: 'discord_operator'})-[:HAS_STEP]->(s:STEP)
RETURN w.id, s.id
ORDER BY s.id;

// Update the log_initial_session_message step
MATCH (s:STEP {id: 'log_initial_session_message'})
SET s.function = 'utils.code.code'
SET s.input = '{
  "file_path": "log_initial_session_message.py",
  "variables": {
    "session_id": "@{SESSION_ID}.create_channel_session[0].response.session_id",
    "message_id": "@{SESSION_ID}.initial.message.id",
    "content": "@{SESSION_ID}.initial.message.content",
    "author_username": "@{SESSION_ID}.initial.author.username",
    "created_at": "@{SESSION_ID}.initial.message.createdAt", 
    "channel_id": "@{SESSION_ID}.initial.channel_id",
    "guild_id": "@{SESSION_ID}.initial.guild.id"
  }
}';

// Update the lookup_channel_session step
MATCH (s:STEP {id: 'lookup_channel_session'})
SET s.function = 'utils.code.code'
SET s.input = '{
  "file_path": "lookup_channel_session.py",
  "variables": {
    "channel_id": "@{SESSION_ID}.initial.channel_id"
  }
}';

// Update the lookup_followup_session_id step
MATCH (s:STEP {id: 'lookup_followup_session_id'})
SET s.function = 'utils.code.code'
SET s.input = '{
  "file_path": "lookup_followup_session_id.py",
  "variables": {
    "message_id": "@{SESSION_ID}.initial.message.id",
    "response_id": "@{SESSION_ID}.send_session_followup_message.result.response.id",
    "response_content": "@{SESSION_ID}.send_session_followup_message.result.response.content",
    "author_username": "bot",
    "created_at": "@{SESSION_ID}.send_session_followup_message.result.response.timestamp",
    "channel_id": "@{SESSION_ID}.initial.channel_id"
  }
}'; 