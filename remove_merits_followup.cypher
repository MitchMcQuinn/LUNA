// Remove vestigial references from path conditions in the Neo4j database
// This script will find and modify all NEXT relationships that use merits_followup or is_movie_question

// First, identify all relationships that use merits_followup or is_movie_question in their condition
MATCH (s:STEP)-[r:NEXT]->(t:STEP)
WHERE r.condition CONTAINS 'merits_followup' OR r.condition CONTAINS 'is_movie_question'
RETURN s.id as source, t.id as target, r.condition as condition;

// Update all relationships that check if merits_followup is TRUE
// Replace with a simple TRUE condition (1==1) to always follow this path
MATCH (s:STEP)-[r:NEXT]->(t:STEP)
WHERE r.condition CONTAINS 'true":"@{SESSION_ID}' AND r.condition CONTAINS 'merits_followup'
SET r.condition = '[{"true":"1==1"}]'
RETURN s.id as source, t.id as target, r.condition as new_condition;

// Update all relationships that check if merits_followup is FALSE
// Replace with a simple FALSE condition (1==0) to never follow this path
MATCH (s:STEP)-[r:NEXT]->(t:STEP)
WHERE r.condition CONTAINS 'false":"@{SESSION_ID}' AND r.condition CONTAINS 'merits_followup'
SET r.condition = '[{"false":"1==1"}]'
RETURN s.id as source, t.id as target, r.condition as new_condition;

// Update all relationships that check if is_movie_question is TRUE
MATCH (s:STEP)-[r:NEXT]->(t:STEP)
WHERE r.condition CONTAINS 'true":"@{SESSION_ID}' AND r.condition CONTAINS 'is_movie_question'
SET r.condition = '[{"true":"1==1"}]'
RETURN s.id as source, t.id as target, r.condition as new_condition;

// Update all relationships that check if is_movie_question is FALSE
MATCH (s:STEP)-[r:NEXT]->(t:STEP)
WHERE r.condition CONTAINS 'false":"@{SESSION_ID}' AND r.condition CONTAINS 'is_movie_question'
SET r.condition = '[{"false":"1==1"}]'
RETURN s.id as source, t.id as target, r.condition as new_condition;

// Update any conditions with complex AND/OR conditions
// This is more complex and requires a case-by-case approach
// We'll log these for manual review

MATCH (s:STEP)-[r:NEXT]->(t:STEP)
WHERE (r.condition CONTAINS 'merits_followup' OR r.condition CONTAINS 'is_movie_question') 
  AND r.condition CONTAINS 'AND'
RETURN s.id as source, t.id as target, r.condition as condition
WITH 'Complex conditions with vestigial fields found - manual review required' as message, collect({source: source, target: target, condition: condition}) as complex_conditions
RETURN message, complex_conditions;

// Count how many relationships still contain vestigial fields after updates
MATCH (s:STEP)-[r:NEXT]->(t:STEP)
WHERE r.condition CONTAINS 'merits_followup' OR r.condition CONTAINS 'is_movie_question'
RETURN count(r) as remaining_conditions; 