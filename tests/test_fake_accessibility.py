#!/usr/bin/env python3
"""
Test the fake accessibility API implementation.
"""

import sys
import os
import unittest
import tempfile
import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock

# Add the parent directory to the Python path so we can import refined_claude modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from refined_claude.fake_accessibility import FakeAccessibilityAPI, init_fake_api, use_fake_api
from refined_claude.cli import HAX, set_using_fake_apis


class TestFakeAccessibilityAPI(unittest.TestCase):
    """Test the fake accessibility API implementation."""

    def setUp(self):
        """Create a simple XML snapshot for testing."""
        # Create a temporary XML file
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.xml', delete=False)

        # Create a sample accessibility tree
        root = ET.Element("AccessibilityTree")

        # Add metadata
        metadata = ET.SubElement(root, "Metadata")
        metadata.set("timestamp", "1234567890")
        metadata.set("app", "Claude")

        # Add a window
        window = ET.SubElement(root, "AXWindow")
        window.set("id", "1")
        window.set("AXTitle", "Claude")

        # Add a group inside the window
        group = ET.SubElement(window, "AXGroup")
        group.set("id", "2")
        group.set("AXDOMClassList", "container main-content")

        # Add a button inside the group
        button = ET.SubElement(group, "AXButton")
        button.set("id", "3")
        button.set("AXTitle", "Send")
        button.set("AXDescription", "Send message")

        # Add a text area
        text_area = ET.SubElement(group, "AXTextArea")
        text_area.set("id", "4")
        text_area.set("AXValue", "Test message")
        text_area.set("AXDOMClassList", "ProseMirror")

        # Write the XML to the temporary file
        tree = ET.ElementTree(root)
        tree.write(self.temp_file.name)
        self.temp_file.close()

        # Initialize the fake API with the snapshot
        self.fake_api = FakeAccessibilityAPI(self.temp_file.name)

    def tearDown(self):
        """Clean up temporary files."""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_loading_snapshot(self):
        """Test that the snapshot is loaded correctly."""
        # Check that elements were loaded
        self.assertEqual(len(self.fake_api.elements_by_id), 4)
        self.assertEqual(len(self.fake_api.root_elements), 1)

        # Check the root element
        root = self.fake_api.root_elements[0]
        self.assertEqual(root.xml_node.tag, "AXWindow")
        self.assertEqual(root.xml_node.get("AXTitle"), "Claude")

    def test_get_attribute(self):
        """Test getting attributes from elements."""
        # Get an element from the dictionary
        window = self.fake_api.elements_by_id["1"]

        # Test getting attributes
        error, title = self.fake_api.AXUIElementCopyAttributeValue(window, "AXTitle", None)
        self.assertEqual(error, 0)  # kAXErrorSuccess
        self.assertEqual(title, "Claude")

        # Test getting a non-existent attribute
        error, value = self.fake_api.AXUIElementCopyAttributeValue(window, "NonExistentAttribute", None)
        self.assertNotEqual(error, 0)  # Should be an error code
        self.assertIsNone(value)

    def test_get_children(self):
        """Test getting children of elements."""
        # Get the window and group elements
        window = self.fake_api.elements_by_id["1"]

        # Get the children of the window
        error, children = self.fake_api.AXUIElementCopyAttributeValue(window, "AXChildren", None)
        self.assertEqual(error, 0)  # kAXErrorSuccess
        self.assertEqual(len(children), 1)

        # Check that the child is the group
        child = children[0]
        self.assertEqual(child.xml_node.tag, "AXGroup")

        # Check the group's children
        error, group_children = self.fake_api.AXUIElementCopyAttributeValue(child, "AXChildren", None)
        self.assertEqual(error, 0)
        self.assertEqual(len(group_children), 2)

        # Check that the children are the button and text area
        child_tags = [c.xml_node.tag for c in group_children]
        self.assertIn("AXButton", child_tags)
        self.assertIn("AXTextArea", child_tags)

    def test_dom_class_list(self):
        """Test handling of AXDOMClassList attribute."""
        # Get the group element
        group = self.fake_api.elements_by_id["2"]

        # Get the AXDOMClassList attribute
        error, class_list = self.fake_api.AXUIElementCopyAttributeValue(group, "AXDOMClassList", None)
        self.assertEqual(error, 0)
        self.assertEqual(class_list, ["container", "main-content"])

    def test_set_attribute(self):
        """Test setting attributes on elements."""
        # Get the text area element
        text_area = self.fake_api.elements_by_id["4"]

        # Set the AXValue attribute
        new_value = "Updated message"
        result = self.fake_api.AXUIElementSetAttributeValue(text_area, "AXValue", new_value)
        self.assertEqual(result, 0)  # kAXErrorSuccess

        # Check that the value was updated
        error, value = self.fake_api.AXUIElementCopyAttributeValue(text_area, "AXValue", None)
        self.assertEqual(error, 0)
        self.assertEqual(value, new_value)


class TestHAXWithFakeAPI(unittest.TestCase):
    """Test that HAX works correctly with the fake API."""

    def setUp(self):
        """Set up a fake API and patch the necessary modules."""
        # Create a simple XML snapshot
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.xml', delete=False)

        root = ET.Element("AccessibilityTree")

        # Add a window with a button
        window = ET.SubElement(root, "AXWindow")
        window.set("id", "1")
        window.set("AXTitle", "Test Window")

        button = ET.SubElement(window, "AXButton")
        button.set("id", "2")
        button.set("AXTitle", "Test Button")

        tree = ET.ElementTree(root)
        tree.write(self.temp_file.name)
        self.temp_file.close()

        # Initialize the fake API
        init_fake_api(self.temp_file.name)

        # Apply the fake API
        use_fake_api()
        set_using_fake_apis(True)

    def tearDown(self):
        """Clean up and reset the API."""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

        # Reset to real API
        set_using_fake_apis(False)

    def test_hax_with_fake_api(self):
        """Test that HAX works with the fake API."""
        # Get the fake API
        from refined_claude.fake_accessibility import get_fake_api
        fake_api = get_fake_api()

        # Get the window element
        window_element = fake_api.elements_by_id["1"]

        # Create a HAX object with the fake element
        window_hax = HAX(window_element)

        # Test properties and methods
        self.assertEqual(window_hax.role, "AXWindow")
        self.assertEqual(window_hax.title, "Test Window")

        # Test children
        children = window_hax.children
        self.assertEqual(len(children), 1)

        # Test child element
        child = children[0]
        self.assertEqual(child.role, "AXButton")
        self.assertEqual(child.title, "Test Button")


if __name__ == "__main__":
    unittest.main()
