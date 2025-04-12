#!/usr/bin/env python3
"""
Test the auto-approve functionality with the edge case XML containing a different title pattern.
"""

from unittest.mock import patch

# Import our modules
from refined_claude.features import run_auto_approve, _last_allow_button_press_time
from refined_claude.test_base import XMLAccessibilityTestBase


class TestAutoApproveEdgeCase(XMLAccessibilityTestBase):
    """Test the auto-approve functionality with edge case XML."""

    def setUp(self):
        """Set up the test environment with the edge case XML dump."""
        # Reset the last button press time at the start of each test
        global _last_allow_button_press_time
        _last_allow_button_press_time = 0.0

        # Initialize with the approve_weird.xml file, but don't try to find content element
        # since we're mainly concerned with the tool approval dialog
        self.setUp_with_xml('approve_weird.xml', date='20250410', find_content_element=False)

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
