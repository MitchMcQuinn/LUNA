#!/bin/bash

# Check if token is set
if grep -q "your_discord_bot_token_here" "./.env"; then
  echo "ERROR: You haven't set your Discord token in .env"
  echo "Please edit the .env file and replace 'your_discord_bot_token_here' with your actual token"
  exit 1
fi

# Check for node_modules
if [ ! -d "./node_modules" ]; then
  echo "Installing dependencies..."
  npm install
fi

# Start the bot
echo "Starting Discord bot..."
npm start 