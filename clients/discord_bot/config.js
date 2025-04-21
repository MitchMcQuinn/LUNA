import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';
import { GatewayIntentBits } from 'discord.js';

// Get the directory of the current module
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment variables from .env file
dotenv.config({ path: resolve(__dirname, '.env') });

export const config = {
  // Discord configuration
  discord: {
    token: process.env.DISCORD_BOT_TOKEN,
    intents: [
      GatewayIntentBits.Guilds,
      GatewayIntentBits.GuildMessages,
      GatewayIntentBits.MessageContent,
      GatewayIntentBits.GuildMembers
    ]
  },
  
  // LUNA API configuration
  luna: {
    apiUrl: process.env.LUNA_API_URL || 'http://localhost:5000/api',
    workflowId: process.env.LUNA_WORKFLOW_ID || 'discord-root'
  }
}; 