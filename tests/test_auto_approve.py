#!/usr/bin/env python3
"""
Test the auto-approve functionality for tool use dialogs.
"""

import time
from unittest.mock import patch

# Import our modules
from refined_claude.features import run_auto_approve, _last_allow_button_press_time
from refined_claude.test_base import XMLAccessibilityTestBase


class TestAutoApprove(XMLAccessibilityTestBase):
    """Test the auto-approve functionality for tool use dialogs."""

    def setUp(self):
        """Set up the test environment with the XML dump."""
        # Reset the last button press time at the start of each test
        global _last_allow_button_press_time
        _last_allow_button_press_time = 0.0

        # Initialize with the allow_tool.xml file, but don't try to find content element
        # since we're mainly concerned with the tool approval dialog
        self.setUp_with_xml('allow_tool.xml', date='20250410', find_content_element=False)

    def tearDown(self):
        """Clean up after the test."""
        pass

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

            # Advance the clock by 1.1s (well beyond the 1s back-off period)
            mock_time_value[0] += 1.1

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
