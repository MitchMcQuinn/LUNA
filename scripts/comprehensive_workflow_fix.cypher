// This script provides a comprehensive fix for the workflow by:
// 1. Updating the lookup_followup_session_id step to use the session ID from the correct source
// 2. Fixing any steps that reference the non-existent lookup_subflow_session_id

// First, fix the lookup_followup_session_id step to use the session ID from lookup_channel_session
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

// Fix the send_followup_channel_session_message step to reference the correct session ID source
MATCH (s:STEP {id: 'send_followup_channel_session_message'})
SET s.input = REPLACE(s.input, '@{SESSION_ID}.lookup_subflow_session_id.session_id', '@{SESSION_ID}.lookup_channel_session.result.session_id');

// Find and fix any other steps that might reference lookup_subflow_session_id
MATCH (s:STEP)
WHERE s.input CONTAINS 'lookup_subflow_session_id'
SET s.input = REPLACE(s.input, '@{SESSION_ID}.lookup_subflow_session_id.session_id', '@{SESSION_ID}.lookup_channel_session.result.session_id')
RETURN s.id, s.input AS updated_input;

// Verify all updates
MATCH (s:STEP)
WHERE s.id IN ['lookup_followup_session_id', 'send_followup_channel_session_message']
   OR s.input CONTAINS 'lookup_channel_session.result.session_id'
RETURN s.id, s.function, s.input; 