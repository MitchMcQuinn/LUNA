"""
Cypher query execution utility for Neo4j graph operations.
"""

import logging
import json
import re
from neo4j.exceptions import Neo4jError, ClientError

# Import core components
from core.session_manager import get_session_manager
from core.variable_resolver import resolve_variable

logger = logging.getLogger(__name__)

def cypher(cypher_query, session_id=None):
    """
    Execute a Cypher query with variable resolution and store results in session.
    
    Args:
        cypher_query: Cypher query string with optional variable references
        session_id: Current session ID for variable resolution
        
    Returns:
        JSON object containing:
            - result: Query execution results
            - error: Error message if query failed (optional)
    """
    logger.info("Starting Cypher execution")
    
    # Get session manager for database access
    session_manager = get_session_manager()
    
    # Get current session state for variable resolution
    if session_id:
        session_state = session_manager.get_session_state(session_id)
    else:
        session_state = None
        logger.warning("No session_id provided, variable resolution will be limited")
    
    try:
        # Resolve variables in the query if it contains references
        if "@{" in cypher_query and session_state:
            logger.info("Resolving variable references in query")
            cypher_query = resolve_query_variables(cypher_query, session_state)
        
        # Execute the query
        results = execute_query(cypher_query, session_manager)
        
        return {
            "result": results,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        return {
            "result": None,
            "error": str(e)
        }

def resolve_query_variables(query, session_state):
    """
    Resolve variable references in a Cypher query.
    
    Args:
        query: Cypher query with variable references
        session_state: Current session state
        
    Returns:
        Query with variables resolved
    """
    # Pattern to match variable references: @{SESSION_ID}.step_id[index].field|default
    var_pattern = r'@\{[^}]+\}(?:\.[a-zA-Z0-9_-]+)(?:\[\d+\])?(?:\.[a-zA-Z0-9_-]+)*(?:\|[^@\s]+)?'
    
    # Find all variable references in the query
    matches = list(re.finditer(var_pattern, query))
    
    # Process each match, starting from the end to avoid offset issues
    for match in reversed(matches):
        var_reference = match.group(0)
        logger.info(f"Found variable reference: {var_reference}")
        
        try:
            # Resolve the variable
            resolved_value = resolve_variable(var_reference, session_state)
            
            # Convert resolved value to string suitable for Cypher
            if resolved_value is None:
                # Check if default value is provided
                if '|' in var_reference:
                    default_value = var_reference.split('|')[-1]
                    logger.info(f"Using default value: {default_value}")
                    cypher_value = default_value
                else:
                    logger.warning(f"Variable {var_reference} resolved to None with no default")
                    cypher_value = "null"
            elif isinstance(resolved_value, str):
                # Escape single quotes for Cypher
                escaped_val = resolved_value.replace("'", "\\'")
                cypher_value = f"'{escaped_val}'"
            elif isinstance(resolved_value, bool):
                cypher_value = str(resolved_value).lower()
            elif isinstance(resolved_value, (int, float)):
                cypher_value = str(resolved_value)
            elif isinstance(resolved_value, list):
                # Convert list to Cypher list format
                elements = []
                for item in resolved_value:
                    if isinstance(item, str):
                        escaped_item = item.replace("'", "\\'")
                        elements.append(f"'{escaped_item}'")
                    else:
                        elements.append(str(item))
                cypher_value = f"[{', '.join(elements)}]"
            elif isinstance(resolved_value, dict):
                # Convert dict to Cypher map format
                pairs = []
                for k, v in resolved_value.items():
                    if isinstance(v, str):
                        escaped_v = v.replace("'", "\\'")
                        pairs.append(f"'{k}': '{escaped_v}'")
                    else:
                        pairs.append(f"'{k}': {v}")
                cypher_value = f"{{{', '.join(pairs)}}}"
            else:
                # For complex objects, use string representation
                cypher_value = str(resolved_value)
            
            # Replace the variable reference with the resolved value
            query = query[:match.start()] + cypher_value + query[match.end():]
            logger.info(f"Resolved to: {cypher_value}")
            
        except Exception as e:
            logger.error(f"Error resolving variable {var_reference}: {e}")
            
            # Check if default value is provided
            if '|' in var_reference:
                default_value = var_reference.split('|')[-1]
                logger.info(f"Using default value due to error: {default_value}")
                query = query[:match.start()] + default_value + query[match.end():]
            else:
                # Replace with null if no default
                logger.warning(f"Replacing unresolvable variable with null")
                query = query[:match.start()] + "null" + query[match.end():]
    
    return query

def execute_query(query, session_manager):
    """
    Execute a Cypher query against Neo4j.
    
    Args:
        query: Cypher query to execute
        session_manager: Session manager for Neo4j access
        
    Returns:
        Query results
    """
    logger.info(f"Executing query: {query}")
    
    # Get Neo4j driver from session manager
    driver = session_manager.driver
    
    results = []
    
    try:
        # Open a session
        with driver.get_session() as session:
            # Execute query
            result = session.run(query)
            
            # Process results
            for record in result:
                # Convert to dict and handle neo4j types
                row = dict(record)
                row = sanitize_neo4j_values(row)
                results.append(row)
    
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise
    
    return results

def sanitize_neo4j_values(data):
    """
    Convert Neo4j types to standard Python types suitable for JSON.
    
    Args:
        data: Data containing Neo4j types
        
    Returns:
        Data with Neo4j types converted to standard Python types
    """
    if isinstance(data, dict):
        return {k: sanitize_neo4j_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_neo4j_values(item) for item in data]
    elif hasattr(data, 'items') and callable(getattr(data, 'items')):
        # Handle Neo4j Node, Relationship, and Path types
        if hasattr(data, 'id') and hasattr(data, 'labels'):
            # This is a Node
            result = {
                '_type': 'Node',
                'id': data.id,
                'labels': list(data.labels),
                'properties': sanitize_neo4j_values(dict(data))
            }
            return result
        elif hasattr(data, 'type') and hasattr(data, 'start_node') and hasattr(data, 'end_node'):
            # This is a Relationship
            result = {
                '_type': 'Relationship',
                'type': data.type,
                'properties': sanitize_neo4j_values(dict(data)),
                'start_node': sanitize_neo4j_values(data.start_node),
                'end_node': sanitize_neo4j_values(data.end_node)
            }
            return result
        else:
            # Generic conversion
            return {k: sanitize_neo4j_values(v) for k, v in data.items()}
    else:
        # Handle basic Python types
        return data 