"""
Schema package for generate.py utility.

Contains predefined schemas that can be imported and used with the generate function.
"""

from importlib import import_module

def load_schema(schema_name):
    """
    Load a schema by name from the schemas package
    
    Args:
        schema_name: Name of the schema module to load
        
    Returns:
        The SCHEMA dictionary from the specified module
    """
    try:
        module = import_module(f"utils.schemas.{schema_name}")
        return module.SCHEMA
    except (ImportError, AttributeError) as e:
        raise ValueError(f"Error loading schema '{schema_name}': {e}") 