"""
Reimbursement request schema for generate.py utility.
"""

SCHEMA = {
    "type": "object",
    "required": ["reimbursement_requests", "is_complete", "response"],
    "properties": {
        "is_complete": {
            "type": "boolean",
            "description": "Whether the first reimbursement request is complete. A request is complete if all required fields (blockchain_address, person, description, amount, token,) are filled out (ie. not 'None')."
        },
        "response": {
            "type": "string",
            "description": "The response to the reimbursement request. If the address, person, description, amount, or token are not found (ie. listed as 'None'), follow up with the user to get the correct information. If all the information is correct, respond with an appreciative thank you. If no relevant information was found in the user's message at all, respectfully remind the user of your purpose."
        },            
        "reimbursement_requests": {
            "type": "array",
            "description": "Array of reimbursement requests to process",
            "items": {
                "type": "object",
                "required": [
                    "blockchain_address",
                    "person",
                    "description",
                    "amount",
                    "token",
                    "chain"
                ],
                "properties": {
                    "blockchain_address": {
                        "type": "string",
                        "description": "The blockchain address for the reimbursement request."
                    },
                    "person": {
                        "type": "string",
                        "description": "The name of the person requesting the reimbursement."
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the reimbursement request."
                    },
                    "amount": {
                        "type": "number",
                        "description": "The amount to be reimbursed."
                    },
                    "token": {
                        "type": "string",
                        "description": "The token used for the reimbursement. Must be ETH, DAI, USDT, or USDC.",
                        "enum": ["ETH", "DAI", "USDT", "USDC"]
                    },
                    "chain": {
                        "type": "string",
                        "description": "The blockchain chain.",
                        "enum": [
                            "ETH",
                            "BASE",
                            "ARB"
                        ]
                    }
                },
                "additionalProperties": False
            }
        }
    }
} 