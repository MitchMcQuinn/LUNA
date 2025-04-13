# Cypher Utility for Neo4j Graph Operations

This utility allows workflows to interact with the Neo4j graph database using either direct Cypher queries or natural language instructions.

## Features

- **Dual Mode Operation**: Run pre-defined queries or generate queries from natural language
- **Variable Resolution**: Use workflow variables in your queries with `@{SESSION_ID}.step_id.field` syntax
- **Safety Checks**: Confirmation requests for potentially destructive operations
- **Result Size Limiting**: Prevent overwhelming results
- **Error Handling**: Automatic retry with error feedback
- **Transaction Support**: Write operations use transactions for atomicity
- **Result Explanation**: Natural language overview of query results

## Usage Examples

### Direct Mode (Pre-defined Query)

```json
{
  "function": "utils.cypher.cypher",
  "input": {
    "query": "MATCH (s:SESSION) WHERE s.created_at > datetime() - duration('P7D') RETURN s",
    "max_results": 100
  }
}
```

### Dynamic Mode (Natural Language)

```json
{
  "function": "utils.cypher.cypher",
  "input": {
    "instruction": "Find all user sessions created in the last week",
    "ontology": "SESSION nodes have id, created_at properties...",
    "safety_on": true
  }
}
```

### Using Variable References

```json
{
  "function": "utils.cypher.cypher",
  "input": {
    "query": "MATCH (s:STEP) WHERE s.id = @{SESSION_ID}.previous_step[0].value RETURN s",
    "session_id": "{SESSION_ID}"
  }
}
```

### Safe Write Operations

```json
{
  "function": "utils.cypher.cypher",
  "input": {
    "query": "CREATE (n:NODE {id: 'new-node'})",
    "safety_on": true,
    "confirmed": false  // Set to true to skip confirmation
  }
}
```

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | Pre-defined Cypher query to execute directly |
| `instruction` | string | Natural language instruction to generate a query |
| `safety_on` | boolean | Whether to apply safety checks for write operations (default: true) |
| `previous_error` | string | Error from previous attempt, for retry guidance |
| `ontology` | string | Description of graph ontology to guide query generation |
| `max_retries` | integer | Maximum number of retry attempts for failed queries (default: 5) |
| `max_results` | integer | Maximum number of results to return (default: 1000) |
| `confirmed` | boolean | Whether write operation has been confirmed by user (default: false) |
| `session_id` | string | Current workflow session ID for variable resolution |

## Return Value

The utility returns a JSON object with the following fields:

```json
{
  "query": "The executed Cypher query",
  "result": [
    {
      "field1": "value1",
      "field2": "value2"
    }
  ],
  "overview": "Natural language explanation of the results"
}
```

If an error occurs, the result will include an `error` field with the error message. 