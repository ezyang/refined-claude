#!/usr/bin/env python3
"""
Base test class for accessibility tree XML-based tests.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock
import logging

# Mock the ApplicationServices and HIServices modules before importing our code
mock_ApplicationServices = MagicMock()
mock_HIServices = MagicMock()
sys.modules['ApplicationServices'] = mock_ApplicationServices
sys.modules['HIServices'] = mock_HIServices

# Import our modules
from refined_claude.fake_accessibility import init_fake_api
from refined_claude.accessibility import HAX
from refined_claude.cli import find_chat_content_element

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)


class XMLAccessibilityTestBase(unittest.TestCase):
    """Base test class for tests that use XML dumps of the accessibility tree."""

    def setUp_with_xml(self, xml_name, date="20250410", find_content_element=True):
        """Set up the test environment with the specified XML dump.

        Args:
            xml_name: Name of the XML file (without path) to use
            date: Date directory containing the XML file (format: YYYYMMDD)
            find_content_element: Whether to find the chat content element (default: True)
        """
        # Path to the XML dump of the accessibility tree
        # Move up two levels from this file to the project root
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

        # Find the content element if requested
        if find_content_element:
            self.content_element = find_chat_content_element(self.web_view)
            self.assertIsNotNone(self.content_element, "Could not find chat content element")
