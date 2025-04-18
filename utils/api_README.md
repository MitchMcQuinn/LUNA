# API Utility Module

The API utility module enables workflows to interact with external APIs, allowing the system to fetch data from external services and incorporate it into conversations.

## Features

- Make HTTP requests to external APIs (GET, POST, PUT, DELETE)
- Handle authentication via headers or auth parameters
- Process environment variables in header values (for API keys)
- Full error handling with detailed error information
- Simple response format with the entire response as a single property

## Usage

### Basic Request

```python
# Step configuration to make a simple GET request
{
  "id": "weather-api",
  "function": "utils.api.api",
  "input": '{"method": "GET", "url": "https://api.example.com/weather"}'
}
```

### Request with Variable Substitution

```python
# Incorporate variables from previous steps
{
  "id": "fetch-user",
  "function": "utils.api.api",
  "input": '{"method": "GET", "url": "https://api.example.com/users/@{SESSION_ID}.get_username.response"}'
}
```

### Request with Authentication

```python
# Using an API key from environment variable in headers
{
  "id": "api-with-auth",
  "function": "utils.api.api",
  "input": '{"method": "GET", "url": "https://api.service.com/data", "headers": {"Authorization": "Bearer $API_KEY"}}'
}
```

### POST Request with JSON Body

```python
# Sending data to an API
{
  "id": "create-resource",
  "function": "utils.api.api",
  "input": '{"method": "POST", "url": "https://api.example.com/resources", "json_data": {"name": "@{SESSION_ID}.get_name.response", "type": "user"}}'
}
```

## Response Format

The API utility returns a consistent response object:

```json
{
  "status_code": 200,            // HTTP status code
  "response": "...",             // Full response body as text
  "headers": { ... },            // Response headers as dictionary
  "error": null                  // Error message if request failed (null on success)
}
```

## Processing API Responses

The recommended pattern is to pass API responses to an LLM step for intelligent parsing:

```python
# Example of processing an API response with an LLM
{
  "id": "process-weather",
  "function": "utils.generate.generate",
  "input": '{"system": "...", "user": "Parse this weather data: @{SESSION_ID}.fetch-weather.response"}'
}
```

## Convenience Methods

The API utility also provides convenience methods for common HTTP methods:

- `utils.api.get(url, **kwargs)`
- `utils.api.post(url, **kwargs)`
- `utils.api.put(url, **kwargs)`
- `utils.api.delete(url, **kwargs)`

These methods call the main `api` function with the appropriate HTTP method. 