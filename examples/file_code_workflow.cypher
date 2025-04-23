// Example workflow demonstrating the code.py utility with file loading feature
// Note: Run this script manually in your Neo4j instance

// 1. Create the root step that asks for data to process
CREATE (root:STEP {
  id: "code_root",
  name: "Request Data",
  description: "Request input data for processing",
  function: "utils.request.request",
  input: '{"prompt": "Please provide some text to transform:", "options": null}'
})

// 2. Create a first response step
CREATE (respond:STEP {
  id: "generate_generic",
  name: "Generate Response",
  description: "Generate initial response",
  function: "utils.generate.generate",
  input: '{"user": "@{SESSION_ID}.code_root.response", "system": "You are a helpful assistant."}'
})

// 3. Create a step to send the initial response
CREATE (send_response:STEP {
  id: "api_generic_reply",
  name: "Send Response",
  description: "Send the initial response",
  function: "utils.api.api",
  input: '{"method": "POST", "url": "https://discord.com/api/v10/channels/@{SESSION_ID}.channel.id/messages", "headers": {"Authorization": "Bot $DISCORD_BOT_TOKEN", "Content-Type": "application/json"}, "json_data": {"content": "@{SESSION_ID}.generate_generic.response"}}'
})

// 4. Create a transformation step using file loading
CREATE (transform:STEP {
  id: "transform_text",
  name: "Transform Text",
  description: "Transforms text to uppercase using code from file",
  function: "utils.code.code",
  input: '{"file_path": "text_analysis.py"}'
})

// 5. Create a step to send the transformed response
CREATE (send_transformed:STEP {
  id: "api_generic_reply2",
  name: "Send Transformed Response",
  description: "Send the transformed uppercase response",
  function: "utils.api.api",
  input: '{"method": "POST", "url": "https://discord.com/api/v10/channels/@{SESSION_ID}.channel.id/messages", "headers": {"Authorization": "Bot $DISCORD_BOT_TOKEN", "Content-Type": "application/json"}, "json_data": {"content": "**Transformed Text**\n```\nOriginal: @{SESSION_ID}.transform_text.result.original\nUppercase: @{SESSION_ID}.transform_text.result.transformed\nLength: @{SESSION_ID}.transform_text.result.length characters\nWord Count: @{SESSION_ID}.transform_text.result.word_count\n```"}}'
})

// Create the workflow connections
CREATE 
  (root)-[:NEXT]->(generate_generic),
  (generate_generic)-[:NEXT]->(send_response),
  (send_response)-[:NEXT]->(transform_text),
  (transform_text)-[:NEXT]->(send_transformed)

// Log completion
RETURN "File-based code workflow created successfully" as message 