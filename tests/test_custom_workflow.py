#!/usr/bin/env python3
"""
Test script for interacting with a custom workflow via the API.
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:5000/api"
WORKFLOW_ID = "example-loop-root"  # Your custom workflow starting point

def main():
    print(f"Testing workflow with ID: {WORKFLOW_ID}")
    
    # Create a new session with the custom workflow
    print("Creating session...")
    response = requests.post(
        f"{BASE_URL}/session", 
        json={"workflow_id": WORKFLOW_ID}
    )
    
    if response.status_code != 200:
        print(f"Error creating session: {response.status_code}")
        print(response.text)
        return
    
    session_data = response.json()
    session_id = session_data['session_id']
    print(f"Created session: {session_id}")
    
    # Display initial messages
    print("\n=== Initial Messages ===")
    for msg in session_data.get('messages', []):
        print(f"{msg['role']}: {msg['content']}")
    
    # Main interaction loop
    while True:
        # Check if awaiting input
        if session_data.get('awaiting_input') is not None:
            user_input = input("\n> ")
            
            if user_input.lower() == 'exit':
                print("Exiting...")
                break
            
            # Send message
            print("Sending message...")
            response = requests.post(
                f"{BASE_URL}/session/{session_id}/message", 
                json={"message": user_input}
            )
            
            if response.status_code != 200:
                print(f"Error sending message: {response.status_code}")
                print(response.text)
                break
            
            session_data = response.json()
            
            # Display new messages
            print("\n=== New Messages ===")
            for msg in session_data.get('messages', []):
                if msg['role'] == 'assistant':
                    print(f"Assistant: {msg['content']}")
        else:
            status = session_data.get('status', 'unknown')
            print(f"\nSession status: {status}")
            if status == 'complete':
                print("Workflow completed.")
            else:
                print("No input required but session not complete.")
                
                # Try to get updated session state
                response = requests.get(f"{BASE_URL}/session/{session_id}")
                if response.status_code == 200:
                    session_data = response.json()
                    continue
            
            break
    
    print("Done.")

if __name__ == "__main__":
    main() 