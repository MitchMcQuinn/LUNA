// Update existing nodes to use agent packages instead of explicit configuration

// Create an agent collection node if it doesn't exist
MERGE (agents:AgentCollection {name: "agents"})
SET agents.description = "Collection of predefined agent configurations for LLM utilities";

// Create references to agent packages
MERGE (reimbursement_agent:Agent {name: "reimbursement_processor"})
SET reimbursement_agent.description = "Agent for processing reimbursement requests",
    reimbursement_agent.path = "utils.agents.reimbursement_processor";

// Connect agents to the collection
MERGE (agents)-[:CONTAINS]->(reimbursement_agent);

// Find all steps that use generate with reimbursement schema and update to use agent package
MATCH (s:STEP)-[r:CALLS|:EXECUTES]->(f:FUNCTION {name: "generate"})
WHERE exists(r.params.schema_name) AND r.params.schema_name = "reimbursement"
  AND exists(r.params.system) AND r.params.system CONTAINS "reimbursement"
WITH s, r, r.params as params
// Store the value of include_history if it exists
WITH s, r, params, 
     CASE WHEN exists(r.params.include_history) THEN r.params.include_history ELSE null END as include_history_value
// Remove only model, temperature, and system parameters (keep include_history)
REMOVE r.params.model, r.params.temperature, r.params.system
// Add the agent parameter
SET r.params.agent = "reimbursement_processor"
// If include_history was specified before, set it again
WITH s, r, include_history_value
WHERE include_history_value IS NOT NULL
SET r.params.include_history = include_history_value;

// Find all config nodes that need to be updated
MATCH (config:CONFIG)-[:HAS_PROPERTY]->(system_prop)
WHERE system_prop.name = "system" AND system_prop.value CONTAINS "reimbursement"
MATCH (config)-[:HAS_PROPERTY]->(schema_prop)
WHERE schema_prop.name = "schema_name" AND schema_prop.value = "reimbursement"
// Store the existing include_history value if it exists
WITH config, 
     CASE WHEN exists((config)-[:HAS_PROPERTY]->(:PROPERTY {name: "include_history"})) 
     THEN (config)-[:HAS_PROPERTY]->(:PROPERTY {name: "include_history"}).value 
     ELSE null END as include_history_value
// Delete only model, temperature, and system properties (keep include_history)
MATCH (config)-[:HAS_PROPERTY]->(prop)
WHERE prop.name IN ["model", "temperature", "system"]
DETACH DELETE prop
// Add the agent property
MERGE (config)-[:HAS_PROPERTY]->(:PROPERTY {name: "agent", value: "reimbursement_processor"}); 