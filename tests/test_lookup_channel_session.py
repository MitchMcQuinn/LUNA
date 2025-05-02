import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

class TestLookupChannelSession(unittest.TestCase):
    
    @patch("core.session_manager.get_session_manager")
    def test_lookup_by_message_id(self, mock_get_session_manager):
        """Test that the script can find a session using a message ID reference"""
        # Mock the session manager and database response
        mock_session_manager = MagicMock()
        mock_get_session_manager.return_value = mock_session_manager
        
        mock_session = MagicMock()
        mock_session_manager.driver.get_session.return_value.__enter__.return_value = mock_session
        
        # Mock a successful database query result
        mock_result = MagicMock()
        mock_record = {
            "session_id": "test-session-123",
            "message_id": "test-message-456",
            "content": "Test message content"
        }
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        
        # Set up the test environment
        test_env = {
            "message_id": "test-message-456"
        }
        
        # Run the script in the test environment
        with patch.dict("sys.modules"):
            with patch.dict(globals(), test_env):
                from utils.tools.lookup_channel_session import main
                result = main()
        
        # Check that the script tried to find by message_id
        mock_session.run.assert_called_once()
        call_args = mock_session.run.call_args[0]
        self.assertIn("message_id", call_args[1])
        self.assertEqual(call_args[1]["message_id"], "test-message-456")
        
        # Check the result format
        self.assertEqual(result["session_id"], "test-session-123")
        self.assertEqual(result["message_id"], "test-message-456")
        self.assertEqual(result["content"], "Test message content")
        self.assertTrue(result["found"])
    
    @patch("core.session_manager.get_session_manager")
    def test_no_message_id_provided(self, mock_get_session_manager):
        """Test behavior when no message_id is provided"""
        # Mock the session manager
        mock_get_session_manager.return_value = MagicMock()
        
        # Set up the test environment with no message_id
        test_env = {
            "message_id": None
        }
        
        # Run the script in the test environment
        with patch.dict("sys.modules"):
            with patch.dict(globals(), test_env):
                from utils.tools.lookup_channel_session import main
                result = main()
        
        # Check the result when no message_id is provided
        self.assertIsNone(result["session_id"])
        self.assertFalse(result["found"])
        
        # Verify that we didn't try to make any database calls
        mock_get_session_manager.return_value.driver.get_session.assert_not_called()
    
    @patch("core.session_manager.get_session_manager")
    def test_no_session_found(self, mock_get_session_manager):
        """Test handling when no session is found"""
        # Mock the session manager and database response
        mock_session_manager = MagicMock()
        mock_get_session_manager.return_value = mock_session_manager
        
        mock_session = MagicMock()
        mock_session_manager.driver.get_session.return_value.__enter__.return_value = mock_session
        
        # Mock no results from database
        mock_result = MagicMock()
        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result
        
        # Set up the test environment
        test_env = {
            "message_id": "nonexistent-message-id"
        }
        
        # Run the script in the test environment
        with patch.dict("sys.modules"):
            with patch.dict(globals(), test_env):
                from utils.tools.lookup_channel_session import main
                result = main()
        
        # Check that the script handles not finding a session correctly
        self.assertIsNone(result["session_id"])
        self.assertFalse(result["found"])

if __name__ == "__main__":
    unittest.main() 