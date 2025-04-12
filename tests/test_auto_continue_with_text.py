#!/usr/bin/env python3
"""
Test the auto-continue functionality for Claude chats that already have "Continue" in the input field.
"""

import time
from unittest.mock import patch

# Import our modules
from refined_claude.features import run_auto_continue, check_should_continue, perform_auto_continue
from refined_claude.test_base import XMLAccessibilityTestBase


class TestAutoContinueWithText(XMLAccessibilityTestBase):
    """Test the auto-continue functionality for Claude chats when text already exists."""

    def setUp(self):
        """Set up the test environment with the XML dump."""
        self.setUp_with_xml('hit_max_length_textarea_continue.xml', date='20250410')

    def test_check_should_continue_with_existing_text(self):
        """Test the read-only part of auto-continue that analyzes if continuation is needed."""
        # Test with a fresh continuation history
        continue_history = [None]
        sticky_footer = check_should_continue(
            self.web_view, continue_history, 0, self.content_element
        )

        # The test data should indicate we should continue
        self.assertIsNotNone(sticky_footer, "Should find sticky footer when continuation is needed")

        # Check that continue_history was updated
        self.assertIsNotNone(continue_history[0], "Continue history should be updated")

    def test_perform_auto_continue_with_existing_text(self):
        """Test the DOM manipulation part of auto-continue with existing 'Continue' text."""
        # First get the sticky footer from the read-only function
        sticky_footer = check_should_continue(
            self.web_view, [None], 0, self.content_element
        )
        self.assertIsNotNone(sticky_footer, "Sticky footer should be found")

        # Mock the press functionality and time.sleep for testing
        with patch('refined_claude.accessibility.HAX.press') as mock_press, \
             patch('time.sleep'):  # Mock sleep to speed up test

            # Run the function that should still work even with existing "Continue" text
            result = perform_auto_continue(self.web_view, sticky_footer, False)

            # Should return True because the function should still work with existing "Continue" text
            self.assertTrue(result, "Should continue even with existing 'Continue' text")

            # Verify the send button was pressed
            mock_press.assert_called_once()

    def test_run_auto_continue_with_existing_text(self):
        """Test the full auto-continue process with existing 'Continue' text."""
        continue_history = [None]

        # Mock the press functionality and time.sleep for testing
        with patch('refined_claude.accessibility.HAX.press') as mock_press, \
             patch('time.sleep'):  # Mock sleep to speed up test

            # Run the full auto-continue function
            run_auto_continue(self.web_view, False, continue_history, 0, self.content_element)

            # Verify continue_history was updated
            self.assertIsNotNone(continue_history[0], "Continue history should be updated")

            # Verify the send button was pressed
            mock_press.assert_called_once()


if __name__ == "__main__":
    unittest.main()
