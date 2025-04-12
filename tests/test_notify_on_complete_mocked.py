#!/usr/bin/env python3
"""
Test the notify_on_complete functionality for Claude chats using mocking.
"""

import unittest
import logging
from unittest.mock import patch, MagicMock
import subprocess

# Import our modules
from refined_claude.features import (
    run_notify_on_complete, check_notify_state, perform_notification,
    check_chat_running_state
)
from refined_claude.test_base import XMLAccessibilityTestBase
from refined_claude.fake_accessibility import init_fake_api
from refined_claude.accessibility import HAX
from refined_claude.cli import find_chat_content_element

# Set up logging
logging.basicConfig(level=logging.DEBUG)


class TestNotifyOnCompleteMocked(XMLAccessibilityTestBase):
    """Test the notify_on_complete functionality for Claude chats using mocking."""

    def setUp(self):
        """Set up the test environment with the XML dump."""
        # Use in_progress.xml for the test
        self.setUp_with_xml('in_progress.xml', date='20250410')

    def test_check_notify_state_running(self):
        """Test that 'started' is detected correctly when state changes to running."""
        # Set initial state to not running
        running = [False]

        # The in_progress.xml has the Stop button, so it should detect as running
        notification_type = check_notify_state(self.content_element, running, 0)

        # Should detect a state change from not running -> running
        self.assertEqual(notification_type, 'started', "Should detect chat has started")

    def test_check_notify_state_finished(self):
        """Test that 'finished' is detected correctly when state changes to not running."""
        # Set initial state to running
        running = [True]

        # Mock check_chat_running_state to return False (not running)
        with patch('refined_claude.features.check_chat_running_state', return_value=False):
            # Test notification state detection with mocked non-running state
            notification_type = check_notify_state(self.content_element, running, 0)

            # Should detect a state change from running -> not running
            self.assertEqual(notification_type, 'finished', "Should detect chat has finished")

    def test_perform_notification(self):
        """Test the notification function works correctly."""
        running = [True]  # Starting state (running)

        # Mock subprocess.check_call to avoid actual system notifications
        with patch('subprocess.check_call') as mock_check_call:
            # Test 'finished' notification
            result = perform_notification('finished', running, 0)

            # Verify results
            self.assertTrue(result, "Should return True for valid notification type")
            self.assertFalse(running[0], "Should update running state to False")
            mock_check_call.assert_called_once()

            # Test call arguments for osascript
            args = mock_check_call.call_args[0][0]
            self.assertEqual(args[0], "osascript")
            self.assertEqual(args[1], "-e")
            self.assertIn("Claude response finished", args[2])

    def test_run_notify_on_complete_full_cycle(self):
        """Test the full notification process from running to finished state."""
        # Set up running state tracking
        running = [False]  # Initially not tracking as running

        # First check with a running state (will set running[0] to True)
        run_notify_on_complete(self.web_view, running, 0, self.content_element)
        self.assertTrue(running[0], "Should detect chat is running")

        # Mock check_chat_running_state to return False to simulate completed state
        with patch('refined_claude.features.check_chat_running_state', return_value=False), \
             patch('subprocess.check_call') as mock_check_call:
            # Run the notification function again
            run_notify_on_complete(self.web_view, running, 0, self.content_element)

            # Verify results
            self.assertFalse(running[0], "Should detect chat is no longer running")
            mock_check_call.assert_called_once()


if __name__ == "__main__":
    unittest.main()
