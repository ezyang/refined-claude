#!/usr/bin/env python3
"""
Test the auto-approve functionality for tool use dialogs.
"""

import sys
import os
import unittest
import logging
import time
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
from refined_claude.accessibility_api import set_using_fake_api as set_using_fake_apis, set_api
from refined_claude.features import run_auto_approve, _last_allow_button_press_time

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)


class TestAutoApprove(unittest.TestCase):
    """Test the auto-approve functionality for tool use dialogs."""

    def setUp(self):
        """Set up the test environment with the XML dump."""
        # Reset the last button press time at the start of each test
        global _last_allow_button_press_time
        _last_allow_button_press_time = 0.0

        # Path to the XML dump of the accessibility tree
        xml_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', 'testdata', '20250410', 'allow_tool.xml'
        ))

        # Initialize the fake API with the XML dump
        self.fake_api = init_fake_api(xml_path)
        set_using_fake_apis(True)
        set_api(self.fake_api)

        # Get the root window element
        window = None
        for element in self.fake_api.root_elements:
            window_hax = HAX(element)
            if window_hax.role == "AXWindow" and window_hax.title == "Claude":
                window = window_hax
                break

        self.assertIsNotNone(window, "Could not find Claude window")

        # Find the web view by traversing the tree using HAX objects
        self.web_view = None
        web_areas = window.findall(lambda e: e.role == "AXWebArea" and e.title == "Claude")

        for web_area in web_areas:
            if hasattr(web_area, 'url') and web_area.url and web_area.url.startswith("https://claude.ai"):
                self.web_view = web_area
                break

        if not self.web_view:
            raise ValueError("Could not find Claude web view in the accessibility tree")

    def tearDown(self):
        """Clean up after the test."""
        # Reset to real API
        set_using_fake_apis(False)

    def test_find_allow_button(self):
        """Test that the 'Allow for this chat' button is found correctly."""
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

    def test_back_off_mechanism(self):
        """Test that the back-off mechanism prevents rapid button presses."""
        # Create a button press tracker
        button_pressed_count = [0]

        # Create a mock press method
        def mock_press(button_self):
            button_pressed_count[0] += 1

        # Using a list for mutable state
        mock_time_value = [1000.0]  # Starting time value in a list for mutability

        def mock_time():
            return mock_time_value[0]

        # Patch both the press method and time.time()
        with patch('refined_claude.accessibility.HAX.press', mock_press), \
             patch('time.time', mock_time):

            # First run should press the button
            run_auto_approve(self.web_view, dry_run=False)
            self.assertEqual(button_pressed_count[0], 1, "Button should be pressed on first run")

            # Second immediate run should not press the button (back-off period)
            run_auto_approve(self.web_view, dry_run=False)
            self.assertEqual(button_pressed_count[0], 1, "Button should not be pressed again immediately")

            # Advance the clock by 200ms (well beyond the 100ms back-off period)
            mock_time_value[0] += 0.2

            # After waiting, the button should be pressed again
            run_auto_approve(self.web_view, dry_run=False)
            self.assertEqual(button_pressed_count[0], 2, "Button should be pressed after waiting")

    def test_dry_run_mode(self):
        """Test that the button is not pressed in dry-run mode."""
        # Create a button press tracker to verify it was not called
        button_pressed = [False]  # Use a list to track state within the closure

        # Create a mock press method that accepts self parameter
        def mock_press(button_self):
            button_pressed[0] = True

        # Patch the press method of HAX to use our mock
        with patch('refined_claude.accessibility.HAX.press', mock_press):
            # Run the auto-approve function in dry-run mode
            run_auto_approve(self.web_view, dry_run=True)

            # Verify that the button was found but not pressed
            self.assertFalse(button_pressed[0], "The button was pressed even in dry-run mode")

    def test_allow_tool_dialog_exists(self):
        """Test that the 'Allow tool' dialog exists in the accessibility tree."""
        # Find the dialog by pattern matching as described in run_auto_approve
        dialog = None

        # Look for the dialog in the web view structure
        for main_group in self.web_view.children:
            if main_group.role == "AXGroup" and "min-h-screen" in main_group.dom_class_list:
                for modal_group in main_group.children:
                    if modal_group.role == "AXGroup" and "bg-black" in modal_group.dom_class_list:
                        for tool_dialog in modal_group.children:
                            if (tool_dialog.role == "AXGroup" and
                                tool_dialog.title and
                                tool_dialog.title.startswith("Allow tool")):
                                dialog = tool_dialog
                                break

        # Verify the dialog exists
        self.assertIsNotNone(dialog, "Allow tool dialog not found in accessibility tree")

        # Verify the dialog has the expected title
        self.assertTrue(dialog.title.startswith("Allow tool"),
                        f"Dialog has unexpected title: {dialog.title}")

        # Verify the dialog contains the expected button
        buttons = dialog.findall(lambda e: e.role == "AXButton" and e.title == "Allow for this chat")
        self.assertTrue(len(buttons) > 0, "Allow for this chat button not found in dialog")


if __name__ == "__main__":
    unittest.main()
