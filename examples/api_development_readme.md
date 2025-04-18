# LUNA API Development Guide

This guide covers how to build applications that use the LUNA graph-based workflow engine API. The workflow engine exposes a RESTful API that allows you to create sessions, send messages, and retrieve workflow state.

## API Endpoints

The API consists of the following main endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/session` | POST | Create a new workflow session |
| `/api/session/<session_id>/message` | POST | Send a message to a workflow |
| `/api/session/<session_id>` | GET | Get the current state of a session |
| `/api/health` | GET | Health check endpoint |

## Creating a New Session

To create a new workflow session:

```http
POST /api/session
Content-Type: application/json

{
  "workflow_id": "default",
  "initial_data": {
    "user_info": {
      "name": "John Doe",
      "preferences": ["movies", "books"]
    },
    "context": "Customer support inquiry"
  }
}
```

The `initial_data` parameter is optional and allows you to pre-populate the session state with custom data that your workflow steps can access. This data will be accessible in two ways:

1. **Direct access**: Each top-level key in initial_data becomes a "virtual step output" in the session state, accessible via:
   ```
   @{SESSION_ID}.user_info.name
   @{SESSION_ID}.context
   ```

2. **Through "initial" step**: The entire initial_data object is also added as an output of an "initial" step:
   ```
   @{SESSION_ID}.initial.user_info.name
   @{SESSION_ID}.initial.context
   ```

This allows your workflow steps to reference these variables just like any other step output.

Response:

```json
{
  "session_id": "unique-session-id",
  "status": "active|awaiting_input|complete|error",
  "messages": [
    {
      "role": "assistant",
      "content": "Initial message or prompt",
      "timestamp": 1234567890
    }
  ],
  "awaiting_input": null
}
```

The `awaiting_input` field will be non-null if the workflow is waiting for user input, and may contain options or other UI-specific data.

## Sending Messages to a Workflow

To send a message to an active workflow:

```http
POST /api/session/<session_id>/message
Content-Type: application/json

{
  "message": "Your message here"
}
```

Response:

```json
{
  "status": "active|awaiting_input|complete|error",
  "messages": [
    {
      "role": "assistant",
      "content": "Initial prompt",
      "timestamp": 1234567890
    },
    {
      "role": "user",
      "content": "Your message here",
      "timestamp": 1234567891
    },
    {
      "role": "assistant",
      "content": "Response to your message",
      "timestamp": 1234567892
    }
  ],
  "awaiting_input": null
}
```

## Retrieving Session State

To get the current state of a session:

```http
GET /api/session/<session_id>
```

The response format is the same as the other endpoints.

## Example: Simple Command-Line Client

Here's an example of a simple command-line client in Python:

```python
import requests
import json

class LunaClient:
    def __init__(self, base_url="http://localhost:5000/api"):
        self.base_url = base_url
        self.session_id = None
        
    def create_session(self, workflow_id="default", initial_data=None):
        """Create a new workflow session"""
        payload = {"workflow_id": workflow_id}
        
        # Add initial data if provided
        if initial_data:
            payload["initial_data"] = initial_data
            
        response = requests.post(
            f"{self.base_url}/session", 
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        self.session_id = data['session_id']
        return data
        
    def send_message(self, message):
        """Send a message to the workflow"""
        if not self.session_id:
            raise ValueError("No active session. Call create_session first.")
            
        response = requests.post(
            f"{self.base_url}/session/{self.session_id}/message", 
            json={"message": message}
        )
        response.raise_for_status()
        return response.json()
        
    def get_session(self):
        """Get the current session state"""
        if not self.session_id:
            raise ValueError("No active session. Call create_session first.")
            
        response = requests.get(f"{self.base_url}/session/{self.session_id}")
        response.raise_for_status()
        return response.json()
        
    def run_conversation(self, initial_data=None):
        """Interactive conversation loop"""
        try:
            session_data = self.create_session(initial_data=initial_data)
            print("Session created.")
            
            # Print initial messages
            for msg in session_data.get('messages', []):
                print(f"{msg['role'].upper()}: {msg['content']}")
            
            # Main conversation loop
            while True:
                # Check if we're waiting for input
                if session_data.get('status') == 'awaiting_input':
                    user_input = input("> ")
                    session_data = self.send_message(user_input)
                    
                    # Print all new messages
                    for msg in session_data.get('messages', []):
                        if msg['role'] == 'assistant':
                            print(f"ASSISTANT: {msg['content']}")
                
                elif session_data.get('status') == 'complete':
                    print("Conversation completed.")
                    break
                    
                elif session_data.get('status') == 'error':
                    print("Error occurred in the workflow.")
                    break
                    
                else:
                    # Poll for updates if not awaiting input
                    session_data = self.get_session()
                    
        except KeyboardInterrupt:
            print("\nConversation ended by user.")
        except Exception as e:
            print(f"Error: {str(e)}")

# Example usage
if __name__ == "__main__":
    client = LunaClient()
    
    # Example with initial data
    initial_data = {
        "user_info": {
            "name": "John Doe",
            "preferences": ["tech", "science"]
        },
        "context": "Technical support inquiry"
    }
    
    client.run_conversation(initial_data=initial_data)
```

## Example: Integration with a Web Application

Here's how you might integrate with a React application:

```javascript
// api.js
class LunaAPI {
  constructor(baseUrl = 'http://localhost:5000/api') {
    this.baseUrl = baseUrl;
    this.sessionId = null;
  }

  async createSession(workflowId = 'default', initialData = null) {
    const payload = { workflow_id: workflowId };
    
    // Add initial data if provided
    if (initialData) {
      payload.initial_data = initialData;
    }
    
    const response = await fetch(`${this.baseUrl}/session`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });
    
    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.statusText}`);
    }
    
    const data = await response.json();
    this.sessionId = data.session_id;
    return data;
  }

  async sendMessage(message) {
    if (!this.sessionId) {
      throw new Error('No active session. Call createSession first.');
    }
    
    const response = await fetch(`${this.baseUrl}/session/${this.sessionId}/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ message })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to send message: ${response.statusText}`);
    }
    
    return await response.json();
  }

  async getSession() {
    if (!this.sessionId) {
      throw new Error('No active session. Call createSession first.');
    }
    
    const response = await fetch(`${this.baseUrl}/session/${this.sessionId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to get session: ${response.statusText}`);
    }
    
    return await response.json();
  }
}

export default new LunaAPI();
```

Usage in a React component:

```jsx
import React, { useState, useEffect } from 'react';
import LunaAPI from './api';

function ChatComponent() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [status, setStatus] = useState('initializing');
  const [awaitingInput, setAwaitingInput] = useState(null);

  // Initialize session on component mount
  useEffect(() => {
    async function initSession() {
      try {
        // Example of providing initial data
        const initialData = {
          user_info: {
            name: 'Jane Smith',
            preferences: ['travel', 'food']
          },
          context: 'Travel planning assistance'
        };
        
        const sessionData = await LunaAPI.createSession('default', initialData);
        setMessages(sessionData.messages || []);
        setStatus(sessionData.status);
        setAwaitingInput(sessionData.awaiting_input);
      } catch (error) {
        console.error('Failed to initialize session:', error);
      }
    }
    
    initSession();
  }, []);

  // Send message handler
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    
    try {
      const response = await LunaAPI.sendMessage(input);
      setMessages(response.messages || []);
      setStatus(response.status);
      setAwaitingInput(response.awaiting_input);
      setInput('');
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            {msg.content}
          </div>
        ))}
        {status === 'error' && (
          <div className="error-message">
            An error occurred. Please try again.
          </div>
        )}
      </div>
      
      <form onSubmit={handleSendMessage}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={status !== 'awaiting_input'}
          placeholder={status === 'awaiting_input' ? 'Type your message...' : 'Waiting...'}
        />
        <button type="submit" disabled={status !== 'awaiting_input'}>Send</button>
      </form>
    </div>
  );
}

export default ChatComponent;
```

## Best Practices

### 1. Handle Session Management Properly

Store the session ID securely. For web applications, you might store it in:
- localStorage for single-user applications
- A server-side session for authenticated users
- A database for persistence across sessions

### 2. Implement Error Handling

Always handle potential errors from the API:
- Network errors
- Server errors (500 responses)
- Application errors (returned in the error field)

### 3. Manage Workflow State

The status field indicates the current state of the workflow:
- `active`: The workflow is processing
- `awaiting_input`: The workflow is waiting for user input
- `complete`: The workflow has completed
- `error`: An error occurred

### 4. Handling Messages Array

The messages array contains the conversation history. Key considerations:
- Messages are ordered by timestamp
- Handle both user and assistant messages appropriately
- Check for duplicate messages when polling

### 5. Polling Strategy

If your application needs to poll for updates:
- Use a reasonable interval (e.g., 1-3 seconds)
- Implement exponential backoff if no changes are detected
- Stop polling when the status is 'complete' or 'error'

## Advanced Usage

### Custom Workflows

To use custom workflows, you'll need to define them in Neo4j. The workflow_id parameter in the create_session request determines which workflow to use.

### Multiple Simultaneous Sessions

Your application can manage multiple workflow sessions simultaneously by tracking multiple session IDs.

### Timeouts and Session Expiry

Be aware that workflow sessions may expire after a period of inactivity. Your application should handle session expiry gracefully.

## Error Handling

Common error scenarios to handle:

| Status Code | Description | Handling Strategy |
|-------------|-------------|-------------------|
| 404 | Session not found | Create a new session |
| 500 | Server error | Retry with exponential backoff |
| 200 with error in JSON | Application error | Display error to user, possibly restart |

## Security Considerations

- The API does not currently implement authentication
- For production use, consider adding API keys or other authentication mechanisms
- Use HTTPS in production environments

## Example Curl Commands

For testing with curl:

```bash
# Create a session
curl -X POST http://localhost:5000/api/session \
  -H "Content-Type: application/json" \
  -d '{"workflow_id": "default"}'

# Create a session with initial data
curl -X POST http://localhost:5000/api/session \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "default",
    "initial_data": {
      "user_info": {"name": "John Doe"},
      "context": "Product inquiry"
    }
  }'

# Send a message (replace SESSION_ID with your actual session ID)
curl -X POST http://localhost:5000/api/session/SESSION_ID/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Can you tell me about MoonDAO?"}'

# Send a message with special characters (using double quotes for JSON payload)
curl -X POST http://localhost:5000/api/session/SESSION_ID/message \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Here's an example with an apostrophe\"}"

# Alternative approach for complex messages - create a message.json file:
# {"message": "Here's a message with special characters: ', \", etc."}
curl -X POST http://localhost:5000/api/session/SESSION_ID/message \
  -H "Content-Type: application/json" \
  -d @message.json

# Get session state
curl -X GET http://localhost:5000/api/session/SESSION_ID
```

> **Note:** When testing with curl, be careful with special characters in JSON payloads. Single quotes within single-quoted strings can cause shell parsing errors. The approaches shown above (using double quotes with escaped quotes or using a JSON file) help avoid these issues.

# Working with the API in the terminal:
