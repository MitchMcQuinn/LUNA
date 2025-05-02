// Update the log_followup_session_message step to use the last message from the API response
MATCH (s:STEP {id: 'log_followup_session_message'})
SET s.function = 'utils.code.code'
SET s.input = '{
  "file_path": "log_followup_session_message.py",
  "variables": {
    "session_id": "@{SESSION_ID}.lookup_channel_session.result.session_id",
    "message_id": "@{SESSION_ID}.lookup_channel_session.result.message_id",
    "response_id": "@{SESSION_ID}.send_followup_channel_session_message[0].response.id",
    "response_content": "@{SESSION_ID}.send_followup_channel_session_message[0].response.messages[-1].content",
    "author_username": "bot",
    "created_at": "@{SESSION_ID}.send_followup_channel_session_message[0].response.messages[-1].timestamp",
    "channel_id": "@{SESSION_ID}.initial.channel_id"
  }
}';

// Update the lookup_followup_session_id step to be consistent with the approach above
MATCH (s:STEP {id: 'lookup_followup_session_id'})
SET s.function = 'utils.code.code'
SET s.input = '{
  "file_path": "lookup_followup_session_id.py",
  "variables": {
    "message_id": "@{SESSION_ID}.lookup_channel_session.result.message_id",
    "response_id": "@{SESSION_ID}.send_followup_channel_session_message[0].response.id",
    "response_content": "@{SESSION_ID}.send_followup_channel_session_message[0].response.messages[-1].content",
    "author_username": "bot",
    "created_at": "@{SESSION_ID}.send_followup_channel_session_message[0].response.messages[-1].timestamp",
    "channel_id": "@{SESSION_ID}.initial.channel_id"
  }
}'; 