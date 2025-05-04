// Update the path conditions in the reimbursement workflow
// These changes are based on the tests/fix_workflow.py file

// Update the path condition from generate_reimbursement_request to request-reimbursement
// Ensure it doesn't depend on merits_followup
MATCH (source:STEP {id: 'generate_reimbursement_request'})-[r:NEXT]->(target:STEP {id: 'request-reimbursement'})
SET r.condition = '[{"false":"@{SESSION_ID}.generate_reimbursement_request.reimbursement_requests[0].is_complete"}]'
RETURN source.id as source, target.id as target, r.condition as updated_condition;

// Update the path condition from generate_reimbursement_request to reply_reimbursement_request
// Ensure it doesn't depend on merits_followup
MATCH (source:STEP {id: 'generate_reimbursement_request'})-[r:NEXT]->(target:STEP {id: 'reply_reimbursement_request'})
SET r.condition = '[{"true":"@{SESSION_ID}.generate_reimbursement_request.reimbursement_requests[0].is_complete"}]'
RETURN source.id as source, target.id as target, r.condition as updated_condition; 