"""
Example that demonstrates how to use the schema package system with generate.py
"""

import logging
import sys
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add the parent directory to the path
sys.path.append('.')

from utils.generate import generate

def main():
    """
    Run a simple example that demonstrates the schema package system
    """
    # Example using schema_name instead of direct schema
    result = generate(
        model="gpt-4o-mini",  # Use a smaller model for cost savings
        temperature=0.7,
        include_history=True,
        system="You are a helpful assistant that processes reimbursement requests, sometimes multiple reimbursement requests simultaneously. If a token is requested that isn't ETH, DAI, USDT, or USDC, set the token value to an empty string. If the chain isn't specified as either ETH, BASE, or ARB, set the chain value to 'ETH' as default. You are to follow up with the user until all requirements are met. Set the top-level is_complete field to match the is_complete status of the first reimbursement request.",
        schema_name="reimbursement",  # Instead of providing the full schema
        user="I need to be reimbursed 1.5 ETH for the community call I hosted yesterday. My address is 0x123456789abcdef."
    )
    
    # Print the result in a pretty JSON format
    print("Example result using schema_name:")
    print(json.dumps(result, indent=2))
    
    # You can also still use the direct schema if needed
    print("\nUsing direct schema still works as before...")

if __name__ == "__main__":
    main() 