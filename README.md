## Core Architecture

### Key Concepts

1. **Graph-Based Workflow Representation**
   - Workflows defined as directed graphs in Neo4j
   - Steps (nodes) contain execution logic
   - Paths (edges) define flow with conditional branching

2. **State-Driven Execution**
   - Each workflow session maintains its state in Neo4j
   - Comprehensive tracking of step execution status
   - Clean separation between execution state and data
   - Timestamp-based tracking of step evaluation
   - Error handling with detailed error messages stored per step

3. **Versioned Variable Resolution System**
   - Dynamic variable references between steps
   - Format: `@{SESSION_ID}.step_id[index].field|default`
   - Optional indexing of multiple step executions
   - Maintains a rolling window of the last 5 outputs per step
   - Allows flexible data passing between steps and iterations

4. **User Interaction Support**
   - Steps can request and await user input
   - Session state management during waiting periods
   - Smooth resumption after input received

## Graph Ontology

### Node Types and Properties

#### SESSION Node
Primary node for storing workflow state and execution data.

| Property    | Type      | Description                                |
|-------------|-----------|-------------------------------------------|
| id          | String    | Unique identifier (UUID)                  |
| state       | JSON      | Complete serialized state object          |
| created_at  | DateTime  | Timestamp when session was created        |

The `state` JSON contains the following structure:
```json
{
  "id": "UUID",                  // Same as node id
  "workflow": {                  // Step status tracking
    "step_id": {
      "status": "active|pending|complete|error|awaiting_input",
      "error": "",                // Error message if applicable
      "last_executed": 1234567890 // Timestamp of last execution
    }
  },
  "last_evaluated": 1234567890,  // Timestamp of last path evaluation
  "data": {
    "outputs": {                 // Results from each step
      "step_id": [],             // Array of outputs, most recent last (max 5)
    },
    "messages": []               // Optional chat history
  }
}
```

## Core Components

### 3. Variable Resolution
A critical component for data flow between steps and iterations, resolving variable references from session state.

- Supports references to the most recent output: `@{SESSION_ID}.step_id.field`
- Supports indexed access to output history: `@{SESSION_ID}.step_id[2].field`
- Default behavior uses most recent output when no index specified
- Maintains a rolling window of the last 5 outputs per step

## Workflow Engine Logic

### Initialization
1. Create a Neo4j driver connection
2. Generate a unique session ID
3. Create a SESSION node with a state object initialized as:
  ```json
  {
    "id": "[UUID]",                  // Same as node id
    "workflow": {                    // Step status tracking
      "root": {
        "status": "active",          // Initial step status
        "error": ""                  // Error message if applicable
      }
    },
    "last_evaluated": 0,             // Initial path evaluation timestamp
    "data": {
      "outputs": {},                 // Results from each step
      "messages": []                 // Optional chat history
    }
  }
  ```

### Workflow Processing Loop
The engine processes steps in the following order:

1. **Find Active Steps**
   - Get current session state
   - Find all steps with status 'active' or 'pending'
   - If no active steps found:
     - Check if root step needs activation
     - If root step exists and isn't complete, activate it
     - Otherwise, workflow is complete

2. **Process Steps**
   For each pending step:
   - Get step details from Neo4j (function and input)
   - Resolve input variables:
     - Parse input JSON if needed
     - Look up each variable in state.data.outputs (using most recent values by default)
     - If any required variables missing:
       - Mark step as 'pending'
       - Continue to next step
   - Execute step:
     - If function is "utils.request.request":
       - Mark step as 'awaiting_input'
       - Pause workflow
     - If function exists:
       - Execute with resolved inputs
       - Store result in state.data.outputs[step_id] as a new array entry
       - Limit array to most recent 5 outputs
       - Mark step as 'complete'
       - Record execution timestamp
     - If function missing:
       - Mark step as 'error'
       - Store detailed error message in state
       - Allow error inspection in UI

3. **Path Progression**
   - Find steps completed since last path evaluation
   - For each newly completed step:
     - Find outgoing NEXT relationships
     - For each relationship:
       - Evaluate conditions if present:
         - Resolve each condition variable (using most recent outputs)
         - Apply operator logic (AND/OR)
       - If conditions met:
         - Check if target step exists
         - If step exists and not already active:
           - Mark as 'active' in state.workflow
         - If step has error:
           - Skip activation
     - Sort next steps by priority if specified
   - Update last path evaluation timestamp

4. **Continue Processing Until:**
   - No active steps remain
   - All active steps are pending
   - Step requests user input
   - Maximum iterations reached (safety limit)
   - Error occurs

### User Input Handling
When a step requests user input:
1. Workflow pauses at 'awaiting_input' state
2. User provides input
3. Input is processed and stored in step's output array
4. Step is marked as complete with current timestamp
5. Workflow resumes processing 

### Error Handling
When errors occur during step execution:
1. Error details are captured and stored in the step's state
2. Step is marked with 'error' status
3. Error messages are made available to the UI
4. Workflow may continue with other branches if possible
5. Error information can be used for debugging or recovery 