#!/usr/bin/env python3
"""
Test the accessibility tree snapshot functionality.
"""

import sys
import os
import unittest
import tempfile
import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock

# Add the parent directory to the Python path so we can import refined_claude modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the ApplicationServices and HIServices modules before importing our code
mock_ApplicationServices = MagicMock()
mock_HIServices = MagicMock()
mock_AppKit = MagicMock()
mock_Quartz = MagicMock()
sys.modules['ApplicationServices'] = mock_ApplicationServices
sys.modules['HIServices'] = mock_HIServices
sys.modules['AppKit'] = mock_AppKit
sys.modules['Quartz'] = mock_Quartz

# Now import our modules
from refined_claude.snapshot import create_element_xml
from refined_claude.cli import HAX


class MockHAX:
    """Mock HAX class for testing."""

    def __init__(self, role, attributes):
        self.elem = None  # Just to satisfy the HAX API
        self._role = role
        self._attributes = attributes

    def _dir(self):
        """Return list of available attributes."""
        return list(self._attributes.keys())

    def _get(self, name, default=None):
        """Get attribute value."""
        return self._attributes.get(name, default)

    @property
    def role(self):
        """Get role."""
        return self._role


class TestSnapshot(unittest.TestCase):
    """Test the accessibility tree snapshot functionality."""

    def test_create_element_xml_omits_empty_strings(self):
        """Test that create_element_xml omits attributes with empty string values."""
        # Create a mock HAX element with various attribute types
        mock_element = MockHAX("AXButton", {
            "AXTitle": "Test Button",
            "AXDescription": "",  # Empty string that should be omitted
            "AXValue": None,      # None that should be omitted
            "AXDOMClassList": ["class1", "class2"],
            "AXURL": "https://example.com"
        })

        # Create XML element (element_id parameter is now ignored but still required)
        xml_element = create_element_xml(mock_element, 1)

        # Verify that non-empty attributes are included
        self.assertEqual(xml_element.get("AXTitle"), "Test Button")
        self.assertEqual(xml_element.get("AXDOMClassList"), "class1 class2")
        self.assertEqual(xml_element.get("AXURL"), "https://example.com")

        # Verify that empty string and None attributes are omitted
        self.assertIsNone(xml_element.get("AXDescription"))
        self.assertIsNone(xml_element.get("AXValue"))

        # Check the tag name (role)
        self.assertEqual(xml_element.tag, "AXButton")

        # Verify no id attribute is added
        self.assertIsNone(xml_element.get("id"))

    def test_create_element_xml_handles_tuple_classlist(self):
        """Test that create_element_xml correctly handles tuple AXDOMClassList."""
        # Create a mock HAX element with a tuple for AXDOMClassList
        mock_element = MockHAX("AXGroup", {
            "AXTitle": "Test Group",
            "AXDOMClassList": ("class1", "class2", "class3"),  # Tuple instead of list
        })

        # Create XML element
        xml_element = create_element_xml(mock_element, 1)

        # Verify the class list was correctly joined with spaces
        self.assertEqual(xml_element.get("AXDOMClassList"), "class1 class2 class3")
        self.assertIsNone(xml_element.get("id"))  # Ensure no id attribute

        # Create another mock with mixed types in the tuple
        mock_element2 = MockHAX("AXGroup", {
            "AXDOMClassList": (123, "class-name", True),  # Mixed types in tuple
        })

        # Create XML element
        xml_element2 = create_element_xml(mock_element2, 2)

        # Verify the class list was correctly converted to strings and joined
        self.assertEqual(xml_element2.get("AXDOMClassList"), "123 class-name True")
        self.assertIsNone(xml_element2.get("id"))  # Ensure no id attribute


if __name__ == "__main__":
    unittest.main()
