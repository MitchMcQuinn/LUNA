#!/bin/bash

# Path to the source env.local file
SOURCE_ENV="../../sample.env.local"

# Path to destination .env file
DEST_ENV="./.env"

# Make sure source file exists
if [ ! -f "$SOURCE_ENV" ]; then
  echo "ERROR: Source file $SOURCE_ENV not found!"
  exit 1
fi

# Extract Discord token from env.local if it exists
if grep -q "DISCORD_TOKEN" "$SOURCE_ENV"; then
  DISCORD_TOKEN=$(grep "DISCORD_TOKEN" "$SOURCE_ENV" | cut -d '=' -f2)
  # Update the .env file with this token
  sed -i '' "s/DISCORD_BOT_TOKEN=.*/DISCORD_BOT_TOKEN=$DISCORD_TOKEN/" "$DEST_ENV"
  echo "Discord token updated successfully!"
else
  echo "WARNING: DISCORD_TOKEN not found in $SOURCE_ENV"
  echo "You need to manually update the DISCORD_BOT_TOKEN in $DEST_ENV"
fi

echo "Setup complete. You can now run the bot with: npm start" 