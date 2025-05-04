// Update existing nodes to use schema_name instead of full schema
// First find all nodes that have a schema property and replace it with schema_name

// Create a schema collection node if it doesn't exist
MERGE (schemas:SchemaCollection {name: "schemas"})
SET schemas.description = "Collection of predefined schemas for LLM utilities";

// Create references to schema packages
MERGE (reimbursement:Schema {name: "reimbursement"})
SET reimbursement.description = "Schema for reimbursement requests processing",
    reimbursement.path = "utils.schemas.reimbursement";

// Connect schemas to the collection
MERGE (schemas)-[:CONTAINS]->(reimbursement);

// Find nodes with the string "additionalProperties":false in schema (JSON format) and replace with Python format
MATCH (n)
WHERE n.schema IS NOT NULL AND n.schema CONTAINS '"additionalProperties":false'
SET n.schema = apoc.text.replace(n.schema, '"additionalProperties":false', '"additionalProperties":False');

// Update system messages to use empty strings instead of 'None'
MATCH (n)
WHERE n.system IS NOT NULL AND n.system CONTAINS "set the token value to 'None'"
SET n.system = apoc.text.replace(
    n.system, 
    "set the token value to 'None'", 
    "set the token value to an empty string"
);

// Update system messages to set chain default to ETH
MATCH (n)
WHERE n.system IS NOT NULL AND n.system CONTAINS "set the chain value to 'None', assume it's ETH"
SET n.system = apoc.text.replace(
    n.system, 
    "set the chain value to 'None', assume it's ETH", 
    "set the chain value to 'ETH' as default"
);

// Find nodes that use the reimbursement schema and update them
MATCH (n)
WHERE n.schema IS NOT NULL AND n.schema CONTAINS "reimbursement_requests"
SET n.schema_name = "reimbursement",
    n.schema = null;

// Update the generate function's config to use schema_name instead of schema
MATCH (config)-[:HAS_PROPERTY]->(prop)
WHERE prop.name = "schema" AND prop.value CONTAINS "reimbursement_requests"
SET prop.name = "schema_name",
    prop.value = "reimbursement";

// Update any workflows using the generate function to switch schema to schema_name
MATCH (n)-[r:CALLS]->(generate:Function {name: "generate"})
WHERE exists(r.params.schema) AND r.params.schema CONTAINS "reimbursement_requests"
SET r.params.schema_name = "reimbursement",
    r.params.schema = null; 