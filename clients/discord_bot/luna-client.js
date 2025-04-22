import fetch from 'node-fetch';
import { config } from './config.js';

export class LunaClient {
  constructor() {
    this.apiUrl = config.luna.apiUrl;
    this.workflowId = config.luna.workflowId;
  }

  /**
   * Create a new workflow session for each message
   * @param {Object} initialData - Initial data to populate the session with
   * @returns {Promise<Object>} Session data
   */
  async createSession(initialData = {}) {
    try {
      const response = await fetch(`${this.apiUrl}/session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow_id: this.workflowId,
          initial_data: initialData
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to create session: ${response.statusText}`);
      }

      const data = await response.json();
      
      return {
        sessionId: data.session_id,
        status: data.status,
        messages: data.messages || []
      };
    } catch (error) {
      console.error('Error creating LUNA session:', error);
      throw error;
    }
  }

  /**
   * Check if a Discord message is a reply and if it has replies
   * @param {Object} message - Discord message object
   * @returns {Promise<Object>} Object containing is_reply, has_reply, and reply_to flags
   */
  async checkMessageResponses(message) {
    try {
      // Default values
      let isReply = false;
      let hasReply = false;
      let replyTo = null;

      // Check if message is a reply to another message
      if (message.reference && message.reference.messageId) {
        isReply = true;
        replyTo = message.reference.messageId;
      }

      // Only check for replies if channel exists and has fetchMessages capability
      if (message.channel && typeof message.channel.messages?.fetch === 'function') {
        // Fetch recent messages in the channel
        const messages = await message.channel.messages.fetch({ limit: 20 });
        
        // Look for messages that reference the current message
        messages.forEach(msg => {
          if (msg.reference && msg.reference.messageId === message.id) {
            hasReply = true;
          }
        });
      }

      return {
        is_reply: isReply,
        has_reply: hasReply,
        reply_to: replyTo
      };
    } catch (error) {
      console.error('Error checking message responses:', error);
      // Default to false if there's an error
      return {
        is_reply: false,
        has_reply: false,
        reply_to: null
      };
    }
  }

  /**
   * Send a message to the workflow
   * @param {string} message - Message content
   * @param {Object} contextData - Additional context data to send
   * @param {Object} discordMessage - Original Discord message object for response checking
   * @returns {Promise<Object>} Response from the workflow
   */
  async sendMessage(message, contextData = {}, discordMessage = null) {
    try {
      // If we have the original Discord message object, check for responses
      if (discordMessage) {
        const responseFlags = await this.checkMessageResponses(discordMessage);
        
        // Add the response flags to context data
        contextData = {
          ...contextData,
          is_reply: responseFlags.is_reply,
          has_reply: responseFlags.has_reply,
          reply_to: responseFlags.reply_to
        };
      }
      
      // Create a new session for each message
      const session = await this.createSession(contextData);
      
      // Send the message to the session
      const response = await fetch(`${this.apiUrl}/session/${session.sessionId}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: message
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to send message: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error sending message to LUNA:', error);
      throw error;
    }
  }

  /**
   * Get the current state of a session
   * @param {string} channelId - Discord channel ID associated with the session
   * @returns {Promise<Object>} Current session state
   */
  async getSessionState(channelId) {
    try {
      const session = this.sessions.get(channelId);
      if (!session) {
        throw new Error('No active session for this channel');
      }

      const response = await fetch(`${this.apiUrl}/session/${session.sessionId}`);
      
      if (!response.ok) {
        throw new Error(`Failed to get session state: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Update session status and last message
      this.sessions.set(channelId, {
        ...session,
        status: data.status,
        lastMessage: data.messages[data.messages.length - 1]?.content || null
      });

      return data;
    } catch (error) {
      console.error('Error getting LUNA session state:', error);
      throw error;
    }
  }
} 