// Fix missing utility property in STEP nodes
// This query finds all STEP nodes that don't have a utility property
// and adds an empty string utility property to them

// First, let's check which STEP nodes are missing the utility property
// MATCH (s:STEP)
// WHERE NOT exists(s.utility)
// RETURN s.id as step_id, labels(s) as labels LIMIT 10;

// Now, let's add the utility property to all STEP nodes that don't have it
MATCH (s:STEP)
WHERE NOT exists(s.utility) 
SET s.utility = ""
RETURN count(s) as updated_nodes;

// Verify the fix was applied
// MATCH (s:STEP)
// WHERE NOT exists(s.utility)
// RETURN count(s) as remaining_nodes_without_utility; 