# Migrating from API-based Nested Sessions to Code-based Nested Sessions

This guide explains how to migrate your workflow steps from using the API utility with nested servers to using the code utility with direct session management.

## Why Migrate?

The old approach of using the API utility for nested sessions has several limitations:
- Requires running a separate server instance on a different port for each nested session level
- Limited to just one level of nesting (port 5000 -> port 5001)
- Poor scalability for complex workflows with multiple nested sessions

The new code-based approach provides:
- Direct access to core session management
- No additional servers needed
- Unlimited nesting levels
- Better performance
- Simplified workflow configuration

## Migration Steps

### Step 1: Identify API-based Nested Session Steps

Look for workflow steps that use the `api` function to:
1. Create a session
2. Send a message to a session
3. Get session messages

These typically have configurations like:

```json
{
  "function": "utils.api.api",
  "method": "POST",
  "url": "http://localhost:5000/api/session",
  "headers": {
    "Content-Type": "application/json"
  },
  "json_data": {
    "workflow_id": "some_workflow",
    "initial_data": {}
  }
}
```

Or:

```json
{
  "function": "utils.api.api",
  "method": "POST",
  "url": "http://localhost:5000/api/session/@{SESSION_ID}.create_nested.session_id/message",
  "headers": {
    "Content-Type": "application/json"
  },
  "json_data": {
    "message": "Hello from parent workflow"
  }
}
```

### Step 2: Replace with Code-based Steps

#### For Session Creation

Replace:
```json
{
  "function": "utils.api.api",
  "method": "POST",
  "url": "http://localhost:5000/api/session",
  "headers": {
    "Content-Type": "application/json"
  },
  "json_data": {
    "workflow_id": "some_workflow",
    "initial_data": {
      "key": "value"
    }
  }
}
```

With:
```json
{
  "function": "utils.code.code",
  "file_path": "create_session.py",
  "variables": {
    "workflow_id": "some_workflow",
    "initial_data": {
      "key": "value"
    }
  }
}
```

#### For Sending Messages

Replace:
```json
{
  "function": "utils.api.api",
  "method": "POST",
  "url": "http://localhost:5000/api/session/@{SESSION_ID}.create_nested.session_id/message",
  "headers": {
    "Content-Type": "application/json"
  },
  "json_data": {
    "message": "Hello from parent workflow"
  }
}
```

With:
```json
{
  "function": "utils.code.code",
  "file_path": "send_session_message.py",
  "variables": {
    "session_id": "@{SESSION_ID}.create_nested.session_id",
    "message": "Hello from parent workflow"
  }
}
```

#### For Getting Session Messages

Replace:
```json
{
  "function": "utils.api.api",
  "method": "GET",
  "url": "http://localhost:5000/api/session/@{SESSION_ID}.create_nested.session_id"
}
```

With:
```json
{
  "function": "utils.code.code",
  "file_path": "get_session_messages.py",
  "variables": {
    "session_id": "@{SESSION_ID}.create_nested.session_id"
  }
}
```

### Step 3: Update Variable References

#### Old API Response Structure

The old API-based nested sessions returned data in this structure:
```json
{
  "status_code": 200,
  "response": {
    "session_id": "abc123",
    "messages": [],
    "status": "active"
  },
  "headers": {}
}
```

So you'd reference values with:
- `@{SESSION_ID}.create_nested.response.session_id`
- `@{SESSION_ID}.send_message.response.messages[0].content`

#### New Code-based Response Structure

The new code-based tools return a cleaner structure:
```json
{
  "session_id": "abc123",
  "workflow_id": "default",
  "initial_data": {},
  "success": true
}
```

So you'll need to update references to:
- `@{SESSION_ID}.create_nested.session_id`
- `@{SESSION_ID}.get_messages.messages[0].content`

## Available Scripts

### create_session.py

Creates a new workflow session.

**Variables:**
- `workflow_id`: ID of the workflow to run (defaults to "default")
- `initial_data`: (Optional) Dictionary of initial data for the session

**Returns:**
- `session_id`: ID of the created session
- `workflow_id`: ID of the workflow
- `initial_data`: Initial data provided to the session

### send_session_message.py

Sends a message to an existing workflow session.

**Variables:**
- `session_id`: ID of the session to send a message to
- `message`: Content of the message to send

**Returns:**
- `success`: Whether the operation was successful
- `session_id`: ID of the session
- `status`: Current status of the workflow
- `responses`: Array of assistant responses generated after sending the message
- `error`: Error message if operation failed

### get_session_messages.py

Retrieves messages from an existing workflow session.

**Variables:**
- `session_id`: ID of the session to get messages from
- `limit`: (Optional) Maximum number of messages to return
- `after_timestamp`: (Optional) Only return messages after this timestamp

**Returns:**
- `success`: Whether the operation was successful
- `session_id`: ID of the session
- `messages`: Array of messages in the session
- `count`: Number of messages returned
- `error`: Error message if operation failed

## Example Workflow

Here's an example workflow that uses these new code-based tools:

```json
{
  "steps": {
    "create_nested": {
      "function": "utils.code.code",
      "file_path": "create_session.py",
      "variables": {
        "workflow_id": "chatbot",
        "initial_data": {
          "parent_session_id": "@{SESSION_ID}"
        }
      },
      "next": ["send_initial_message"]
    },
    "send_initial_message": {
      "function": "utils.code.code",
      "file_path": "send_session_message.py",
      "variables": {
        "session_id": "@{SESSION_ID}.create_nested.session_id",
        "message": "Hello, I'm from the parent workflow!"
      },
      "next": ["get_responses"]
    },
    "get_responses": {
      "function": "utils.code.code",
      "file_path": "get_session_messages.py",
      "variables": {
        "session_id": "@{SESSION_ID}.create_nested.session_id"
      },
      "next": ["process_responses"]
    },
    "process_responses": {
      "function": "utils.tools.process_responses",
      "content": "@{SESSION_ID}.get_responses.messages",
      "next": []
    }
  }
}
```

## Testing

A test script is available at `tests/test_nested_session_code.py` that demonstrates how to use these new tools programmatically.

Run the test with:
```
python -m unittest tests/test_nested_session_code.py
``` 