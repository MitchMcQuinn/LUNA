import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment
load_dotenv('.env.local')

from core.database import get_neo4j_driver

driver = get_neo4j_driver()
with driver.get_session() as session:
    # Check recent sessions
    print("=== RECENT SESSIONS ===")
    result = session.run('''
        MATCH (s:SESSION)
        RETURN s.id as session_id, s.workflow_id as workflow, s.created_at as created
        ORDER BY s.created_at DESC 
        LIMIT 5
    ''')
    for record in result:
        print(f"  {record['session_id']} - workflow: {record['workflow']} - created: {record['created']}")
    
    # Check any messages in those sessions
    print("\n=== RECENT MESSAGES ===")
    result = session.run('''
        MATCH (s:SESSION)-[:HAS_MESSAGE]->(m:MESSAGE)
        RETURN s.id as session_id, m.message_id as msg_id, m.content as content, m.author_username as author
        ORDER BY m.created_at DESC
        LIMIT 5
    ''')
    for record in result:
        print(f"  Session {record['session_id']}: {record['author']} - \"{record['content']}\"")

    # Check workflow definitions
    print("\n=== WORKFLOW DEFINITIONS ===")
    result = session.run('MATCH (w:WORKFLOW) RETURN w.id as workflow_id, w.description as desc')
    workflows = list(result)
    if workflows:
        for record in workflows:
            print(f"  {record['workflow_id']}: {record['desc']}")
    else:
        print("  No workflows found in database!")

driver.close() 