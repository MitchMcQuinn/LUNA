"""
Utility Registry Test

This test checks that the utility registry can properly load and access
all utilities, especially the utils.code.code function that was failing
in the main application workflow.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_utility_registry():
    """Test that the utility registry can load all utilities successfully"""
    
    logger.info("🔧 Testing Utility Registry")
    logger.info("=" * 50)
    
    try:
        # Load environment variables
        env_file = project_root / '.env.local'
        if env_file.exists():
            load_dotenv(env_file)
            logger.info("✅ Loaded .env.local file")
        
        # Import the utility registry
        logger.info("📦 Importing utility registry...")
        from core.utility_registry import get_utility_registry
        
        # Get the registry instance
        logger.info("🔧 Getting utility registry instance...")
        registry = get_utility_registry()
        
        # Test specific utilities that were failing
        critical_utilities = [
            'utils.code.code',
            'utils.generate.generate',
            'utils.request.request',
            'utils.reply.reply'
        ]
        
        logger.info("🔍 Testing critical utilities...")
        success_count = 0
        
        for utility_path in critical_utilities:
            utility_func = registry.get_utility(utility_path)
            if utility_func:
                logger.info(f"✅ {utility_path}: Found")
                success_count += 1
            else:
                logger.error(f"❌ {utility_path}: Not found")
        
        # Test the specific function that was failing
        logger.info("🎯 Testing the specific failing function: utils.code.code")
        code_func = registry.get_utility('utils.code.code')
        
        if code_func:
            logger.info("✅ utils.code.code function is accessible!")
            
            # Test a simple execution
            try:
                result = code_func(code="result = {'test': 'success', 'value': 42}")
                if result and result.get('result'):
                    logger.info(f"✅ Function execution test successful: {result['result']}")
                    return True
                else:
                    logger.error(f"❌ Function execution failed: {result}")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Function execution error: {e}")
                return False
        else:
            logger.error("❌ utils.code.code function is still not accessible!")
            return False
            
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

def test_utility_registration_details():
    """Get detailed information about what utilities are registered"""
    
    logger.info("📊 Utility Registration Details")
    logger.info("=" * 50)
    
    try:
        from core.utility_registry import get_utility_registry
        registry = get_utility_registry()
        
        # Access the internal utilities dict (this is normally private)
        if hasattr(registry, 'utilities'):
            utilities = registry.utilities
            logger.info(f"Total registered utilities: {len(utilities)}")
            
            # Group by module
            modules = {}
            for path in utilities.keys():
                if '.' in path:
                    module = '.'.join(path.split('.')[:-1])
                    if module not in modules:
                        modules[module] = []
                    modules[module].append(path.split('.')[-1])
                else:
                    if 'root' not in modules:
                        modules['root'] = []
                    modules['root'].append(path)
            
            for module, functions in modules.items():
                logger.info(f"📁 {module}:")
                for func in sorted(functions):
                    logger.info(f"   ✓ {func}")
                    
        return True
        
    except Exception as e:
        logger.error(f"❌ Error getting utility details: {e}")
        return False

def main():
    """Main test function"""
    logger.info("🚀 Starting Utility Registry Test")
    
    success1 = test_utility_registry()
    success2 = test_utility_registration_details()
    
    logger.info("=" * 50)
    if success1:
        logger.info("🎉 Utility registry test passed!")
    else:
        logger.info("❌ Utility registry test failed.")
        
    return success1

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 