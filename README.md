# Neo4j Graph-Based Workflow Engine

## Overview

This project implements a powerful, flexible workflow engine that uses Neo4j as its graph database backend. The system represents workflows as directed graphs where nodes are processing steps and edges define execution flow with conditional logic. This project is an general-purpose framework and is workflow agnostic!

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

3. **Variable Resolution System**
   - Dynamic variable references between steps
   - Format: `@{SESSION_ID}.step_id.field|default`
   - Allows flexible data passing between steps

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
      "error": ""                // Error message if applicable
    }
  },
  "data": {
    "outputs": {                 // Results from each step
      "step_id": {},             // Output value (any structure)
    },
    "messages": []               // Optional chat history
  }
}
```

#### STEP Node
Represents a single processing unit in the workflow.

| Property    | Type      | Description                                |
|-------------|-----------|-------------------------------------------|
| id          | String    | Unique step identifier                    |
| function    | String    | Function reference (e.g., "utils.generate") |
| input       | JSON      | Input parameters with variable references |
| description | String    | Optional human-readable description       |
| tags        | String[]  | Optional categorization tags              |

The `input` JSON contains parameter names mapped to values or variable references:
```json
{
  "param_name": "static value",
  "variable_param": "@{SESSION_ID}.step_id.field|default value"
}
```

### Relationship Types and Properties

#### NEXT Relationship
Defines flow between steps, optionally with conditions.

| Property    | Type      | Description                                |
|-------------|-----------|-------------------------------------------|
| id          | String    | Optional identifier for the relationship  |
| conditions  | String[]  | Array of variable references to evaluate  |
| operator    | String    | Logic operator: "AND" or "OR" (default: "AND") |
| priority    | Integer   | Optional execution priority (lower = higher priority) |
| description | String    | Optional human-readable description       |

### Graph Schema Example

```cypher
// Define constraints
CREATE CONSTRAINT session_id IF NOT EXISTS FOR (s:SESSION) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT step_id IF NOT EXISTS FOR (s:STEP) REQUIRE s.id IS UNIQUE;

// Example session node
CREATE (s:SESSION {
  id: "abc123",
  state: '{"id":"abc123","workflow":{"root":{"status":"active","error":""}},"data":{"outputs":{},"messages":[]}}',
  created_at: datetime()
});

// Example step nodes
CREATE (root:STEP {
  id: "root",
  function: "utils.request",
  input: '{"prompt":"How can I help you today?"}',
  description: "Initial user query"
});

CREATE (process:STEP {
  id: "process-query",
  function: "generate.generate",
  input: '{"prompt":"@{SESSION_ID}.root|","model":"gpt-4"}',
  description: "Process user query"
});

// Example relationship
CREATE (root)-[:NEXT {
  conditions: ["@{SESSION_ID}.root"], 
  operator: "AND",
  priority: 1
}]->(process);
```

## Variable Resolution System

The variable resolution system is a core mechanism for passing data between workflow steps. It uses a special syntax to reference values from previous steps.

### Variable Reference Syntax

## Core Components

### 1. Database Interface

The `database.py` module provides unified Neo4j connectivity with connection pooling:

```python
from neo4j import GraphDatabase
import os

class Neo4jDriver:
    def __init__(self, uri, username, password, max_connection_lifetime=3600):
        self.driver = GraphDatabase.driver(
            uri, 
            auth=(username, password),
            max_connection_lifetime=max_connection_lifetime
        )
        
    def get_session(self, database=None):
        return self.driver.session(database=database)
        
    def close(self):
        self.driver.close()

# Singleton pattern for Neo4j driver
_driver = None

def get_neo4j_driver():
    global _driver
    if _driver is None:
        uri = os.environ.get("NEO4J_URI")
        username = os.environ.get("NEO4J_USERNAME")
        password = os.environ.get("NEO4J_PASSWORD")
        _driver = Neo4jDriver(uri, username, password)
    return _driver
```

### 2. Session Management

The `session_manager.py` module handles session lifecycle and state updates:

```python
import json
import uuid
from .database import get_neo4j_driver

class SessionManager:
    def __init__(self, neo4j_driver=None):
        self.driver = neo4j_driver or get_neo4j_driver()
        
    def create_session(self, workflow_id="default"):
        """Create a new workflow session with initial state"""
        session_id = str(uuid.uuid4())
        
        # Initialize the session state
        initial_state = {
            "id": session_id,
            "workflow": {
                "root": {
                    "status": "active",
                    "error": ""
                }
            },
            "data": {
                "outputs": {},
                "messages": []
            }
        }
        
        # Create session node in Neo4j
        with self.driver.get_session() as session:
            session.run(
                """
                CREATE (s:SESSION {
                    id: $id, 
                    state: $state, 
                    created_at: datetime()
                })
                """,
                id=session_id,
                state=json.dumps(initial_state)
            )
            
        return session_id
        
    def get_session_state(self, session_id):
        """Get current session state"""
        with self.driver.get_session() as session:
            result = session.run(
                """
                MATCH (s:SESSION {id: $id})
                RETURN s.state as state
                """,
                id=session_id
            )
            record = result.single()
            if record:
                return json.loads(record["state"])
            return None
            
    def update_session_state(self, session_id, update_func):
        """
        Update session state with optimistic concurrency control
        
        Args:
            session_id: The session ID
            update_func: Function that takes current state and returns updated state
        
        Returns:
            Boolean indicating success
        """
        with self.driver.get_session() as neo_session:
            tx = neo_session.begin_transaction()
            try:
                # Get current state
                result = tx.run(
                    """
                    MATCH (s:SESSION {id: $id})
                    RETURN s.state as state
                    """,
                    id=session_id
                )
                record = result.single()
                if not record:
                    tx.rollback()
                    return False
                    
                # Apply update function
                current_state = json.loads(record["state"])
                updated_state = update_func(current_state)
                
                # Write updated state
                tx.run(
                    """
                    MATCH (s:SESSION {id: $id})
                    SET s.state = $state
                    """,
                    id=session_id,
                    state=json.dumps(updated_state)
                )
                
                tx.commit()
                return True
            except Exception as e:
                tx.rollback()
                raise e

# Singleton pattern for SessionManager
_session_manager = None

def get_session_manager():
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
```

### 3. Variable Resolution

The variable resolution system is a critical component for data flow between steps:

```python
def resolve_variable(var_reference, session_state):
    """
    Resolve a variable reference from session state
    
    Args:
        var_reference: String in format '@{SESSION_ID}.step_id.field'
        session_state: Current session state object
    
    Returns:
        Resolved value or None if not found
    """
    if not isinstance(var_reference, str) or not var_reference.startswith('@{'):
        # Not a variable reference, return as-is
        return var_reference
        
    # Extract parts: @{SESSION_ID}.step_id.field
    try:
        var_path = var_reference[2:].strip('}').split('.')
        if len(var_path) < 2:
            return None
            
        # Get step output from session state
        step_id = var_path[1]
        
        if step_id not in session_state["data"]["outputs"]:
            return None
            
        value = session_state["data"]["outputs"][step_id]
        
        # Navigate to nested field if specified
        if len(var_path) > 2:
            for field in var_path[2:]:
                if isinstance(value, dict) and field in value:
                    value = value[field]
                else:
                    return None
                    
        return value
    except Exception:
        return None

def resolve_inputs(input_spec, session_state):
    """
    Resolve all variables in an input specification
    
    Args:
        input_spec: Dictionary of input parameters
        session_state: Current session state
        
    Returns:
        Dictionary with resolved values or None if any required value couldn't be resolved
    """
    resolved = {}
    
    for key, value in input_spec.items():
        resolved_value = resolve_variable(value, session_state)
        
        # Check if resolution failed for a required input
        if resolved_value is None and isinstance(value, str) and value.startswith('@{'):
            return None
            
        resolved[key] = resolved_value
        
    return resolved
```

### 4. Workflow Engine

The `graph_engine.py` module implements the core workflow execution logic:

```python
from .session_manager import get_session_manager
from .utility_registry import get_utility_registry

class GraphWorkflowEngine:
    def __init__(self, session_manager=None, utility_registry=None):
        self.session_manager = session_manager or get_session_manager()
        self.utility_registry = utility_registry or get_utility_registry()
        
    def process_workflow(self, session_id):
        """
        Process workflow steps for a session
        
        Returns:
            Workflow status: 'completed', 'awaiting_input', or 'active'
        """
        # Get current session state
        state = self.session_manager.get_session_state(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")
            
        # Find active steps
        active_steps = self._get_active_steps(state)
        if not active_steps:
            return "completed"
            
        # Process each active step
        for step_id in active_steps:
            result = self._process_step(session_id, step_id, state)
            
            # If step is waiting for input, return immediately
            if result == "awaiting_input":
                return "awaiting_input"
                
        # Update paths after processing steps
        self._update_execution_paths(session_id)
        
        # Check if there are still active steps
        state = self.session_manager.get_session_state(session_id)
        active_steps = self._get_active_steps(state)
        
        if active_steps:
            # Continue processing if there are more active steps
            return self.process_workflow(session_id)
        else:
            return "completed"
    
    def _get_active_steps(self, state):
        """Find steps with 'active' status in workflow state"""
        active_steps = []
        for step_id, step_info in state["workflow"].items():
            if step_info["status"] == "active":
                active_steps.append(step_id)
        return active_steps
    
    def _process_step(self, session_id, step_id, state):
        """Process a single workflow step"""
        # Get step details from Neo4j
        step_details = self._get_step_details(step_id)
        if not step_details:
            # Handle missing step
            self._mark_step_error(session_id, step_id, "Step not found")
            return "error"
            
        # Resolve input variables
        from .resolve_variable import resolve_inputs
        resolved_inputs = resolve_inputs(step_details["input"], state)
        
        if resolved_inputs is None:
            # Not all inputs could be resolved, mark as pending
            self._update_step_status(session_id, step_id, "pending")
            return "pending"
            
        # Get utility function
        function_name = step_details["function"]
        function_func = self.utility_registry.get_utility(function_name)
        
        if not function_func:
            # Handle missing utility
            self._mark_step_error(session_id, step_id, f"Utility not found: {function_name}")
            return "error"
            
        # Special handling for request utility
        if function_name == "utils.request":
            self._update_step_status(session_id, step_id, "awaiting_input")
            return "awaiting_input"
            
        # Execute utility function
        try:
            result = function_func(**resolved_inputs)
            
            # Store result in session
            def update_state(current_state):
                current_state["data"]["outputs"][step_id] = result
                current_state["workflow"][step_id]["status"] = "complete"
                return current_state
                
            self.session_manager.update_session_state(session_id, update_state)
            return "complete"
            
        except Exception as e:
            # Handle execution error
            self._mark_step_error(session_id, step_id, str(e))
            return "error"
    
    def _get_step_details(self, step_id):
        """Get step details from Neo4j"""
        with self.session_manager.driver.get_session() as session:
            result = session.run(
                """
                MATCH (s:STEP {id: $id})
                RETURN s.function as function, s.input as input
                """,
                id=step_id
            )
            record = result.single()
            if record:
                return {
                    "function": record["function"],
                    "input": json.loads(record["input"]) if record["input"] else {}
                }
            return None
    
    def _update_execution_paths(self, session_id):
        """Identify and activate next steps in the workflow"""
        # Get current state
        state = self.session_manager.get_session_state(session_id)
        if not state:
            return
            
        # Find completed steps
        completed_steps = []
        for step_id, info in state["workflow"].items():
            if info["status"] == "complete":
                completed_steps.append(step_id)
                
        if not completed_steps:
            return
            
        # Find next steps from completed ones
        next_steps = []
        for step_id in completed_steps:
            outgoing = self._get_outgoing_relationships(step_id)
            
            for rel in outgoing:
                # Evaluate conditions if present
                conditions_met = True
                if rel["conditions"]:
                    from .resolve_variable import resolve_variable
                    
                    results = []
                    for condition in rel["conditions"]:
                        value = resolve_variable(condition, state)
                        results.append(bool(value))
                        
                    # Apply operator logic
                    if rel["operator"] == "OR":
                        conditions_met = any(results)
                    else:  # Default to AND
                        conditions_met = all(results)
                        
                if conditions_met:
                    next_steps.append(rel["target_step"])
        
        # Update session with new active steps
        if next_steps:
            def update_state(current_state):
                for step_id in next_steps:
                    # Only add if not already in workflow
                    if step_id not in current_state["workflow"]:
                        current_state["workflow"][step_id] = {
                            "status": "active",
                            "error": ""
                        }
                return current_state
                
            self.session_manager.update_session_state(session_id, update_state)
    
    def _get_outgoing_relationships(self, step_id):
        """Get outgoing NEXT relationships from a step"""
        with self.session_manager.driver.get_session() as session:
            result = session.run(
                """
                MATCH (s:STEP {id: $id})-[r:NEXT]->(target:STEP)
                RETURN target.id as target_id, r.condition as conditions, r.operator as operator
                """,
                id=step_id
            )
            relationships = []
            for record in result:
                relationships.append({
                    "target_step": record["target_id"],
                    "conditions": record["conditions"] or [],
                    "operator": record["operator"] or "AND"
                })
            return relationships
    
    def _update_step_status(self, session_id, step_id, status):
        """Update a step's status in session state"""
        def update_state(current_state):
            if step_id in current_state["workflow"]:
                current_state["workflow"][step_id]["status"] = status
            return current_state
            
        self.session_manager.update_session_state(session_id, update_state)
    
    def _mark_step_error(self, session_id, step_id, error_message):
        """Mark a step as having an error"""
        def update_state(current_state):
            if step_id in current_state["workflow"]:
                current_state["workflow"][step_id]["status"] = "error"
                current_state["workflow"][step_id]["error"] = error_message
            return current_state
            
        self.session_manager.update_session_state(session_id, update_state)
    
    def handle_user_input(self, session_id, user_input):
        """
        Handle user input for a workflow that's awaiting input
        
        Args:
            session_id: Session ID
            user_input: User's input data
            
        Returns:
            Updated workflow status
        """
        # Get current state
        state = self.session_manager.get_session_state(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")
            
        # Find step awaiting input
        awaiting_step = None
        for step_id, info in state["workflow"].items():
            if info["status"] == "awaiting_input":
                awaiting_step = step_id
                break
                
        if not awaiting_step:
            raise ValueError("No step is awaiting input")
            
        # Store input and mark step as complete
        def update_state(current_state):
            # Store result
            current_state["data"]["outputs"][awaiting_step] = user_input
            current_state["workflow"][awaiting_step]["status"] = "complete"
            
            # Add to message history if text input
            if isinstance(user_input, str):
                current_state["data"]["messages"].append({
                    "role": "user",
                    "content": user_input
                })
                
            return current_state
            
        self.session_manager.update_session_state(session_id, update_state)
        
        # Resume workflow processing
        return self.process_workflow(session_id)

# Singleton pattern
_engine = None

def get_graph_workflow_engine():
    global _engine
    if _engine is None:
        _engine = GraphWorkflowEngine()
    return _engine
```

### 5. Utility Registry

The `utility_registry.py` module manages available utility functions:

```python
class UtilityRegistry:
    def __init__(self):
        self.utilities = {}
        
    def register_utility(self, path, function):
        """Register a utility function"""
        self.utilities[path] = function
        
    def get_utility(self, path):
        """Get utility function by path"""
        return self.utilities.get(path)
        
    def register_module(self, module_path, module_obj):
        """Register all functions in a module with prefix"""
        for name in dir(module_obj):
            item = getattr(module_obj, name)
            if callable(item) and not name.startswith('_'):
                full_path = f"{module_path}.{name}"
                self.register_utility(full_path, item)

# Singleton pattern
_registry = None

def get_utility_registry():
    global _registry
    if _registry is None:
        _registry = UtilityRegistry()
        
        # Register core utilities
        import utils.generate
        import utils.request
        import utils.reply
        
        _registry.register_module("utils.generate", utils.generate)
        _registry.register_module("utils.request", utils.request)
        _registry.register_module("utils.reply", utils.reply)
        
    return _registry
```

## Core Utilities

Three essential utility functions form the foundation of most workflows:

### 1. Generate (LLM Text Generation)

```python
def generate(prompt, model="gpt-3.5-turbo", max_tokens=1000, temperature=0.7, **kwargs):
    """
    Generate text using an LLM
    
    Args:
        prompt: Text prompt
        model: Model identifier
        max_tokens: Maximum response length
        temperature: Randomness (0-1)
        **kwargs: Additional model parameters
        
    Returns:
        Generated text
    """
    # Implementation depends on LLM service
    try:
        # Example implementation with OpenAI
        import openai
        
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
        
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Text generation failed: {str(e)}")
```

### 2. Request (User Input)

```python
def request(prompt=None, options=None):
    """
    Request input from the user
    
    Args:
        prompt: Text prompt to display
        options: List of option choices
        
    Returns:
        Signal object indicating workflow should pause
    """
    # This function signals the engine to pause and await input
    return {
        "waiting_for_input": True,
        "prompt": prompt,
        "options": options
    }
```

### 3. Reply (User Response)

```python
def reply(message, end_conversation=False):
    """
    Send a response to the user
    
    Args:
        message: Text response
        end_conversation: Whether to end conversation
        
    Returns:
        Formatted response object
    """
    return {
        "message": message,
        "end_conversation": end_conversation
    }
```

## Workflow Examples

### Example 1: Simple Conversation Flow

```cypher
// Root step - initial user input
CREATE (root:STEP {
  id: "root",
  function: "utils.request",
  input: "{\"prompt\": \"How can I help you today?\"}"
})

// Generate answer based on user query
CREATE (generate:STEP {
  id: "generate-answer",
  function: "utils.generate",
  input: "{\"prompt\": \"User query: '@{SESSION_ID}.root'. Provide a helpful response.\"}"
})

// Reply to user with generated answer
CREATE (reply:STEP {
  id: "send-response",
  function: "utils.reply",
  input: "{\"message\": \"@{SESSION_ID}.generate-answer\"}"
})

// Check if followup needed
CREATE (check:STEP {
  id: "check-followup",
  function: "utils.generate",
  input: "{\"prompt\": \"Should I ask a follow-up question? Answer 'yes' or 'no'.\", \"temperature\": 0.2}"
})

// Followup question if needed
CREATE (followup:STEP {
  id: "followup-question",
  function: "utils.request",
  input: "{\"prompt\": \"Is there anything else you'd like to know?\"}"
})

// End conversation
CREATE (end:STEP {
  id: "end-conversation",
  function: "utils.reply",
  input: "{\"message\": \"Thank you for chatting!\", \"end_conversation\": true}"
})

// Create flow relationships
CREATE (root)-[:NEXT]->(generate)
CREATE (generate)-[:NEXT]->(reply)
CREATE (reply)-[:NEXT]->(check)
CREATE (check)-[:NEXT {conditions: ["@{SESSION_ID}.check-followup"], operator: "AND"}]->(followup)
CREATE (check)-[:NEXT {conditions: ["@{SESSION_ID}.check-followup == no"], operator: "AND"}]->(end)
CREATE (followup)-[:NEXT]->(generate)
```

### Example 2: Multi-Path Workflow

```cypher
// Root step - initial user input
CREATE (root:STEP {
  id: "root",
  function: "utils.request",
  input: "{\"prompt\": \"What type of task do you need help with?\"}"
})

// Categorize user input
CREATE (categorize:STEP {
  id: "categorize",
  function: "utils.generate",
  input: "{\"prompt\": \"@{SESSION_ID}.root\"}"
})

// Answer based on categorization
CREATE (answer:STEP {
  id: "answer",
  function: "utils.generate",
  input: "{\"prompt\": \"@{SESSION_ID}.categorize\"}"
})

// Task-specific answer
CREATE (task:STEP {
  id: "task-answer",
  function: "utils.generate",
  input: "{\"prompt\": \"@{SESSION_ID}.categorize\"}"
})

// Chat-specific answer
CREATE (chat:STEP {
  id: "chat-answer",
  function: "utils.generate",
  input: "{\"prompt\": \"@{SESSION_ID}.categorize\"}"
})

// Conditional paths based on categorization
CREATE (categorize)-[:NEXT {conditions: ["@{SESSION_ID}.categorize-input == question"], operator: "AND"}]->(answer)
CREATE (categorize)-[:NEXT {conditions: ["@{SESSION_ID}.categorize-input == task"], operator: "AND"}]->(task)
CREATE (categorize)-[:NEXT {conditions: ["@{SESSION_ID}.categorize-input == chat"], operator: "AND"}]->(chat)
```

### Creating a Workflow

1. **Define Steps**: Create STEP nodes with unique IDs and function references
2. **Define Inputs**: Specify inputs for each step, using variable references when needed
3. **Connect Steps**: Create NEXT relationships, with conditions if necessary
4. **Set Root Step**: Ensure there's a step with ID "root" for workflow entry