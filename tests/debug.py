"""
Debug script to check environment variables.
"""

import os
from dotenv import load_dotenv

# Load environment variables from the correct location
load_dotenv("LUNA/.env.local")

# Print environment variables
print("Environment variables:")
print(f"NEO4J_URI: '{os.environ.get('NEO4J_URI')}'")
print(f"NEO4J_USERNAME: '{os.environ.get('NEO4J_USERNAME')}'")
print(f"NEO4J_PASSWORD: '{os.environ.get('NEO4J_PASSWORD')}'")
print(f"OPENAI_API_KEY: '{os.environ.get('OPENAI_API_KEY')}'")

# Check if the file paths are correct
print("\nFile paths:")
print(f"Current directory: {os.getcwd()}")
print(f".env.local exists: {os.path.exists('.env.local')}")
print(f"LUNA/.env.local exists: {os.path.exists('LUNA/.env.local')}")

# Print the contents of LUNA/.env.local
print("\nContents of LUNA/.env.local:")
try:
    with open('LUNA/.env.local', 'r') as f:
        print(f.read())
except Exception as e:
    print(f"Error reading LUNA/.env.local: {e}") 