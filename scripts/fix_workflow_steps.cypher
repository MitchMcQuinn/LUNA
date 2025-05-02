// Query to update log_initial_session_message step
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

// Query to update lookup_followup_session_id step with dynamic session ID from lookup_channel_session
MATCH (s:STEP {id: 'lookup_followup_session_id'})
SET s.function = 'utils.code.code'
SET s.input = '{
  "file_path": "lookup_followup_session_id.py",
  "variables": {
    "session_id": "@{SESSION_ID}.lookup_channel_session.result.session_id",
    "message_id": "@{SESSION_ID}.initial.message.id",
    "response_id": "@{SESSION_ID}.send_session_followup_message.result.response.id",
    "response_content": "@{SESSION_ID}.send_session_followup_message.result.response.content",
    "author_username": "bot",
    "created_at": "@{SESSION_ID}.send_session_followup_message.result.response.timestamp",
    "channel_id": "@{SESSION_ID}.initial.channel_id"
  }
}';

// Query to update lookup_followup_session_id step with proper session reference
// (This is an alternative approach using the proper reference path)
MATCH (s:STEP {id: 'lookup_followup_session_id'})
SET s.function = 'utils.code.code'
SET s.input = '{
  "file_path": "lookup_followup_session_id.py", 
  "variables": {
    "session_id": "@{SESSION_ID}.create_channel_session[0].response.session_id",
    "message_id": "@{SESSION_ID}.initial.message.id",
    "response_id": "@{SESSION_ID}.send_session_followup_message.result.response.id",
    "response_content": "@{SESSION_ID}.send_session_followup_message.result.response.content",
    "author_username": "bot",
    "created_at": "@{SESSION_ID}.send_session_followup_message.result.response.timestamp",
    "channel_id": "@{SESSION_ID}.initial.channel_id" 
  }
}'; 