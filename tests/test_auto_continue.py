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

# Mock the ApplicationServices and HIServices modules before importing our code
mock_ApplicationServices = MagicMock()
mock_HIServices = MagicMock()
sys.modules['ApplicationServices'] = mock_ApplicationServices
sys.modules['HIServices'] = mock_HIServices

# Import our modules
from refined_claude.fake_accessibility import FakeAccessibilityAPI, init_fake_api
from refined_claude.accessibility import HAX
from refined_claude.features import run_auto_continue
from refined_claude.cli import find_chat_content_element

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)


class TestAutoContinue(unittest.TestCase):
    """Test the auto-approve functionality for tool use dialogs."""

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

    def test_auto_continue(self):
        content_element = find_chat_content_element(self.web_view)
        run_auto_continue(self.web_view, False, [None], 0, content_element)
        #self.fail()


if __name__ == "__main__":
    unittest.main()
