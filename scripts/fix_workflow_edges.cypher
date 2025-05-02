// First examine the current workflow connections related to send_followup_channel_session_message
MATCH (s1:STEP)-[r]->(s2:STEP)
WHERE s1.id = 'send_followup_channel_session_message' OR s2.id = 'send_followup_channel_session_message'
RETURN s1.id, type(r), r.condition, s2.id;

// Check the inputs for the problematic send_followup_channel_session_message step
MATCH (s:STEP {id: 'send_followup_channel_session_message'})
RETURN s.id, s.function, s.input;

// Update the input of send_followup_channel_session_message to directly reference the session ID
// found by lookup_channel_session instead of trying to use lookup_subflow_session_id
MATCH (s:STEP {id: 'send_followup_channel_session_message'})
SET s.input = REPLACE(s.input, '@{SESSION_ID}.lookup_subflow_session_id.session_id', '@{SESSION_ID}.lookup_channel_session.result.session_id');

// Verify the changes
MATCH (s:STEP {id: 'send_followup_channel_session_message'})
RETURN s.id, s.function, s.input; 