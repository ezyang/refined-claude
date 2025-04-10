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

# Mock the ApplicationServices and HIServices modules before importing our code
mock_ApplicationServices = MagicMock()
mock_HIServices = MagicMock()
sys.modules['ApplicationServices'] = mock_ApplicationServices
sys.modules['HIServices'] = mock_HIServices

# Now import our modules
from refined_claude.fake_accessibility import FakeAccessibilityAPI, init_fake_api, AXUIElement
from refined_claude.accessibility import HAX
from refined_claude.accessibility_api import RealAccessibilityAPI


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
        window.set("AXTitle", "Claude")

        # Add a group inside the window
        group = ET.SubElement(window, "AXGroup")
        group.set("AXDOMClassList", "container main-content")

        # Add a button inside the group
        button = ET.SubElement(group, "AXButton")
        button.set("AXTitle", "Send")
        button.set("AXDescription", "Send message")

        # Add a text area
        text_area = ET.SubElement(group, "AXTextArea")
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
        # Check that elements were loaded (with sequential IDs)
        # We expect 4 elements (window, group, button, text_area)
        self.assertGreaterEqual(len(self.fake_api.elements_by_id), 4)
        self.assertEqual(len(self.fake_api.root_elements), 1)

        # Check the root element
        root = self.fake_api.root_elements[0]
        self.assertEqual(root.xml_node.tag, "AXWindow")
        self.assertEqual(root.xml_node.get("AXTitle"), "Claude")

    def test_get_attribute(self):
        """Test getting attributes from elements."""
        # Find the window element from the root elements
        window = self.fake_api.root_elements[0]

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
        # Get the window element from root_elements
        window = self.fake_api.root_elements[0]

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
        # Find the group element through the window
        window = self.fake_api.root_elements[0]
        error, children = self.fake_api.AXUIElementCopyAttributeValue(window, "AXChildren", None)
        group = children[0]  # The group is the first child of the window

        # Get the AXDOMClassList attribute
        error, class_list = self.fake_api.AXUIElementCopyAttributeValue(group, "AXDOMClassList", None)
        self.assertEqual(error, 0)
        self.assertEqual(class_list, ["container", "main-content"])

    def test_space_separated_dom_class_list(self):
        """Test that AXDOMClassList is properly serialized and deserialized as space-separated."""
        # Create a simple XML element with a class list attribute
        root = ET.Element("AXElement")

        # Set the class list using the HTML-style space-separated format
        root.set("AXDOMClassList", "class1 class2 some-class another-class")

        # Create a fake element with this XML
        element = AXUIElement("test-element", root)

        # Test retrieving the class list
        error, class_list = self.fake_api.AXUIElementCopyAttributeValue(element, "AXDOMClassList", None)

        # Verify it was parsed correctly
        self.assertEqual(error, 0)  # kAXErrorSuccess
        self.assertEqual(class_list, ["class1", "class2", "some-class", "another-class"])

    def test_set_attribute(self):
        """Test setting attributes on elements."""
        # Find the text area element through navigation
        window = self.fake_api.root_elements[0]
        error, window_children = self.fake_api.AXUIElementCopyAttributeValue(window, "AXChildren", None)
        group = window_children[0]
        error, group_children = self.fake_api.AXUIElementCopyAttributeValue(group, "AXChildren", None)

        # Find the text area among the children
        text_area = None
        for child in group_children:
            if child.xml_node.tag == "AXTextArea":
                text_area = child
                break

        self.assertIsNotNone(text_area, "Text area not found")

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
        """Set up a fake API."""
        # Create a simple XML snapshot
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.xml', delete=False)

        root = ET.Element("AccessibilityTree")

        # Add a window with a button
        window = ET.SubElement(root, "AXWindow")
        window.set("AXTitle", "Test Window")

        button = ET.SubElement(window, "AXButton")
        button.set("AXTitle", "Test Button")

        tree = ET.ElementTree(root)
        tree.write(self.temp_file.name)
        self.temp_file.close()

        # Create the fake API
        self.fake_api = init_fake_api(self.temp_file.name)

    def tearDown(self):
        """Clean up and reset the API flag."""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_hax_with_fake_api(self):
        """Test that HAX works with the fake API."""
        # Get the window element (first root element)
        window_element = self.fake_api.root_elements[0]

        # Create a HAX object with the fake element
        window_hax = HAX(window_element, self.fake_api)

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


class TestEmptyStringHandling(unittest.TestCase):
    """Test handling of empty string attributes in the fake API."""

    def setUp(self):
        """Set up the test with a minimal XML snapshot."""
        # Create a temporary XML file
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.xml', delete=False)

        # Create a minimal accessibility tree
        root = ET.Element("AccessibilityTree")

        # Add an element with no text attributes
        element = ET.SubElement(root, "AXElement")

        # Add an element with empty text attributes
        element_with_empty = ET.SubElement(root, "AXElement")
        element_with_empty.set("AXTitle", "")  # Empty string

        tree = ET.ElementTree(root)
        tree.write(self.temp_file.name)
        self.temp_file.close()

        # Initialize the fake API with the snapshot
        self.fake_api = init_fake_api(self.temp_file.name)

    def tearDown(self):
        """Clean up temporary files."""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

        # No need to reset the API as it's local to this test

    def test_missing_attributes_default_to_empty_string(self):
        """Test that certain missing attributes default to empty string."""
        # Get the element with no attributes (first root element)
        element = self.fake_api.root_elements[0]

        # Test retrieving text attributes that should default to empty string
        for attr in ["AXTitle", "AXDescription", "AXValue"]:
            error, value = self.fake_api.AXUIElementCopyAttributeValue(element, attr, None)
            self.assertEqual(error, 0)  # kAXErrorSuccess
            self.assertEqual(value, "")  # Should be empty string, not None or error

        # Test retrieving a non-text attribute that should not default to empty string
        error, value = self.fake_api.AXUIElementCopyAttributeValue(element, "AXURL", None)
        self.assertNotEqual(error, 0)  # Should be an error
        self.assertIsNone(value)  # Should be None


if __name__ == "__main__":
    unittest.main()
