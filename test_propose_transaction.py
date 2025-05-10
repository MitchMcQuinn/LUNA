#!/usr/bin/env python3
"""
Test script for the propose_transaction.py tool

This script allows you to test the transaction proposal functionality
with the Safe SDK without needing to run it through the workflow engine.
"""

import os
import sys
import json
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Add project root to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Test Safe transaction proposal')
    
    parser.add_argument('--safe-address', required=True, 
                        help='Address of the Safe')
    
    parser.add_argument('--to', required=True,
                        help='Recipient address for the transaction')
    
    parser.add_argument('--value', default='0',
                        help='Amount to send in wei (default: 0)')
    
    parser.add_argument('--data', default='0x',
                        help='Transaction data in hex format (default: 0x)')
    
    parser.add_argument('--operation', type=int, default=0, choices=[0, 1],
                        help='Operation type: 0 for Call, 1 for DelegateCall (default: 0)')
    
    parser.add_argument('--chain-id', type=int, required=True,
                        help='Chain ID where the Safe is deployed (e.g., 1 for Ethereum mainnet)')
    
    parser.add_argument('--sender-address', required=True,
                        help='Address of the proposer account')
    
    parser.add_argument('--private-key', required=False,
                        help='Private key of the proposer (if not provided, will check SAFE_PRIVATE_KEY env var)')
    
    parser.add_argument('--api-url', 
                        help='Custom Safe Transaction Service URL (optional)')
    
    return parser.parse_args()

def main():
    """Run the transaction proposal test"""
    args = parse_args()
    
    # Get private key from args or environment variable
    private_key = args.private_key or os.environ.get('SAFE_PRIVATE_KEY')
    if not private_key:
        print("Error: No private key provided. Use --private-key or set SAFE_PRIVATE_KEY environment variable")
        sys.exit(1)
    
    # Prepare transaction data
    transaction_data = {
        'to': args.to,
        'value': args.value,
        'data': args.data,
        'operation': args.operation
    }
    
    # Import the propose_transaction module
    try:
        from utils.tools.propose_transaction import main as propose_transaction
        
        # Set up the global variables expected by the script
        globals_dict = {
            'safe_address': args.safe_address,
            'transaction_data': transaction_data,
            'chain_id': args.chain_id,
            'sender_address': args.sender_address,
            'sender_private_key': private_key,
        }
        
        if args.api_url:
            globals_dict['api_url'] = args.api_url
            
        # Update globals with our parameters
        for key, value in globals_dict.items():
            globals()[key] = value
            
        # Run the transaction proposal
        result = propose_transaction()
        
        # Print the result
        print(json.dumps(result, indent=2))
        
    except ImportError as e:
        print(f"Error importing propose_transaction module: {e}")
        print("Make sure the Safe SDK dependencies are installed:")
        print("pip install web3 safe-sdk-api-kit safe-sdk-protocol-kit safe-sdk-types-kit")
        sys.exit(1)
    except Exception as e:
        print(f"Error proposing transaction: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 