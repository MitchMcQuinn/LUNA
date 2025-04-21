import { Client, GatewayIntentBits, Partials } from 'discord.js';
import { config } from './config.js';
import { LunaClient } from './luna-client.js';

// Create Discord client with necessary intents
const client = new Client({ 
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildMembers
  ],
  partials: [
    Partials.Channel,
    Partials.Message,
    Partials.User,
    Partials.GuildMember
  ]
});

// Create LUNA API client
const lunaClient = new LunaClient();

// Discord ready event
client.once('ready', () => {
  console.log(`Logged in as ${client.user.tag}`);
  console.log(`Bot is in ${client.guilds.cache.size} servers`);
});

/**
 * Recursively fetches the entire reply chain for a message
 * @param {Message} message - Current Discord message
 * @returns {Promise<Array>} Array of messages in the reply chain (oldest first)
 */
async function getReplyChain(message) {
  // Initialize thread array
  const thread = [];
  
  // Start with the current message
  let currentMessage = message;
  
  // Follow the reply chain backward until we find the root message
  while (currentMessage.reference) {
    try {
      // Fetch the message this is replying to
      const channel = currentMessage.channel;
      const repliedToMessage = await channel.messages.fetch(currentMessage.reference.messageId);
      
      // Extract relevant message data
      thread.unshift({
        id: repliedToMessage.id,
        content: repliedToMessage.content,
        createdAt: repliedToMessage.createdAt.toISOString(),
        author: {
          id: repliedToMessage.author.id,
          username: repliedToMessage.author.username,
          discriminator: repliedToMessage.author.discriminator,
          globalName: repliedToMessage.author.globalName,
          bot: repliedToMessage.author.bot
        }
      });
      
      // Move up the chain
      currentMessage = repliedToMessage;
    } catch (error) {
      console.error('Error fetching reply chain message:', error);
      break; // Break the loop if we can't fetch a message
    }
  }
  
  return thread;
}

// Process incoming messages
client.on('messageCreate', async (message) => {
  // Ignore messages from bots (including self)
  if (message.author.bot) return;
  
  try {
    // Fetch the reply thread history
    const replyChain = await getReplyChain(message);
    
    // Extract all the available context data from the message
    const contextData = {
      message: {
        id: message.id,
        content: message.content,
        createdAt: message.createdAt.toISOString(),
        reference: message.reference ? {
          messageId: message.reference.messageId,
          channelId: message.reference.channelId,
          guildId: message.reference.guildId
        } : null,
        attachments: Array.from(message.attachments.values()).map(a => ({
          id: a.id,
          name: a.name,
          url: a.url,
          contentType: a.contentType
        })),
        components: message.components
      },
      author: {
        id: message.author.id,
        username: message.author.username,
        discriminator: message.author.discriminator,
        globalName: message.author.globalName,
        avatar: message.author.avatar
      },
      member: message.member ? {
        id: message.member.id,
        nickname: message.member.nickname,
        roles: Array.from(message.member.roles.cache.values()).map(r => ({
          id: r.id,
          name: r.name,
          color: r.color,
          position: r.position
        })),
        joinedAt: message.member.joinedAt?.toISOString(),
        displayName: message.member.displayName
      } : null,
      channel: {
        id: message.channel.id,
        name: message.channel.name,
        type: message.channel.type,
        topic: 'topic' in message.channel ? message.channel.topic : null,
        nsfw: 'nsfw' in message.channel ? message.channel.nsfw : null,
        parentId: 'parentId' in message.channel ? message.channel.parentId : null
      },
      guild: message.guild ? {
        id: message.guild.id,
        name: message.guild.name,
        iconURL: message.guild.iconURL(),
        memberCount: message.guild.memberCount
      } : null,
      // Add the thread history as a top-level key
      thread: replyChain
    };

    try {
      // Send the message to LUNA with all context data
      console.log(`Processing message in channel: ${message.channel.id}`);
      const response = await lunaClient.sendMessage(
        message.content,
        contextData,
        message  // Pass the original Discord message object
      );

      // Process LUNA response
      if (response.status === 'complete' || response.status === 'awaiting_input') {
        // Get most recent assistant message if any
        const assistantMessages = response.messages.filter(msg => msg.role === 'assistant');
        if (assistantMessages.length > 0) {
          const lastAssistantMessage = assistantMessages[assistantMessages.length - 1];
          
          // Only reply if we have new content
          if (lastAssistantMessage && lastAssistantMessage.content) {
            await message.reply({
              content: lastAssistantMessage.content,
              // This allows threaded responses if supported
              allowedMentions: { repliedUser: false }
            });
          }
        }
      }
    } catch (error) {
      console.error('Error sending message to LUNA:', error);
      
      // Add debugging response to see the error in Discord
      if (message.content.startsWith('!debug')) {
        await message.reply({
          content: `⚠️ **LUNA API Connection Error**\nCould not connect to LUNA API server.\nPlease make sure it's running at ${config.luna.apiUrl}\n\nError: ${error.message}`,
          allowedMentions: { repliedUser: false }
        });
      }
    }
  } catch (error) {
    console.error('Error processing message:', error);
    // Optionally notify of errors in Discord for visibility
    // await message.reply('Sorry, I encountered an error processing your message.');
  }
});

// Handle errors
client.on('error', (error) => {
  console.error('Discord client error:', error);
});

// Login to Discord
client.login(config.discord.token)
  .catch(error => {
    console.error('Failed to log in to Discord:', error);
    process.exit(1);
  }); 