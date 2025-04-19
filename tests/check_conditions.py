#!/usr/bin/env python
"""
Check workflow relationships with the singular 'condition' property name.
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set up paths
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

# Load environment variables
load_dotenv()

# Try to import the session manager
try:
    from core.session_manager import get_session_manager
except ImportError as e:
    logger.error(f"Failed to import components: {e}")
    sys.exit(1)

def check_relationships():
    """Check workflow relationships with the singular 'condition' property."""
    session_manager = get_session_manager()
    
    with session_manager.driver.get_session() as session:
        print("\n=== WORKFLOW RELATIONSHIPS (SINGULAR 'condition') ===")
        result = session.run("""
            MATCH (source:STEP)-[r:NEXT]->(target:STEP)
            RETURN source.id as source, target.id as target,
                   r.condition as condition, r.priority as priority
            ORDER BY source.id, coalesce(priority, 0)
        """)
        
        for record in result:
            source = record["source"]
            target = record["target"]
            condition = record["condition"]
            priority = record["priority"] or "default"
            
            print(f"\n{source} -> {target}")
            print(f"  Priority: {priority}")
            print(f"  Condition: {condition}")
            
            # Try to parse condition JSON
            if condition and isinstance(condition, str):
                try:
                    condition_data = json.loads(condition)
                    print(f"  Parsed Condition: {json.dumps(condition_data, indent=2)}")
                except Exception as e:
                    print(f"  Error parsing condition: {e}")

if __name__ == "__main__":
    check_relationships() 