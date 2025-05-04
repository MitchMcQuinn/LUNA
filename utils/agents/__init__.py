"""
Agent package for generate.py utility.

Contains predefined agent configurations that can be imported and used with the generate function.
"""

from importlib import import_module

def load_agent(agent_name):
    """
    Load an agent configuration by name from the agents package
    
    Args:
        agent_name: Name of the agent module to load
        
    Returns:
        The AGENT dictionary from the specified module
    """
    try:
        module = import_module(f"utils.agents.{agent_name}")
        return module.AGENT
    except (ImportError, AttributeError) as e:
        raise ValueError(f"Error loading agent '{agent_name}': {e}") 