# Discord Bot Variable Reference Guide

## Introduction

This guide documents all available Discord context variables that the Discord bot client adds to the LUNA session state. These variables can be referenced in your workflow steps using LUNA's variable resolution system.

## Variable Reference Syntax

In LUNA workflows, variables follow this syntax pattern:
```
@{SESSION_ID}.step_id.field
```

For Discord bot integration, initial context data is available under the `initial` step ID:
```
@{SESSION_ID}.initial.field
```

## Message Information

### Basic Message Properties
```
@{SESSION_ID}.initial.message.content          // Message text content
@{SESSION_ID}.initial.message.id               // Unique Discord message ID
@{SESSION_ID}.initial.message.createdAt        // ISO timestamp when message was created
```

### Message References (Replies)
```
@{SESSION_ID}.initial.message.reference.messageId   // ID of the message being replied to
@{SESSION_ID}.initial.message.reference.channelId   // Channel ID of the referenced message
@{SESSION_ID}.initial.message.reference.guildId     // Guild ID of the referenced message
```

### Message Attachments
```
@{SESSION_ID}.initial.message.attachments[0].id          // Attachment ID
@{SESSION_ID}.initial.message.attachments[0].name        // File name
@{SESSION_ID}.initial.message.attachments[0].url         // Download URL
@{SESSION_ID}.initial.message.attachments[0].contentType // MIME type
```

### Message Components
```
@{SESSION_ID}.initial.message.components       // UI components attached to message
```

### Threading Variables
```
@{SESSION_ID}.initial.is_reply                // Boolean flag indicating if the message is a reply to another message
@{SESSION_ID}.initial.has_reply               // Boolean flag indicating if the message has any replies
@{SESSION_ID}.initial.reply_to                // Message ID of the message being replied to (null if not a reply)
```

## User Information

### Author Properties
```
@{SESSION_ID}.initial.author.id                // Discord user ID
@{SESSION_ID}.initial.author.username          // Discord username
@{SESSION_ID}.initial.author.discriminator     // User discriminator (number after #)
@{SESSION_ID}.initial.author.globalName        // Global display name
@{SESSION_ID}.initial.author.avatar            // Avatar reference
```

### Member Properties (Server-specific User Data)
```
@{SESSION_ID}.initial.member.id                // Member ID in the server
@{SESSION_ID}.initial.member.nickname          // Server-specific nickname (if set)
@{SESSION_ID}.initial.member.displayName       // Display name in the server
@{SESSION_ID}.initial.member.joinedAt          // ISO timestamp when user joined server
```

### Member Roles
```
@{SESSION_ID}.initial.member.roles[0].id       // Role ID (access specific role by index)
@{SESSION_ID}.initial.member.roles[0].name     // Role name
@{SESSION_ID}.initial.member.roles[0].color    // Role color
@{SESSION_ID}.initial.member.roles[0].position // Role position in hierarchy
```

## Channel Information

```
@{SESSION_ID}.initial.channel.id               // Discord channel ID
@{SESSION_ID}.initial.channel.name             // Channel name
@{SESSION_ID}.initial.channel.type             // Channel type
@{SESSION_ID}.initial.channel.topic            // Channel topic (if set)
@{SESSION_ID}.initial.channel.nsfw             // Whether channel is NSFW
@{SESSION_ID}.initial.channel.parentId         // Parent category ID (if in category)
```

## Guild (Server) Information

```
@{SESSION_ID}.initial.guild.id                 // Discord server ID
@{SESSION_ID}.initial.guild.name               // Server name
@{SESSION_ID}.initial.guild.iconURL            // Server icon URL
@{SESSION_ID}.initial.guild.memberCount        // Total members in server
```

## Thread History (Reply Chain)

When a message is part of a reply chain, the bot collects the entire thread history:

```
@{SESSION_ID}.initial.thread[0].id             // ID of message in reply chain (oldest first)
@{SESSION_ID}.initial.thread[0].content        // Content of message in reply chain
@{SESSION_ID}.initial.thread[0].createdAt      // Timestamp of message in reply chain
@{SESSION_ID}.initial.thread[0].author.id      // Author ID of message in reply chain
@{SESSION_ID}.initial.thread[0].author.username // Author username of message in reply chain
@{SESSION_ID}.initial.thread[0].author.globalName // Author display name in reply chain
@{SESSION_ID}.initial.thread[0].author.bot     // Whether author is a bot
```

## Common Usage Examples

### Example 1: Personalized Greeting in AI Step

```json
{
  "function": "ai.openai.chat",
  "input": {
    "messages": [
      {
        "role": "system",
        "content": "You are a helpful assistant in the #@{SESSION_ID}.initial.channel.name channel of @{SESSION_ID}.initial.guild.name. Respond in a friendly tone."
      },
      {
        "role": "user",
        "content": "Message from @{SESSION_ID}.initial.author.username}: @{SESSION_ID}.initial.message.content}"
      }
    ],
    "model": "gpt-4"
  }
}
```

### Example 2: Extracting Message Context in a Transform Step

```json
{
  "function": "utils.data.transform",
  "input": {
    "message": "@{SESSION_ID}.initial.message.content",
    "metadata": {
      "author": "@{SESSION_ID}.initial.author.username",
      "channel": "@{SESSION_ID}.initial.channel.name",
      "has_attachments": "@{SESSION_ID}.initial.message.attachments.length > 0",
      "is_reply": "@{SESSION_ID}.initial.message.reference !== null"
    }
  }
}
```

### Example 3: Conditional Path Based on Message Properties

```json
{
  "condition": [
    {
      "operator": "AND",
      "true": "@{SESSION_ID}.initial.channel.name === 'help'",
      "false": "@{SESSION_ID}.initial.author.bot"
    }
  ]
}
```

### Example 4: Using Threading Variables for Reply Management

```json
{
  "condition": [
    {
      "operator": "OR",
      "false": [
        "@{SESSION_ID}.initial.has_reply",
        "@{SESSION_ID}.initial.is_reply && @{SESSION_ID}.initial.reply_to"
      ]
    }
  ]
}
```

## Tips for Working with Discord Variables

1. Always check if optional fields exist before referencing them (especially for `member`, `guild`, and `reference`)
2. For arrays like `roles` and `attachments`, check length or use appropriate indexing
3. Remember that all timestamps are in ISO format and may need conversion
4. For complex conditionals, use transform steps to evaluate expressions first
5. Use the `is_reply`, `has_reply`, and `reply_to` variables to create workflows that manage message threading effectively

## Debugging Variable Resolution

If you need to debug variable resolution, create a transform step that outputs the entire context:

```json
{
  "function": "utils.data.transform",
  "input": {
    "debug_context": "@{SESSION_ID}.initial"
  }
}
```

This will output the complete context object for inspection in your workflow's state. 




{"cypher_query": "CREATE (n:NOTEPAD {author_id:'@{SESSION_ID}.initial.author.id', author_name:'@{SESSION_ID}.initial.author.name', member_role_id:'@{SESSION_ID}.initial.member.roles[0].id', member_role_name:'@{SESSION_ID}.initial.member.roles[0].name', message_id_log: '@{SESSION_ID}.initial.message.id', session_id_log: '@{SESSION_ID}.initial.session_id', description: 'Session log: @{SESSION_ID}.initial.session_id', channel_id:'@{SESSION_ID}.initial.channel.id', server_id:'@{SESSION_ID}.initial.guild.id'})"}

{"cypher_query": "CREATE (n:NOTEPAD {author_id:'@{SESSION_ID}.initial.author.id', author_name:'@{SESSION_ID}.initial.author.name', member_role_id:'@{SESSION_ID}.initial.member.roles.id', member_role_name:'@{SESSION_ID}.initial.member.roles[0].name', message_id_log: '@{SESSION_ID}.initial.message.id', session_id_log: '@{SESSION_ID}.initial.session_id', description: 'Session log: @{SESSION_ID}.initial.session_id', channel_id:'@{SESSION_ID}.initial.channel.id', server_id:'@{SESSION_ID}.initial.guild.id'})"}

{"cypher_query": "CREATE (n:NOTEPAD {message_id_log: '@{SESSION_ID}.initial.message.id', session_id_log: '@{SESSION_ID}.initial.session_id', description: 'Session log: @{SESSION_ID}.initial.session_id', channel_id:'@{SESSION_ID}.initial.channel.id', server_id:'@{SESSION_ID}.initial.guild.id', author_id:'@{SESSION_ID}.initial.author.id'})"}










{"cypher_query": "CREATE (n:NOTEPAD {message_id_log: '@{SESSION_ID}.initial.message.id', session_id_log: '@{SESSION_ID}.initial.session_id', description: 'Session log: @{SESSION_ID}.initial.session_id', channel_id:'@{SESSION_ID}.initial.channel.id', server_id:'@{SESSION_ID}.initial.guild.id', author_id:'@{SESSION_ID}.initial.author.id', author_name: '@{SESSION_ID}.initial.author.username'})"}


{"cypher_query": "CREATE (n:NOTEPAD {message_id_log: '@{SESSION_ID}.initial.message.id', session_id_log: '@{SESSION_ID}.initial.session_id', description: 'Session log: @{SESSION_ID}.initial.session_id', channel_id:'@{SESSION_ID}.initial.channel.id', server_id:'@{SESSION_ID}.initial.guild.id', author_id:'@{SESSION_ID}.initial.author.id', author_name: '@{SESSION_ID}.initial.author.username', member_role_name:'@{SESSION_ID}.initial.member.roles[0].name'})"}