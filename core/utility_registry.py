"""
Registry for workflow utility functions.
"""

import logging

logger = logging.getLogger(__name__)

class UtilityRegistry:
    def __init__(self):
        self.utilities = {}
        
    def register_utility(self, path, function):
        """Register a utility function"""
        self.utilities[path] = function
        logger.info(f"Registered utility: {path}")
        
    def get_utility(self, path):
        """Get utility function by path"""
        if not path:
            return None
            
        # First try exact match
        if path in self.utilities:
            return self.utilities[path]
            
        # Then try remapping from function style (module.function) to utility style (utils.module.function)
        if '.' in path and not path.startswith('utils.'):
            remapped_path = f"utils.{path}"
            if remapped_path in self.utilities:
                logger.info(f"Remapped {path} to {remapped_path}")
                return self.utilities[remapped_path]
        
        logger.warning(f"Utility not found: {path}")
        return None
        
    def register_module(self, module_path, module_obj):
        """Register all functions in a module with prefix"""
        for name in dir(module_obj):
            item = getattr(module_obj, name)
            if callable(item) and not name.startswith('_'):
                full_path = f"{module_path}.{name}"
                self.register_utility(full_path, item)

# Singleton pattern
_registry = None

def get_utility_registry():
    global _registry
    if _registry is None:
        _registry = UtilityRegistry()
        
        # Register core utilities
        try:
            import utils.generate
            import utils.request
            import utils.reply
            import utils.conversation
            import utils.cypher
            import utils.api
            import utils.code
            
            _registry.register_module("utils.generate", utils.generate)
            _registry.register_module("utils.request", utils.request)
            _registry.register_module("utils.reply", utils.reply)
            _registry.register_module("utils.conversation", utils.conversation)
            _registry.register_module("utils.cypher", utils.cypher)
            _registry.register_module("utils.api", utils.api)
            _registry.register_module("utils.code", utils.code)
        except ImportError as e:
            logger.warning(f"Could not import utilities: {e}")
        
    return _registry 