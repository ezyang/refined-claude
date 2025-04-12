#!/usr/bin/env python3
"""
Test the notify_on_complete functionality for Claude chats.
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


class TestNotifyOnComplete(XMLAccessibilityTestBase):
    """Test the notify_on_complete functionality for Claude chats."""

    def setUp(self):
        """Set up the test environment with the XML dump."""
        # Use in_progress.xml for initial state (chat is running)
        self.xml_path = self.setup_with_xml_path('in_progress.xml')

    def setup_with_xml_path(self, xml_name, date="20250410"):
        """Set up the test environment with the specified XML dump and return the path.

        This is a modified version of setUp_with_xml that doesn't set self.content_element,
        allowing us to reinitialize with a different XML file during the test.

        Args:
            xml_name: Name of the XML file (without path) to use
            date: Date directory containing the XML file (format: YYYYMMDD)

        Returns:
            str: The path to the XML file
        """
        # Get the full path to the XML file
        import os
        xml_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', 'testdata', date, xml_name
        ))

        # Initialize the fake API with the XML dump
        self.fake_api = init_fake_api(xml_path)

        # Get the root window element
        window = None
        for element in self.fake_api.root_elements:
            window_hax = HAX(element, self.fake_api)
            if window_hax.role == "AXWindow" and window_hax.title == "Claude":
                window = window_hax
                break

        self.assertIsNotNone(window, "Could not find Claude window")

        # Find the web view by traversing the tree using HAX objects
        self.web_view = None
        web_areas = window.findall(lambda e: e.role == "AXWebArea" and "Claude" in e.title)

        for web_area in web_areas:
            if hasattr(web_area, 'url') and web_area.url and web_area.url.startswith("https://claude.ai"):
                self.web_view = web_area
                break

        if not self.web_view:
            raise ValueError("Could not find Claude web view in the accessibility tree")

        # Find the content element
        self.content_element = find_chat_content_element(self.web_view)
        self.assertIsNotNone(self.content_element, "Could not find chat content element")

        return xml_path

    def update_xml(self, xml_name, date="20250410"):
        """Reinitialize the fake API with a different XML file.

        Args:
            xml_name: Name of the XML file (without path) to use
            date: Date directory containing the XML file (format: YYYYMMDD)

        Returns:
            None
        """
        self.setup_with_xml_path(xml_name, date)

    def debug_chat_state(self, label=""):
        """Debug helper method to print chat state information."""
        is_running = check_chat_running_state(self.content_element)
        print(f"{label} - Chat running state: {is_running}")

        # Debug: Look for the stop button structure
        sticky_footer = None
        for child in self.content_element.children:
            if child.role == "AXGroup" and hasattr(child, "dom_class_list"):
                classes = child.dom_class_list
                if "sticky" in classes and "bottom-0" in classes:
                    sticky_footer = child
                    print(f"{label} - Found sticky footer")
                    break

        if sticky_footer and sticky_footer.children:
            print(f"{label} - Sticky footer children: {len(sticky_footer.children)}")
            for i, child in enumerate(sticky_footer.children):
                print(f"{label} - Child {i}: {child.role}")
                if child.role == "AXGroup" and child.children:
                    for j, grandchild in enumerate(child.children):
                        print(f"{label} -   Grandchild {j}: {grandchild.role}")
                        if hasattr(grandchild, "children") and grandchild.children:
                            for k, great_grandchild in enumerate(grandchild.children):
                                print(f"{label} -     Great-grandchild {k}: {great_grandchild.role}")
                                if great_grandchild.role == "AXButton" and hasattr(great_grandchild, "description"):
                                    print(f"{label} -       Button desc: {great_grandchild.description}")

    def test_check_notify_state_running(self):
        """Test the read-only part detects running state correctly."""
        # Test with initial state (in_progress.xml - chat is running)
        self.debug_chat_state("Initial XML (in_progress.xml)")

        running = [False]  # Initial state says not running
        notification_type = check_notify_state(self.content_element, running, 0)

        # Should detect a state change from not running -> running
        self.assertEqual(notification_type, 'started', "Should detect chat has started")

    def test_check_notify_state_finished(self):
        """Test the read-only part detects finished state correctly."""
        # Initialize with in_progress.xml first (running state)
        self.debug_chat_state("Before mock (in_progress.xml)")
        running = [True]  # Set initial state to running

        # Use mocking instead of XML swapping since both XMLs have the Stop response button
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

        # First check with in_progress.xml (running state)
        self.debug_chat_state("Before run_notify_on_complete (in_progress.xml)")
        run_notify_on_complete(self.web_view, running, 0, self.content_element)
        self.assertTrue(running[0], "Should detect chat is running")

        # Use mocking instead of XML swapping
        with patch('refined_claude.features.check_chat_running_state', return_value=False), \
             patch('subprocess.check_call') as mock_check_call:
            # Run the notification function again with mocked non-running state
            run_notify_on_complete(self.web_view, running, 0, self.content_element)

            # Verify results
            self.assertFalse(running[0], "Should detect chat is no longer running")
            mock_check_call.assert_called_once()


if __name__ == "__main__":
    unittest.main()
