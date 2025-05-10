"""
Reimbursement confirmation schema for generate.py utility.
"""

SCHEMA = {
    "type": "object",
    "required": ["response"],
    "properties": {
        "response": {
            "type": "string",
            "description": "The response to the user that summarizes the reimbursement request details and asks for confirmation. If the user confirms, thank them and indicate the process is complete. If they reject, ask what details need to be corrected."
        }
    }
}
