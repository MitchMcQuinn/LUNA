"""
Propose a transaction to a Safe Wallet.

This script uses the Safe API to propose transactions to a Safe Wallet using a proposer account.
Proposers can create and suggest transactions for a Safe without having signing authority.

Example usage:
```
{
  "function": "utils.code.code",
  "file_path": "propose_transaction.py",
  "variables": {
    "safe_address": "0x123...",
    "transaction_data": {
      "to": "0x456...",
      "value": "1000000000000000", 
      "data": "0x",
      "operation": 0
    },
    "chain_id": 1,
    "sender_address": "0x789...",
    "sender_private_key": "0xabc...",
    "api_url": "https://safe-transaction-mainnet.safe.global"
  }
}
```
"""

import json
import logging
import os
import requests
from web3 import Web3

# Configure logger
logger = logging.getLogger(__name__)

def main():
    """
    Propose a transaction to a Safe Wallet using the Safe API.
    
    Required variables:
    - safe_address: Address of the Safe to propose the transaction to
    - transaction_data: Dictionary containing transaction details:
      - to: Recipient address
      - value: Amount to send in wei (as string)
      - data: Transaction data (hexadecimal string)
      - operation: 0 for Call, 1 for DelegateCall (default: 0)
    - chain_id: The chain ID where the Safe is deployed (e.g., 1 for Ethereum mainnet)
    - sender_address: Address of the proposer account
    - sender_private_key: Private key of the proposer account
    - api_url: Optional URL for the Safe Transaction Service API (if not using the default)
    """
    # Extract the required variables
    required_vars = ['safe_address', 'transaction_data', 'chain_id', 'sender_address', 'sender_private_key']
    for var in required_vars:
        if var not in globals():
            raise ValueError(f"Missing required variable: {var}")
    
    # Set up the web3 provider and account
    web3 = Web3(Web3.HTTPProvider('https://rpc.ankr.com/eth'))
    account = web3.eth.account.from_key(sender_private_key)
    
    # Determine the appropriate Safe Transaction Service URL based on chain_id
    if 'api_url' in globals() and api_url:
        service_url = api_url
    else:
        # Default Safe Transaction Service URLs for common networks
        service_urls = {
            1: "https://safe-transaction-mainnet.safe.global",
            5: "https://safe-transaction-goerli.safe.global",
            137: "https://safe-transaction-polygon.safe.global",
            11155111: "https://safe-transaction-sepolia.safe.global",
            42161: "https://safe-transaction-arbitrum.safe.global"  # Arbitrum One
        }
        service_url = service_urls.get(chain_id)
        if not service_url:
            raise ValueError(f"No default Safe Transaction Service URL for chain ID {chain_id}. "
                             f"Please provide an api_url parameter.")
    
    logger.info(f"Using Safe Transaction Service URL: {service_url}")
    
    # Create transaction data from input
    tx_data = {
        "to": transaction_data['to'],
        "value": transaction_data['value'],
        "data": transaction_data.get('data', '0x'),
        "operation": transaction_data.get('operation', 0)
    }
    
    # Get the nonce for the Safe
    nonce_url = f"{service_url}/api/v1/safes/{safe_address}"
    try:
        response = requests.get(nonce_url)
        response.raise_for_status()
        safe_info = response.json()
        nonce = safe_info.get('nonce', 0)
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting Safe nonce: {str(e)}")
        raise
    
    logger.info(f"Using nonce: {nonce}")
    
    # In a real implementation, we would use the Safe Protocol Kit to:
    # 1. Create a Safe transaction
    # 2. Get the transaction hash
    # 3. Sign the transaction hash with the sender's private key
    
    # Mock implementation for demonstration purposes
    # This would be replaced with the actual SDK calls
    safe_tx_hash = Web3.keccak(text=f"{safe_address}-{json.dumps(tx_data)}-{nonce}").hex()
    
    # Sign the transaction hash with the private key
    message_hash = Web3.solidity_keccak(['bytes32'], [Web3.to_bytes(hexstr=safe_tx_hash)])
    signed_message = account.signHash(message_hash)
    signature = signed_message.signature.hex()
    
    # Prepare the transaction payload for the Safe Transaction Service
    payload = {
        "safe": safe_address,
        "to": tx_data["to"],
        "value": tx_data["value"],
        "data": tx_data["data"],
        "operation": tx_data["operation"],
        "safeTxGas": 0,  # Optional: gas that should be used for the safe transaction
        "baseGas": 0,    # Optional: gas costs for data used to trigger the safe transaction
        "gasPrice": 0,   # Optional: gas price that should be used for the payment calculation
        "gasToken": "0x0000000000000000000000000000000000000000",  # Optional: token address (or 0x0 for ETH) that is used for the payment
        "refundReceiver": "0x0000000000000000000000000000000000000000",  # Optional: address of receiver of gas payment (or 0x0 for tx.origin)
        "nonce": nonce,
        "contractTransactionHash": safe_tx_hash,
        "sender": sender_address,
        "signature": signature,
        "origin": os.environ.get('APP_NAME', 'Safe Transaction Proposer')  # Optional app identifier
    }
    
    # Submit the transaction proposal to the Safe Transaction Service
    propose_url = f"{service_url}/api/v1/safes/{safe_address}/multisig-transactions/"
    try:
        logger.info(f"Proposing transaction with hash: {safe_tx_hash}")
        response = requests.post(propose_url, json=payload)
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error proposing transaction: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Response: {e.response.text}")
        raise
    
    # Return the transaction details and result
    return {
        "safe_address": safe_address,
        "transaction_hash": safe_tx_hash,
        "sender_address": sender_address,
        "status": "proposed",
        "api_response": result
    }

# Run the main function and set the result for workflow output
try:
    result = main()
except Exception as e:
    logger.error(f"Error proposing transaction: {str(e)}")
    # Return error information in a structured format
    result = {
        "error": str(e),
        "status": "failed"
    }

"""
Note on Implementation:

This is a simplified mock implementation that demonstrates the general flow of proposing
a transaction to a Safe Wallet. In a production environment, you would need to:

1. Use the actual Safe SDK, which is primarily available in JavaScript/TypeScript.
2. For Python, you may need to use the REST API directly as shown in this example.

For a production-ready implementation, consider:
- Using safe-eth-py if functionality is added in the future
- Creating a JavaScript service to interface with the Safe SDK
- Using the REST API directly as shown here, but with proper error handling and retries

Required Parameters:
- safe_address: The address of the Safe account
- transaction_data: Contains 'to', 'value', 'data', and optional 'operation'
- chain_id: The chain ID where the Safe is deployed
- sender_address: The proposer's address
- sender_private_key: The proposer's private key

Expected Response Format:
{
  "safe_address": "0x123...",
  "transaction_hash": "0x456...",
  "sender_address": "0x789...",
  "status": "proposed",
  "api_response": { ... } // Response from the Safe API
}
"""
