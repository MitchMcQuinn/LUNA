import pytest
import sys
import os
import json
from unittest.mock import MagicMock, patch
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.graph_engine import GraphWorkflowEngine
from core.session_manager import SessionManager

class TestContextLimit:
    @pytest.fixture
    def mock_driver(self):
        """Create a mock Neo4j driver for testing"""
        driver = MagicMock()
        session = MagicMock()
        transaction = MagicMock()
        result = MagicMock()
        record = MagicMock()
        
        # Configure mocks
        driver.get_session.return_value = session
        session.__enter__.return_value = session
        session.__exit__.return_value = None
        session.begin_transaction.return_value = transaction
        transaction.__enter__.return_value = transaction
        transaction.__exit__.return_value = None
        session.run.return_value = result
        result.single.return_value = record
        
        return driver
    
    @pytest.fixture
    def session_manager(self, mock_driver):
        """Create a session manager with mock driver"""
        manager = SessionManager(driver=mock_driver)
        return manager
    
    @pytest.fixture
    def engine(self, session_manager):
        """Create a graph engine with mocked components"""
        utility_registry = MagicMock()
        utility_registry.get_utility.return_value = lambda **kwargs: kwargs
        
        engine = GraphWorkflowEngine(session_manager=session_manager, utility_registry=utility_registry)
        return engine
    
    def test_unlimited_output_storage(self, engine, mock_driver):
        """Test that outputs are stored without limits by default"""
        session_id = "test-session"
        step_id = "test-step"
        
        # Mock the session state
        state = {
            "id": session_id,
            "workflow": {
                step_id: {
                    "status": "active",
                    "error": ""
                }
            },
            "data": {
                "outputs": {}
            }
        }
        
        # Mock step details without context_limit
        mock_driver.get_session.return_value.run.return_value.single.return_value = {
            "function": "test.function",
            "input": {}
        }
        
        # Mock get_session_state
        engine.session_manager.get_session_state = lambda id: state if id == session_id else None
        
        # Mock update_session_state to update our state object
        def mock_update(id, updater_func):
            nonlocal state
            if id == session_id:
                state = updater_func(state)
            return True
        
        engine.session_manager.update_session_state = mock_update
        
        # Process the step 10 times - should store all outputs
        for i in range(10):
            engine._process_step(session_id, step_id)
        
        # Verify all outputs are stored
        assert len(state["data"]["outputs"][step_id]) == 10
    
    def test_context_limited_output_storage(self, engine, mock_driver):
        """Test that outputs are limited when context_limit is specified"""
        session_id = "test-session"
        step_id = "test-step"
        context_limit = 3
        
        # Mock the session state
        state = {
            "id": session_id,
            "workflow": {
                step_id: {
                    "status": "active",
                    "error": ""
                }
            },
            "data": {
                "outputs": {}
            }
        }
        
        # Mock step details with context_limit
        mock_driver.get_session.return_value.run.return_value.single.return_value = {
            "function": "test.function",
            "input": {"context_limit": context_limit}
        }
        
        # Mock get_session_state
        engine.session_manager.get_session_state = lambda id: state if id == session_id else None
        
        # Mock update_session_state to update our state object
        def mock_update(id, updater_func):
            nonlocal state
            if id == session_id:
                state = updater_func(state)
            return True
        
        engine.session_manager.update_session_state = mock_update
        
        # Mock utility function to return an identifiable value for each call
        utility_func = lambda **kwargs: {"test": len(state["data"].get("outputs", {}).get(step_id, []))}
        engine.utility_registry.get_utility.return_value = utility_func
        
        # Process the step 10 times - should only store last 3 outputs
        for i in range(10):
            engine._process_step(session_id, step_id)
        
        # Verify only context_limit outputs are stored
        assert len(state["data"]["outputs"][step_id]) == context_limit
        
        # Verify the stored outputs are the last ones (indexes 7, 8, 9)
        values = [o["test"] for o in state["data"]["outputs"][step_id]]
        expected = [7, 8, 9]
        assert values == expected, f"Expected {expected}, got {values}"
    
    def test_user_input_respects_context_limit(self, engine, mock_driver):
        """Test that user input handling respects context_limit"""
        session_id = "test-session"
        step_id = "test-step"
        context_limit = 2
        
        # Mock the session state
        state = {
            "id": session_id,
            "workflow": {
                step_id: {
                    "status": "awaiting_input",
                    "error": ""
                }
            },
            "data": {
                "outputs": {
                    step_id: [
                        {"prompt": "Question 1?", "waiting_for_input": True},
                        {"prompt": "Question 2?", "waiting_for_input": True},
                        {"prompt": "Question 3?", "waiting_for_input": True},
                        {"prompt": "Question 4?", "waiting_for_input": True}
                    ]
                }
            }
        }
        
        # Mock step details with context_limit
        mock_driver.get_session.return_value.run.return_value.single.return_value = {
            "function": "test.function",
            "input": {"context_limit": context_limit}
        }
        
        # Patch time.sleep to avoid actual delays
        with patch('time.sleep'):
            # Mock get_session_state
            engine.session_manager.get_session_state = lambda id: state if id == session_id else None
            
            # Mock update_session_state to update our state object
            def mock_update(id, updater_func):
                nonlocal state
                if id == session_id:
                    state = updater_func(state)
                return True
            
            engine.session_manager.update_session_state = mock_update
            
            # Mock _update_execution_paths
            engine._update_execution_paths = lambda id: None
            
            # Handle user input
            engine.handle_user_input(session_id, "User response")
            
            # Verify only context_limit outputs are stored
            assert len(state["data"]["outputs"][step_id]) == context_limit
            
            # Verify the stored outputs are the last ones
            assert state["data"]["outputs"][step_id][-1]["response"] == "User response"
            assert not state["data"]["outputs"][step_id][-1]["waiting_for_input"]

if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 