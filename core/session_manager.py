"""
Session management for workflow execution.
"""

import json
import uuid
from datetime import datetime
from .database import get_neo4j_driver

class SessionManager:
    def __init__(self, neo4j_driver=None):
        self.driver = neo4j_driver or get_neo4j_driver()
        
    def create_session(self, workflow_id="default"):
        """Create a new workflow session with initial state"""
        session_id = str(uuid.uuid4())
        
        # Initialize the session state
        initial_state = {
            "id": session_id,
            "workflow_id": workflow_id,
            "workflow": {
                "root": {
                    "status": "active",
                    "error": ""
                }
            },
            "data": {
                "outputs": {},
                "messages": []
            }
        }
        
        # Create session node in Neo4j
        with self.driver.get_session() as session:
            session.run(
                """
                CREATE (s:SESSION {
                    id: $id, 
                    state: $state, 
                    created_at: datetime()
                })
                """,
                id=session_id,
                state=json.dumps(initial_state)
            )
            
        return session_id
        
    def get_session_state(self, session_id):
        """Get current session state"""
        with self.driver.get_session() as session:
            result = session.run(
                """
                MATCH (s:SESSION {id: $id})
                RETURN s.state as state
                """,
                id=session_id
            )
            record = result.single()
            if record:
                return json.loads(record["state"])
            return None
            
    def update_session_state(self, session_id, update_func):
        """
        Update session state with optimistic concurrency control
        
        Args:
            session_id: The session ID
            update_func: Function that takes current state and returns updated state
        
        Returns:
            Boolean indicating success
        """
        with self.driver.get_session() as neo_session:
            tx = neo_session.begin_transaction()
            try:
                # Get current state
                result = tx.run(
                    """
                    MATCH (s:SESSION {id: $id})
                    RETURN s.state as state
                    """,
                    id=session_id
                )
                record = result.single()
                if not record:
                    tx.rollback()
                    return False
                    
                # Apply update function
                current_state = json.loads(record["state"])
                updated_state = update_func(current_state)
                
                # Write updated state
                tx.run(
                    """
                    MATCH (s:SESSION {id: $id})
                    SET s.state = $state
                    """,
                    id=session_id,
                    state=json.dumps(updated_state)
                )
                
                tx.commit()
                return True
            except Exception as e:
                tx.rollback()
                raise e
                
    def delete_session(self, session_id):
        """Delete a session from Neo4j"""
        with self.driver.get_session() as session:
            session.run(
                """
                MATCH (s:SESSION {id: $id})
                DELETE s
                """,
                id=session_id
            )
            
    def list_sessions(self):
        """List all sessions"""
        with self.driver.get_session() as session:
            result = session.run(
                """
                MATCH (s:SESSION)
                RETURN s.id as id, s.created_at as created_at
                ORDER BY s.created_at DESC
                """
            )
            return [{"id": record["id"], "created_at": record["created_at"]} 
                   for record in result]

# Singleton pattern for SessionManager
_session_manager = None

def get_session_manager():
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager 