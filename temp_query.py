#!/usr/bin/env python

from core.session_manager import get_session_manager

def main():
    sm = get_session_manager()
    with sm.driver.get_session() as session:
        # Query for MESSAGE nodes
        result = session.run('''
            MATCH (m:MESSAGE) 
            RETURN m.message_id, m.content, m.session_id 
            LIMIT 10
        ''')
        
        nodes = list(result)
        print(f'MESSAGE NODES (found {len(nodes)}):')
        for r in nodes:
            print(f'ID: {r["m.message_id"]}, Content: {r["m.content"]}, Session: {r["m.session_id"]}')
            
        # Also check for SESSION-to-MESSAGE relationships
        result = session.run('''
            MATCH (s:SESSION)-[r:HAS_MESSAGE]->(m:MESSAGE)
            RETURN s.id as session_id, m.message_id as message_id
            LIMIT 10
        ''')
        
        relationships = list(result)
        print(f'\nSESSION-MESSAGE RELATIONSHIPS (found {len(relationships)}):')
        for r in relationships:
            print(f'Session: {r["session_id"]}, Message: {r["message_id"]}')

if __name__ == "__main__":
    main() 