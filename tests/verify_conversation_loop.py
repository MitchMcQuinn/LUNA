#!/usr/bin/env python3
"""
Script to verify the conversation_loop.cypher file has the correct structure.
"""

import logging
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def read_file(file_path="conversation_loop.cypher"):
    """Read the file contents."""
    try:
        with open(file_path, "r") as f:
            content = f.read()
            logger.info(f"Successfully read {file_path}")
            return content
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return None

def verify_structure(content):
    """Verify the structure of the conversation loop."""
    if not content:
        logger.error("No content to verify")
        return False
    
    # Check for the presence of all required nodes
    required_nodes = ["root", "request", "generate", "reply"]
    missing_nodes = []
    
    for node in required_nodes:
        if f"id: '{node}'" not in content:
            missing_nodes.append(node)
    
    if missing_nodes:
        logger.error(f"Missing nodes: {missing_nodes}")
        return False
    else:
        logger.info("All required nodes are present")
    
    # Check for node connections
    connections = [
        ("root", "request"),
        ("request", "generate"),
        ("generate", "reply")
    ]
    
    for source, target in connections:
        # Look for direct relationships in the form (source)-[:NEXT]->(target)
        direct_pattern = f"\\({source}[^)]*\\)-\\[:NEXT\\]->\\({target}"
        # Also look for variable-based relationships like (sourceVar:STEP {id: 'source'})-[:NEXT]->(targetVar:STEP {id: 'target'})
        var_pattern = f"\\([a-zA-Z0-9_]+:STEP {{[^}}]*id: '{source}'[^}}]*}}\\)-\\[:NEXT\\]->\\([a-zA-Z0-9_]+:STEP {{[^}}]*id: '{target}'"
        
        if not (re.search(direct_pattern, content) or re.search(var_pattern, content)):
            logger.error(f"Missing connection: {source} -> {target}")
            return False
        else:
            logger.info(f"Connection {source} -> {target} verified")
    
    # Check for conditional loop back from reply to request
    reply_request_pattern = r"\(reply[^)]*\)-\[:NEXT\s*\{\s*conditions:\s*\[[^\]]+\]\s*\}\]->\(request"
    var_reply_request_pattern = r"\([a-zA-Z0-9_]+:STEP {[^}]*id: 'reply'[^}]*}\)-\[:NEXT\s*\{\s*conditions:\s*\[[^\]]+\]\s*\}\]->\([a-zA-Z0-9_]+:STEP {[^}]*id: 'request'"
    
    if not (re.search(reply_request_pattern, content) or re.search(var_reply_request_pattern, content)):
        logger.error("Missing conditional loop back from reply to request")
        return False
    else:
        logger.info("Conditional loop back from reply to request verified")
    
    # Check if the condition uses merits_followup
    condition_pattern = r"conditions:\s*\[\s*\"([^\"]+)\"\s*\]"
    condition_match = re.search(condition_pattern, content)
    
    if condition_match:
        condition = condition_match.group(1)
        if "merits_followup" in condition:
            logger.info(f"Loop back condition uses merits_followup: {condition}")
        else:
            logger.warning(f"Loop back condition does not use merits_followup: {condition}")
    
    # Check for the correct functions
    functions = {
        "request": "utils.request.request",
        "generate": "utils.generate.generate",
        "reply": "utils.reply.reply"
    }
    
    for node, expected_function in functions.items():
        function_pattern = f"id: '{node}'[^}}]*function: '{expected_function}'"
        if not re.search(function_pattern, content):
            logger.error(f"Node {node} missing correct function: {expected_function}")
            return False
        else:
            logger.info(f"Node {node} has correct function: {expected_function}")
    
    # All checks passed
    logger.info("All structure checks passed")
    return True

def main():
    """Main function."""
    content = read_file()
    if not content:
        return
    
    # Print the file content for reference
    logger.info("File content for reference:")
    for i, line in enumerate(content.split('\n'), 1):
        logger.info(f"{i:02d}: {line}")
    
    logger.info("\nVerifying structure...")
    
    if verify_structure(content):
        logger.info("\nCONCLUSION: conversation_loop.cypher has the correct structure")
    else:
        logger.error("\nCONCLUSION: conversation_loop.cypher has structural issues")

if __name__ == "__main__":
    main() 