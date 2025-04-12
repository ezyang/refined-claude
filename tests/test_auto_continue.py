#!/usr/bin/env python3
"""
Test the auto-continue functionality for Claude chats that hit the reply size limit.
"""

import time
from unittest.mock import patch

# Import our modules
from refined_claude.features import run_auto_continue, check_should_continue, perform_auto_continue
from refined_claude.test_base import XMLAccessibilityTestBase


class TestAutoContinue(XMLAccessibilityTestBase):
    """Test the auto-continue functionality for Claude chats."""

    def setUp(self):
        """Set up the test environment with the XML dump."""
        self.setUp_with_xml('hit_max_length.xml', date='20250410')

    def test_check_should_continue(self):
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

        # Test that we don't continue the same message twice
        sticky_footer2 = check_should_continue(
            self.web_view, continue_history, 0, self.content_element
        )
        self.assertIsNone(sticky_footer2, "Should not continue the same message twice")

    def test_perform_auto_continue(self):
        """Test the DOM manipulation part of auto-continue."""
        # First get the sticky footer from the read-only function
        sticky_footer = check_should_continue(
            self.web_view, [None], 0, self.content_element
        )
        self.assertIsNotNone(sticky_footer, "Sticky footer should be found")

        # Test with dry_run=True to avoid actual DOM manipulation in test
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = perform_auto_continue(self.web_view, sticky_footer, True)

        # Should return False because of dry_run but still process successfully
        self.assertFalse(result, "Should return False in dry_run mode")

    def test_run_auto_continue(self):
        """Test the full auto-continue process."""
        continue_history = [None]

        # Test the combined function with dry_run=True
        with patch('time.sleep'):  # Mock sleep to speed up test
            run_auto_continue(self.web_view, True, continue_history, 0, self.content_element)

        # Verify continue_history was updated
        self.assertIsNotNone(continue_history[0], "Continue history should be updated")


if __name__ == "__main__":
    unittest.main()
