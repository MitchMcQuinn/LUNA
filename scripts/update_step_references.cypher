// Update the lookup_followup_session_id step to use the references from send_followup_channel_session_message
MATCH (s:STEP {id: 'lookup_followup_session_id'})
SET s.function = 'utils.code.code'
SET s.input = '{
  "file_path": "lookup_followup_session_id.py",
  "variables": {
    "message_id": "@{SESSION_ID}.initial.message.id",
    "response_id": "@{SESSION_ID}.send_followup_channel_session_message[0].response.messages[4]._message_id",
    "response_content": "@{SESSION_ID}.send_followup_channel_session_message[0].response.messages[4].content",
    "author_username": "bot",
    "created_at": "@{SESSION_ID}.send_followup_channel_session_message[0].response.messages[4].timestamp",
    "channel_id": "@{SESSION_ID}.initial.channel_id"
  }
}';

// Update the log_followup_session_message step to use the correct message index
MATCH (s:STEP {id: 'log_followup_session_message'})
SET s.function = 'utils.code.code'
SET s.input = '{
  "file_path": "log_followup_session_message.py",
  "variables": {
    "session_id": "@{SESSION_ID}.lookup_channel_session.result.session_id",
    "message_id": "@{SESSION_ID}.lookup_channel_session.result.message_id",
    "response_id": "@{SESSION_ID}.send_followup_channel_session_message[0].response.messages[4]._message_id",
    "response_content": "@{SESSION_ID}.send_followup_channel_session_message[0].response.messages[4].content",
    "author_username": "bot",
    "created_at": "@{SESSION_ID}.send_followup_channel_session_message[0].response.messages[4].timestamp",
    "channel_id": "@{SESSION_ID}.initial.channel_id"
  }
}'; 