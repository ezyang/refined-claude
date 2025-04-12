#!/usr/bin/env python3
"""
Test the auto-continue functionality for Claude chats that hit the reply size limit.
"""

import sys
import os
import unittest
import logging
import time
from unittest.mock import patch, MagicMock

# Mock the ApplicationServices and HIServices modules before importing our code
mock_ApplicationServices = MagicMock()
mock_HIServices = MagicMock()
sys.modules['ApplicationServices'] = mock_ApplicationServices
sys.modules['HIServices'] = mock_HIServices

# Import our modules
from refined_claude.fake_accessibility import FakeAccessibilityAPI, init_fake_api
from refined_claude.accessibility import HAX
from refined_claude.features import run_auto_continue, check_should_continue, perform_auto_continue
from refined_claude.cli import find_chat_content_element

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)


class TestAutoContinue(unittest.TestCase):
    """Test the auto-continue functionality for Claude chats."""

    def setUp(self):
        """Set up the test environment with the XML dump."""
        # Path to the XML dump of the accessibility tree
        xml_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', 'testdata', '20250410', 'hit_max_length.xml'
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
