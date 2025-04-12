#!/usr/bin/env python3
"""
Test that auto-continue doesn't trigger when textarea has unrelated content.
"""

import time
from unittest.mock import patch

# Import our modules
from refined_claude.features import run_auto_continue, check_should_continue, perform_auto_continue
from refined_claude.test_base import XMLAccessibilityTestBase


class TestAutoContinueWithOtherText(XMLAccessibilityTestBase):
    """Test the auto-continue functionality when textarea has unrelated content."""

    def setUp(self):
        """Set up the test environment with the XML dump."""
        self.setUp_with_xml('hit_max_length_textarea_other.xml', date='20250410')

    def test_check_should_continue_with_other_text(self):
        """Test that the read-only part correctly identifies the need to continue but observes other text."""
        # Test with a fresh continuation history
        continue_history = [None]
        sticky_footer = check_should_continue(
            self.web_view, continue_history, 0, self.content_element
        )

        # The test data should indicate we should continue (should find sticky footer)
        self.assertIsNotNone(sticky_footer, "Should find sticky footer when continuation is needed")

        # Check that continue_history was updated
        self.assertIsNotNone(continue_history[0], "Continue history should be updated")

    def test_perform_auto_continue_with_other_text(self):
        """Test that DOM manipulation part does not continue when textarea has unrelated content."""
        # First get the sticky footer from the read-only function
        sticky_footer = check_should_continue(
            self.web_view, [None], 0, self.content_element
        )
        self.assertIsNotNone(sticky_footer, "Sticky footer should be found")

        # Perform the auto-continue function (should not trigger due to unrelated text)
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = perform_auto_continue(self.web_view, sticky_footer, False)

        # Should return False because the textarea contains unrelated text ("Other")
        self.assertFalse(result, "Should not continue when textarea has unrelated content")

    def test_run_auto_continue_with_other_text(self):
        """Test the full auto-continue process with unrelated text in textarea."""
        continue_history = [None]

        # Mock the press functionality and time.sleep for testing
        with patch('refined_claude.accessibility.HAX.press') as mock_press, \
             patch('time.sleep'):  # Mock sleep to speed up test

            # Run the full auto-continue function
            run_auto_continue(self.web_view, False, continue_history, 0, self.content_element)

            # Verify continue_history was updated (analysis part still runs)
            self.assertIsNotNone(continue_history[0], "Continue history should be updated")

            # Verify the send button was NOT pressed (DOM manipulation should not occur)
            mock_press.assert_not_called()


if __name__ == "__main__":
    unittest.main()
