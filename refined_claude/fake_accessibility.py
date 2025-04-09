from __future__ import annotations

import os
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List, Set, Tuple, Callable, Protocol

log = logging.getLogger(__name__)

# Constants for error codes (mirroring Objective-C constants)
kAXErrorSuccess = 0
kAXErrorNoValue = -25300
kAXErrorAttributeUnsupported = -25205

class AXUIElement:
    """Fake implementation of the AXUIElement class."""
    def __init__(self, element_id: str, xml_node: ET.Element):
        self.element_id = element_id
        self.xml_node = xml_node

    def __repr__(self):
        role = self.xml_node.tag
        return f"<FakeAXUIElement id={self.element_id} role={role}>"

class FakeAccessibilityAPI:
    """A fake implementation of the macOS Accessibility APIs for testing."""

    def __init__(self, snapshot_path: str):
        """Initialize with a path to an XML snapshot file."""
        self.elements_by_id: Dict[str, AXUIElement] = {}
        self.root_elements: List[AXUIElement] = []
        self.load_snapshot(snapshot_path)

    def load_snapshot(self, snapshot_path: str):
        """Load the accessibility tree from an XML snapshot file."""
        if not os.path.exists(snapshot_path):
            raise FileNotFoundError(f"Snapshot file not found: {snapshot_path}")

        try:
            tree = ET.parse(snapshot_path)
            root = tree.getroot()

            # Process all window elements directly under the root
            for window_elem in root.findall("*"):
                if window_elem.tag == "Metadata":
                    continue  # Skip metadata

                window_id = window_elem.get("id")
                if window_id:
                    window = AXUIElement(window_id, window_elem)
                    self.elements_by_id[window_id] = window
                    self.root_elements.append(window)

            # Process all other elements
            self._process_element_children(root)

            log.info(f"Loaded {len(self.elements_by_id)} elements from snapshot")
        except Exception as e:
            log.error(f"Error loading snapshot: {e}")
            raise

    def _process_element_children(self, parent_xml: ET.Element):
        """Recursively process all child elements in the XML tree."""
        for elem in parent_xml.findall("*"):
            if elem.tag == "Metadata":
                continue

            elem_id = elem.get("id")
            if elem_id and elem_id not in self.elements_by_id:
                element = AXUIElement(elem_id, elem)
                self.elements_by_id[elem_id] = element

            self._process_element_children(elem)

    # Fake API implementations that mirror the actual Objective-C APIs

    def AXUIElementCopyAttributeValue(self, element: AXUIElement, attribute: str, out_value: Optional[Any] = None) -> Tuple[int, Any]:
        """Simulate AXUIElementCopyAttributeValue API call."""
        if not isinstance(element, AXUIElement):
            return kAXErrorNoValue, None

        # For AXChildren attribute, return child elements
        if attribute == "AXChildren":
            children = []
            for child in element.xml_node:
                child_id = child.get("id")
                if child_id and child_id in self.elements_by_id:
                    children.append(self.elements_by_id[child_id])
            return kAXErrorSuccess, children

        # For AXParent attribute, find the parent element
        if attribute == "AXParent":
            # We need to find which element has this one as a child
            for elem_id, elem in self.elements_by_id.items():
                for child in elem.xml_node:
                    if child.get("id") == element.element_id:
                        return kAXErrorSuccess, elem
            return kAXErrorSuccess, None  # No parent found

        # For other attributes, retrieve from XML attributes
        if attribute in element.xml_node.attrib:
            value = element.xml_node.get(attribute)

            # Handle special types
            if attribute == "AXDOMClassList":
                # Convert space-separated string back to list
                return kAXErrorSuccess, value.split()

            # Handle boolean values
            if value.lower() in ("true", "false"):
                return kAXErrorSuccess, value.lower() == "true"

            return kAXErrorSuccess, value

        # Handle specific attributes that might not be directly stored
        if attribute == "AXRole":
            return kAXErrorSuccess, element.xml_node.tag

        # Attribute not found
        return kAXErrorAttributeUnsupported, None

    def AXUIElementCopyAttributeNames(self, element: AXUIElement, out_names: Optional[List[str]] = None) -> Tuple[int, List[str]]:
        """Simulate AXUIElementCopyAttributeNames API call."""
        if not isinstance(element, AXUIElement):
            return kAXErrorNoValue, []

        # Get all attributes from the XML element
        attributes = list(element.xml_node.attrib.keys())

        # Add standard attributes that might not be in the attributes
        if "AXRole" not in attributes:
            attributes.append("AXRole")
        if "AXChildren" not in attributes:
            attributes.append("AXChildren")
        if "AXParent" not in attributes:
            attributes.append("AXParent")

        return kAXErrorSuccess, attributes

    def AXUIElementSetAttributeValue(self, element: AXUIElement, attribute: str, value: Any) -> int:
        """Simulate AXUIElementSetAttributeValue API call."""
        if not isinstance(element, AXUIElement):
            return kAXErrorNoValue

        # In testing, we'll update the XML node's attribute
        # For real usage, we'd just track this in memory since we can't modify XMLs at runtime
        if attribute == "AXValue":
            element.xml_node.set(attribute, str(value))
            return kAXErrorSuccess

        return kAXErrorAttributeUnsupported

    def AXUIElementPerformAction(self, element: AXUIElement, action: str) -> int:
        """Simulate AXUIElementPerformAction API call."""
        if not isinstance(element, AXUIElement):
            return kAXErrorNoValue

        # In testing, we'll just log the action
        log.info(f"Performed action {action} on element {element}")
        return kAXErrorSuccess

    def AXUIElementCreateApplication(self, pid: int) -> AXUIElement:
        """Simulate AXUIElementCreateApplication API call."""
        # In testing, just return the first root element
        if self.root_elements:
            return self.root_elements[0]

        # Create a dummy element if no root elements
        dummy_xml = ET.Element("AXApplication", {"id": "dummy"})
        return AXUIElement("dummy", dummy_xml)


# Singleton instance of the fake API
_fake_api_instance: Optional[FakeAccessibilityAPI] = None

def get_fake_api() -> FakeAccessibilityAPI:
    """Get the singleton instance of the fake API."""
    global _fake_api_instance
    if _fake_api_instance is None:
        raise RuntimeError("Fake API not initialized. Call init_fake_api first.")
    return _fake_api_instance

def init_fake_api(snapshot_path: str) -> FakeAccessibilityAPI:
    """Initialize the fake API with a snapshot file."""
    global _fake_api_instance
    _fake_api_instance = FakeAccessibilityAPI(snapshot_path)
    return _fake_api_instance

# API selector that decides whether to use real or fake API
_use_fake_api = False

def use_fake_api(snapshot_path: Optional[str] = None) -> None:
    """Switch to using the fake API."""
    global _use_fake_api
    _use_fake_api = True

    if snapshot_path:
        init_fake_api(snapshot_path)

    # Monkey patch the ApplicationServices module
    if "ApplicationServices" in globals():
        global ApplicationServices
        fake_api = get_fake_api()

        # Replace the API functions with our fake implementations
        ApplicationServices.AXUIElementCopyAttributeValue = fake_api.AXUIElementCopyAttributeValue
        ApplicationServices.AXUIElementCopyAttributeNames = fake_api.AXUIElementCopyAttributeNames

    # Monkey patch the HIServices module
    if "HIServices" in globals():
        global HIServices
        fake_api = get_fake_api()

        # Replace the API functions with our fake implementations
        HIServices.AXUIElementSetAttributeValue = fake_api.AXUIElementSetAttributeValue
        HIServices.AXUIElementPerformAction = fake_api.AXUIElementPerformAction

def use_real_api() -> None:
    """Switch back to using the real API."""
    global _use_fake_api
    _use_fake_api = False

    # We'd need to restore the original functions here
    # But for simplicity, we'll rely on module reloading to restore them
