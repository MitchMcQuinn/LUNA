import requests
import os

# Paste your token directly here for testing
TOKEN = "MTI4MzYwNjcxNzkxNzI5ODc2OQ.GMvgag.xxPsrqTDZwJ_2goau9kY9BRTJdc-83WSExLUJo"

response = requests.get(
    "https://discord.com/api/v10/users/@me",
    headers={"Authorization": f"Bot {TOKEN}"}
)

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
