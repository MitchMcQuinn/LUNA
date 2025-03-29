#!/usr/bin/env python3
"""
Script to analyze the structure defined in conversation_loop.cypher.
"""

import re
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def read_cypher_file(file_path="conversation_loop.cypher"):
    """Read the Cypher file and return its contents."""
    try:
        with open(file_path, "r") as f:
            cypher_content = f.read()
            logger.info(f"Successfully read {file_path}")
            return cypher_content
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return None

def extract_node_definition(node_str):
    """Extract node properties from a node string."""
    node_info = {
        "id": None,
        "description": None,
        "function": None,
        "input": None
    }
    
    # Extract ID
    id_match = re.search(r'id:\s*[\'"]([^\'"]+)[\'"]', node_str)
    if id_match:
        node_info["id"] = id_match.group(1)
    
    # Extract description
    desc_match = re.search(r'description:\s*[\'"]([^\'"]+)[\'"]', node_str)
    if desc_match:
        node_info["description"] = desc_match.group(1)
    
    # Extract function
    func_match = re.search(r'function:\s*[\'"]([^\'"]+)[\'"]', node_str)
    if func_match:
        node_info["function"] = func_match.group(1)
    
    # Extract input - this might contain nested quotes and braces
    input_start = node_str.find("input: '")
    if input_start != -1:
        # Find the matching closing quote, considering escaped quotes
        input_start += 8  # Skip past "input: '"
        nesting_level = 0
        in_string = False
        escape_next = False
        
        for i in range(input_start, len(node_str)):
            char = node_str[i]
            
            if escape_next:
                escape_next = False
                continue
                
            if char == '\\':
                escape_next = True
            elif char == "'" and not escape_next:
                if not in_string:
                    in_string = True
                else:
                    in_string = False
                    if nesting_level == 0:
                        # Found the end of the input string
                        node_info["input"] = node_str[input_start:i]
                        break
            elif char == '{' and not in_string:
                nesting_level += 1
            elif char == '}' and not in_string:
                nesting_level -= 1
    
    return node_info

def parse_cypher_structure(cypher_content):
    """Parse the Cypher content to extract nodes and relationships."""
    if not cypher_content:
        return None
    
    # Extract node definitions directly using a more specific pattern
    # This approach looks for node patterns in the form (alias:STEP {...})
    nodes = {}
    node_aliases = {}
    
    # First try to find all node definitions
    node_pattern = r'\((\w+):STEP\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}\)'
    node_matches = re.finditer(node_pattern, cypher_content)
    
    for match in node_matches:
        alias = match.group(1)
        node_content = match.group(2)
        
        # Extract node properties
        node_info = extract_node_definition(node_content)
        
        if node_info["id"]:
            nodes[node_info["id"]] = node_info
            node_aliases[alias] = node_info["id"]
    
    # Now find all relationships
    relationships = []
    
    # Direct NEXT relationships
    rel_pattern = r'\((\w+)\)-\[:NEXT\]->\((\w+)\)'
    rel_matches = re.finditer(rel_pattern, cypher_content)
    
    for match in rel_matches:
        source_alias = match.group(1)
        target_alias = match.group(2)
        
        if source_alias in node_aliases and target_alias in node_aliases:
            source_id = node_aliases[source_alias]
            target_id = node_aliases[target_alias]
            
            relationships.append({
                "source": source_id,
                "target": target_id,
                "conditions": None
            })
    
    # Conditional NEXT relationships
    cond_rel_pattern = r'\((\w+)\)-\[:NEXT\s*\{\s*conditions:\s*\[([^\]]+)\]\s*\}\]->\((\w+)\)'
    cond_rel_matches = re.finditer(cond_rel_pattern, cypher_content)
    
    for match in cond_rel_matches:
        source_alias = match.group(1)
        conditions_str = match.group(2)
        target_alias = match.group(3)
        
        if source_alias in node_aliases and target_alias in node_aliases:
            source_id = node_aliases[source_alias]
            target_id = node_aliases[target_alias]
            
            # Parse conditions
            conditions = [cond.strip('" \'') for cond in conditions_str.split(',')]
            
            relationships.append({
                "source": source_id,
                "target": target_id,
                "conditions": conditions
            })
    
    # Special case for chained relationships in the conversation_loop.cypher format
    # Extract relationships from patterns like (a)-[:NEXT]->(b)-[:NEXT]->(c)
    # We need to first build the chain from the CREATE statement
    create_match = re.search(r'CREATE\s+(.*?);', cypher_content, re.DOTALL)
    if create_match:
        create_content = create_match.group(1)
        
        # Identify all node aliases in the CREATE statement
        node_refs = []
        for alias, node_id in node_aliases.items():
            node_refs.append((alias, node_id))
        
        # Find all chains of the form (a)-[:NEXT]->(b)
        chain_pattern = r'\((\w+)\)-\[:NEXT\]->\((\w+)\)'
        for match in re.finditer(chain_pattern, create_content):
            source_alias = match.group(1)
            target_alias = match.group(2)
            
            if source_alias in node_aliases and target_alias in node_aliases:
                source_id = node_aliases[source_alias]
                target_id = node_aliases[target_alias]
                
                # Only add if not already in relationships
                if not any(r["source"] == source_id and r["target"] == target_id for r in relationships):
                    relationships.append({
                        "source": source_id,
                        "target": target_id,
                        "conditions": None
                    })
    
    return {"nodes": nodes, "relationships": relationships}

def visualize_structure(structure):
    """Print a visual representation of the workflow structure."""
    if not structure:
        return
    
    nodes = structure["nodes"]
    relationships = structure["relationships"]
    
    logger.info("\n=== WORKFLOW STRUCTURE ===\n")
    
    # Print nodes
    logger.info("NODES:")
    for node_id, node_info in nodes.items():
        logger.info(f"  - {node_id}: {node_info['description']}")
        if node_info["function"]:
            logger.info(f"    Function: {node_info['function']}")
        if node_info["input"]:
            input_preview = node_info["input"]
            if len(input_preview) > 70:
                input_preview = input_preview[:67] + "..."
            logger.info(f"    Input: {input_preview}")
    
    # Print relationships
    logger.info("\nRELATIONSHIPS:")
    for rel in relationships:
        source = rel["source"]
        target = rel["target"]
        conditions = rel["conditions"]
        
        if conditions:
            logger.info(f"  - {source} --> {target} [Conditional: {conditions}]")
        else:
            logger.info(f"  - {source} --> {target}")
    
    # Trace workflow execution paths
    logger.info("\nEXECUTION PATHS:")
    
    # Find the root node
    root_nodes = [node_id for node_id in nodes if node_id == "root"]
    if not root_nodes:
        # If no root node, find nodes with no incoming relationships
        all_targets = [rel["target"] for rel in relationships]
        root_nodes = [node_id for node_id in nodes if node_id not in all_targets]
    
    if not root_nodes:
        logger.warning("  No clear starting point found in the workflow")
        return
    
    # Build adjacency list
    adjacency = {}
    for rel in relationships:
        source = rel["source"]
        target = rel["target"]
        conditions = rel["conditions"]
        
        if source not in adjacency:
            adjacency[source] = []
        
        adjacency[source].append((target, conditions))
    
    # Trace paths from root nodes
    for start in root_nodes:
        trace_paths(start, adjacency, nodes, "", [])

def trace_paths(node, adjacency, nodes, prefix, visited):
    """Recursively trace paths through the workflow."""
    if not prefix:
        logger.info(f"  Path starting from {node}:")
        prefix = "    "
    
    if node in visited:
        logger.info(f"{prefix}* {node} (loop detected)")
        return
    
    visited.append(node)
    
    if node in adjacency:
        for target, conditions in adjacency[node]:
            condition_text = f" [if {conditions}]" if conditions else ""
            logger.info(f"{prefix}→ {target}{condition_text}")
            trace_paths(target, adjacency, nodes, prefix + "  ", visited.copy())
    else:
        logger.info(f"{prefix}→ (end)")

def validate_conversation_loop(structure):
    """Validate the conversation loop structure against expected patterns."""
    if not structure:
        return
    
    nodes = structure["nodes"]
    relationships = structure["relationships"]
    
    # Expected components for a conversation loop
    expected_nodes = ["root", "request", "generate", "reply"]
    
    # Check for required nodes
    missing_nodes = [node for node in expected_nodes if node not in nodes]
    if missing_nodes:
        logger.error(f"Missing essential nodes: {missing_nodes}")
    else:
        logger.info("All essential nodes are present")
    
    # Build adjacency list for validation
    adjacency = {}
    for rel in relationships:
        source = rel["source"]
        target = rel["target"]
        
        if source not in adjacency:
            adjacency[source] = []
        
        adjacency[source].append(target)
    
    # Check basic flow: root -> request -> generate -> reply
    expected_path = ["root", "request", "generate", "reply"]
    for i in range(len(expected_path) - 1):
        source = expected_path[i]
        target = expected_path[i + 1]
        
        if source in adjacency and target in adjacency[source]:
            logger.info(f"Connection {source} -> {target} verified")
        else:
            logger.error(f"Missing connection: {source} -> {target}")
    
    # Check for loop back from reply to request
    if "reply" in adjacency and "request" in adjacency["reply"]:
        logger.info("Loop from reply back to request is present")
    else:
        logger.error("Missing loop from reply back to request")
    
    # Validate node functions
    function_checks = {
        "request": "utils.request.request",
        "generate": "utils.generate.generate",
        "reply": "utils.reply.reply"
    }
    
    for node_id, expected_function in function_checks.items():
        if node_id in nodes:
            actual_function = nodes[node_id].get("function")
            if actual_function == expected_function:
                logger.info(f"Node {node_id} has the correct function: {expected_function}")
            else:
                logger.error(f"Node {node_id} has incorrect function: expected {expected_function}, got {actual_function}")
    
    # Check conditional relationships
    conditional_found = False
    for rel in relationships:
        if rel["source"] == "reply" and rel["target"] == "request":
            if rel["conditions"]:
                conditional_found = True
                logger.info(f"Loop back condition is present: {rel['conditions']}")
                
                # Check the condition is using merits_followup
                if any("merits_followup" in cond for cond in rel["conditions"]):
                    logger.info("Loop back correctly uses merits_followup condition")
                else:
                    logger.warning("Loop back should use merits_followup in conditions")
            else:
                logger.warning("Loop back from reply to request should be conditional")
    
    if not conditional_found:
        logger.error("Missing conditional loop back from reply to request")

def main():
    """Main function to analyze the Cypher structure."""
    cypher_content = read_cypher_file()
    if not cypher_content:
        return
    
    structure = parse_cypher_structure(cypher_content)
    if not structure:
        logger.error("Failed to parse Cypher structure")
        return
    
    logger.info(f"Successfully parsed structure with {len(structure['nodes'])} nodes and {len(structure['relationships'])} relationships")
    
    visualize_structure(structure)
    validate_conversation_loop(structure)

if __name__ == "__main__":
    main() 