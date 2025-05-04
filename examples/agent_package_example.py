"""
Example that demonstrates how to use the agent package system with generate.py
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
    Run a simple example that demonstrates the agent package system
    """
    # Example using agent and schema_name together
    result = generate(
        agent="reimbursement_processor",  # Use the packaged agent configuration
        schema_name="reimbursement",      # Use the packaged schema
        include_history=True,             # Explicitly set include_history 
        user="I need to be reimbursed 1.5 ETH for the community call I hosted yesterday. My address is 0x123456789abcdef."
    )
    
    # Print the result in a pretty JSON format
    print("Example result using agent and schema_name:")
    print(json.dumps(result, indent=2))
    
    # Example showing how you can override specific agent settings
    print("\nExample with agent but overriding temperature:")
    result2 = generate(
        agent="reimbursement_processor",  # Use the packaged agent configuration
        schema_name="reimbursement",      # Use the packaged schema
        temperature=0.1,                  # Override the agent's temperature value
        include_history=True,             # Explicitly set include_history
        user="I need to be reimbursed 1.5 ETH for the community call I hosted yesterday. My address is 0x123456789abcdef."
    )
    
    # Example of agent without history
    print("\nExample with agent but without history:")
    result3 = generate(
        agent="reimbursement_processor",  # Use the packaged agent configuration
        schema_name="reimbursement",      # Use the packaged schema
        include_history=False,            # Explicitly disable history
        user="I need to be reimbursed 1.5 ETH for the community call I hosted yesterday. My address is 0x123456789abcdef."
    )
    
    # Compare the results
    print("\nComparison of results with different settings:")
    print(f"Default agent with history: {json.dumps(result.get('reimbursement_requests', []), indent=2)[:200]}...")
    print(f"Custom temperature (0.1) with history: {json.dumps(result2.get('reimbursement_requests', []), indent=2)[:200]}...")
    print(f"Without history: {json.dumps(result3.get('reimbursement_requests', []), indent=2)[:200]}...")

if __name__ == "__main__":
    main() 