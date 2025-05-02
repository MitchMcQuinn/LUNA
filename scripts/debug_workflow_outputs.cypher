// Debug script to check workflow structure and session outputs

// 1. First, check workflow structure to see step ordering and dependency graph
MATCH (w:WORKFLOW {id: 'discord_operator'})-[:HAS_STEP]->(s:STEP)
RETURN w.id as workflow_id, s.id as step_id, s.function as function
ORDER BY s.id;

// 2. Check all outgoing edges from workflow to understand paths between steps
MATCH (w:WORKFLOW {id: 'discord_operator'})-[r]->(s:STEP)
RETURN w.id as workflow_id, type(r) as relationship_type, s.id as step_id
ORDER BY s.id;

// 3. Check inputs for create_channel_session step
MATCH (s:STEP {id: 'create_channel_session'})
RETURN s.id, s.function, s.input;

// 4. Check inputs for lookup_followup_session_id step
MATCH (s:STEP {id: 'lookup_followup_session_id'})
RETURN s.id, s.function, s.input;

// 5. Check transitions to understand workflow routing
MATCH (s1:STEP)-[r:TRANSITIONS_TO]->(s2:STEP)
WHERE s1.id IN ['create_channel_session', 'lookup_followup_session_id', 'send_session_followup_message']
   OR s2.id IN ['create_channel_session', 'lookup_followup_session_id', 'send_session_followup_message']
RETURN s1.id as from_step, r.condition as condition, s2.id as to_step;

// 6. Examine the actual session state of a recent execution
// Replace the session ID with a real one from your tests
MATCH (s:SESSION {id: 'REPLACE_WITH_ACTUAL_SESSION_ID'})
RETURN s.id, s.state;

// 7. Check all message nodes to see what's being created
MATCH (m:MESSAGE)
RETURN m.message_id, m.session_id, m.author_username
LIMIT 20; 