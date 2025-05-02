// Create a basic workflow for Discord bot integration
// Note: You should manually run this in your Neo4j instance

// 1. Create the root node for the Discord bot workflow
CREATE (root:STEP {
  id: "root",
  name: "Discord Bot Root",
  description: "Entry point for Discord messages",
  function: "utils.workflow.pass_through",
  input: "{}"
})

// 2. Create a step to extract and process Discord message data
CREATE (extract:STEP {
  id: "extract_discord_data",
  name: "Extract Discord Data",
  description: "Extracts and organizes data from Discord messages",
  function: "utils.data.transform",
  input: JSON.stringify({
    message: "@{SESSION_ID}.initial.message.content",
    discord_data: {
      user: "@{SESSION_ID}.initial.author",
      member: "@{SESSION_ID}.initial.member",
      channel: "@{SESSION_ID}.initial.channel",
      guild: "@{SESSION_ID}.initial.guild",
      timestamp: "@{SESSION_ID}.initial.message.createdAt",
      session_id: "@{SESSION_ID}.initial.session_id"
    }
  })
})

// 3. Create a step to log session information
CREATE (log_session:STEP {
  id: "log_session",
  name: "Log Session Info",
  description: "Logs session information for debugging",
  function: "utils.data.transform",
  input: JSON.stringify({
    session_info: {
      session_id: "@{SESSION_ID}.initial.session_id",
      channel: "@{SESSION_ID}.initial.channel.name",
      user: "@{SESSION_ID}.initial.author.username",
      timestamp: "@{SESSION_ID}.initial.message.createdAt"
    }
  })
})

// 4. Create a step to generate a response
CREATE (respond:STEP {
  id: "generate_response",
  name: "Generate Response",
  description: "Generates a response to the Discord message",
  function: "ai.openai.chat",
  input: JSON.stringify({
    messages: [
      {
        role: "system", 
        content: "You are a helpful assistant in a Discord server. Respond to user messages in a friendly manner. You have access to information about the message, user, and context."
      },
      {
        role: "user", 
        content: "Here is information about me and my message:\n\nChannel: @{SESSION_ID}.extract_discord_data.discord_data.channel.name\nUsername: @{SESSION_ID}.extract_discord_data.discord_data.user.username\nMessage: @{SESSION_ID}.extract_discord_data.message\nSession ID: @{SESSION_ID}.extract_discord_data.discord_data.session_id"
      }
    ],
    model: "gpt-3.5-turbo",
    temperature: 0.7
  })
})

// 5. Create a step to format the response for Discord
CREATE (format:STEP {
  id: "format_response",
  name: "Format Response",
  description: "Formats the response for Discord",
  function: "utils.data.transform",
  input: JSON.stringify({
    content: "@{SESSION_ID}.generate_response.choices[0].message.content",
    formatted_for_discord: true
  })
})

// 6. Connect the nodes to create the workflow
CREATE 
  (root)-[:NEXT]->(extract),
  (extract)-[:NEXT]->(log_session),
  (log_session)-[:NEXT]->(respond),
  (respond)-[:NEXT]->(format)

// 7. Create the workflow definition
CREATE (workflow:WORKFLOW {
  id: "discord-bot",
  name: "Discord Bot Workflow",
  description: "A workflow that processes Discord messages and generates responses",
  root_step: "root"
})

// 8. Connect workflow to its root step
CREATE (workflow)-[:HAS_ROOT]->(root); 