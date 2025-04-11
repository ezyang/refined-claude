#!/usr/bin/env python3
"""
Test the auto-approve functionality with the edge case XML containing a different title pattern.
"""

import sys
import os
import unittest
import logging
from unittest.mock import patch, MagicMock

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the ApplicationServices and HIServices modules before importing our code
mock_ApplicationServices = MagicMock()
mock_HIServices = MagicMock()
sys.modules['ApplicationServices'] = mock_ApplicationServices
sys.modules['HIServices'] = mock_HIServices

# Import our modules
from refined_claude.fake_accessibility import FakeAccessibilityAPI, init_fake_api
from refined_claude.accessibility import HAX
from refined_claude.features import run_auto_approve, _last_allow_button_press_time

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)


class TestAutoApproveEdgeCase(unittest.TestCase):
    """Test the auto-approve functionality with edge case XML."""

    def setUp(self):
        """Set up the test environment with the edge case XML dump."""
        # Reset the last button press time at the start of each test
        global _last_allow_button_press_time
        _last_allow_button_press_time = 0.0

        # Path to the XML dump of the accessibility tree with the edge case
        xml_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', 'testdata', '20250410', 'approve_weird.xml'
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

    def test_find_allow_button_in_edge_case(self):
        """Test that the 'Allow for this chat' button is found correctly in the edge case XML."""
        # Create a button press tracker to verify it was called
        button_pressed = [False]  # Use a list to track state within the closure
        button_found = [None]  # To store the button that was found

        # Create a mock press method that accepts self parameter
        def mock_press(button_self):
            button_pressed[0] = True
            button_found[0] = button_self

        # Patch the press method of HAX to use our mock
        with patch('refined_claude.accessibility.HAX.press', mock_press):
            # Run the auto-approve function
            run_auto_approve(self.web_view, dry_run=False)

            # Verify that the button was found and pressed
            self.assertTrue(button_pressed[0], "The 'Allow for this chat' button was not pressed")
            self.assertIsNotNone(button_found[0], "Button was not found")

            # Verify it's the correct button by checking its title
            self.assertEqual(button_found[0].title, "Allow for this chat",
                            "The pressed button doesn't have the expected title")


if __name__ == "__main__":
    unittest.main()
