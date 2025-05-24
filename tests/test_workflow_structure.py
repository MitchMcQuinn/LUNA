"""
Comprehensive Workflow Structure Test

This script examines the complete workflow structure in Neo4j:
- All STEP nodes and their properties
- All NEXT relationships and their properties  
- Complete graph structure for workflows
"""

import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment
load_dotenv('.env.local')

from core.database import get_neo4j_driver

def print_section(title):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f"=== {title} ===")
    print('='*60)

def format_properties(props):
    """Format properties for readable display"""
    if not props:
        return "None"
    
    formatted = {}
    for key, value in props.items():
        if isinstance(value, str) and len(value) > 100:
            formatted[key] = f"{value[:100]}... (truncated)"
        else:
            formatted[key] = value
    
    return json.dumps(formatted, indent=2, default=str)

def main():
    driver = get_neo4j_driver()
    
    try:
        with driver.get_session() as session:
            
            # 1. Examine all STEP nodes
            print_section("ALL STEP NODES")
            result = session.run('''
                MATCH (s:STEP)
                RETURN s.id as id, properties(s) as props
                ORDER BY s.id
            ''')
            
            steps = list(result)
            print(f"Found {len(steps)} STEP nodes:")
            
            for i, record in enumerate(steps, 1):
                step_id = record['id']
                props = record['props']
                
                print(f"\n--- STEP {i}: {step_id} ---")
                print(format_properties(props))
            
            # 2. Examine all NEXT relationships
            print_section("ALL NEXT RELATIONSHIPS")
            result = session.run('''
                MATCH (from:STEP)-[r:NEXT]->(to:STEP)
                RETURN from.id as from_step, 
                       to.id as to_step,
                       properties(r) as rel_props
                ORDER BY from.id, to.id
            ''')
            
            next_rels = list(result)
            print(f"Found {len(next_rels)} NEXT relationships:")
            
            for i, record in enumerate(next_rels, 1):
                print(f"\n--- NEXT {i} ---")
                print(f"From: {record['from_step']}")
                print(f"To: {record['to_step']}")
                print(f"Properties: {format_properties(record['rel_props'])}")
            
            # 3. Examine all other relationships involving STEP nodes
            print_section("ALL OTHER STEP RELATIONSHIPS")
            result = session.run('''
                MATCH (s:STEP)-[r]-(other)
                WHERE type(r) <> 'NEXT'
                RETURN s.id as step_id,
                       type(r) as rel_type,
                       labels(other) as other_labels,
                       CASE WHEN 'id' in keys(other) THEN other.id ELSE 'no_id' END as other_id,
                       properties(r) as rel_props
                ORDER BY s.id, rel_type
            ''')
            
            other_rels = list(result)
            print(f"Found {len(other_rels)} other relationships:")
            
            for i, record in enumerate(other_rels, 1):
                print(f"\n--- RELATIONSHIP {i} ---")
                print(f"Step: {record['step_id']}")
                print(f"Relationship: {record['rel_type']}")
                print(f"Connected to: {record['other_labels']} (id: {record['other_id']})")
                print(f"Properties: {format_properties(record['rel_props'])}")
            
            # 4. Look for WORKFLOW nodes
            print_section("WORKFLOW NODES")
            result = session.run('''
                MATCH (w:WORKFLOW)
                RETURN w.id as id, properties(w) as props
                ORDER BY w.id
            ''')
            
            workflows = list(result)
            if workflows:
                print(f"Found {len(workflows)} WORKFLOW nodes:")
                for i, record in enumerate(workflows, 1):
                    print(f"\n--- WORKFLOW {i}: {record['id']} ---")
                    print(format_properties(record['props']))
            else:
                print("No WORKFLOW nodes found")
            
            # 5. Check for workflow patterns (steps connected to workflow-like structures)
            print_section("WORKFLOW PATTERNS")
            result = session.run('''
                MATCH (start:STEP)
                WHERE NOT EXISTS((start)<-[:NEXT]-())
                OPTIONAL MATCH path = (start)-[:NEXT*]->(end:STEP)
                WHERE NOT EXISTS((end)-[:NEXT]->())
                RETURN start.id as start_step,
                       collect(DISTINCT [n.id for n in nodes(path) WHERE n:STEP]) as path_steps,
                       length(path) as path_length
                ORDER BY path_length DESC
            ''')
            
            patterns = list(result)
            print(f"Found {len(patterns)} workflow patterns (chains of NEXT relationships):")
            
            for i, record in enumerate(patterns, 1):
                start = record['start_step']
                steps = record['path_steps']
                length = record['path_length']
                
                print(f"\n--- PATTERN {i} ---")
                print(f"Starts with: {start}")
                print(f"Path length: {length}")
                if steps and steps[0]:  # Check if we have actual step chains
                    print(f"Step chain: {' -> '.join(steps[0])}")
                else:
                    print(f"Single step (no outgoing NEXT relationships)")
            
            # 6. Look for discord_operator specifically
            print_section("DISCORD_OPERATOR SEARCH")
            
            # Search for steps with discord_operator in name or properties
            result = session.run('''
                MATCH (s:STEP)
                WHERE s.id CONTAINS 'discord' OR 
                      toString(properties(s)) CONTAINS 'discord' OR
                      s.id = 'discord_operator'
                RETURN s.id as id, properties(s) as props
            ''')
            
            discord_steps = list(result)
            if discord_steps:
                print(f"Found {len(discord_steps)} discord-related steps:")
                for record in discord_steps:
                    print(f"\n--- {record['id']} ---")
                    print(format_properties(record['props']))
            else:
                print("No discord-related steps found")
            
            # 7. Summary statistics
            print_section("SUMMARY STATISTICS")
            
            # Count various node types
            result = session.run('MATCH (n) RETURN DISTINCT labels(n) as labels, count(*) as count ORDER BY count DESC')
            node_counts = list(result)
            
            print("Node counts by label:")
            for record in node_counts:
                labels = ':'.join(record['labels']) if record['labels'] else 'No Label'
                print(f"  {labels}: {record['count']}")
            
            # Count relationship types
            result = session.run('MATCH ()-[r]->() RETURN type(r) as rel_type, count(*) as count ORDER BY count DESC')
            rel_counts = list(result)
            
            print("\nRelationship counts by type:")
            for record in rel_counts:
                print(f"  {record['rel_type']}: {record['count']}")
            
    finally:
        driver.close()

if __name__ == "__main__":
    main() 