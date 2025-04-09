from __future__ import annotations

import os
import logging
import xml.etree.ElementTree as ET
import threading
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

            # Counter for generating sequential IDs
            next_id = 1

            # Process all window elements directly under the root
            for window_elem in root.findall("*"):
                if window_elem.tag == "Metadata":
                    continue  # Skip metadata

                # Assign a sequential ID
                window_id = str(next_id)
                next_id += 1

                window = AXUIElement(window_id, window_elem)
                self.elements_by_id[window_id] = window
                self.root_elements.append(window)

            # Process all other elements
            self._process_element_children(root, next_id)

            log.info(f"Loaded {len(self.elements_by_id)} elements from snapshot")
        except Exception as e:
            log.error(f"Error loading snapshot: {e}")
            raise

    def _process_element_children(self, parent_xml: ET.Element, next_id: int) -> int:
        """Recursively process all child elements in the XML tree.

        Returns:
            int: The updated next_id value
        """
        for elem in parent_xml.findall("*"):
            if elem.tag == "Metadata":
                continue

            # Assign a sequential ID
            elem_id = str(next_id)
            next_id += 1

            element = AXUIElement(elem_id, elem)
            self.elements_by_id[elem_id] = element

            # Process children recursively
            next_id = self._process_element_children(elem, next_id)

        return next_id

    # Fake API implementations that mirror the actual Objective-C APIs

    def AXUIElementCopyAttributeValue(self, element: AXUIElement, attribute: str, out_value: Optional[Any] = None) -> Tuple[int, Any]:
        """Simulate AXUIElementCopyAttributeValue API call."""
        if not isinstance(element, AXUIElement):
            return kAXErrorNoValue, None

        # For AXChildren attribute, return child elements
        if attribute == "AXChildren":
            children = []
            for child in element.xml_node:
                if child.tag == "Metadata":
                    continue

                # Find the corresponding AXUIElement for this XML node
                for elem_id, elem in self.elements_by_id.items():
                    if elem.xml_node == child:
                        children.append(elem)
                        break

            return kAXErrorSuccess, children

        # For AXRole attribute, return the tag name of the XML element
        if attribute == "AXRole":
            return kAXErrorSuccess, element.xml_node.tag

        # For AXParent attribute, find the parent element
        if attribute == "AXParent":
            # Find which element has this one as a child
            for elem_id, elem in self.elements_by_id.items():
                for child in elem.xml_node:
                    # Compare XML nodes directly
                    if child == element.xml_node:
                        return kAXErrorSuccess, elem

            return kAXErrorSuccess, None  # No parent found

        # For other attributes, retrieve from XML attributes
        if attribute in element.xml_node.attrib:
            value = element.xml_node.get(attribute)

            # Handle special types
            if attribute == "AXDOMClassList":
                # Convert space-separated string (HTML-style) back to list
                return kAXErrorSuccess, value.split()

            # Handle boolean values
            if value.lower() in ("true", "false"):
                return kAXErrorSuccess, value.lower() == "true"

            return kAXErrorSuccess, value

        # If attribute is not in XML, treat as empty string for certain attributes
        # that typically default to empty strings rather than being missing
        if attribute in {"AXTitle", "AXDescription", "AXValue"}:
            return kAXErrorSuccess, ""

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
        dummy_xml = ET.Element("AXApplication")
        return AXUIElement("dummy", dummy_xml)


# Thread-local storage for API instance and state
_thread_local = threading.local()

def get_fake_api() -> FakeAccessibilityAPI:
    """Get the thread-local instance of the fake API.

    Thread-safe using thread-local storage.
    """
    if not hasattr(_thread_local, "fake_api_instance") or _thread_local.fake_api_instance is None:
        raise RuntimeError("Fake API not initialized for this thread. Call init_fake_api first.")
    return _thread_local.fake_api_instance

def init_fake_api(snapshot_path: str) -> FakeAccessibilityAPI:
    """Initialize the thread-local fake API with a snapshot file.

    Thread-safe using thread-local storage.
    """
    _thread_local.fake_api_instance = FakeAccessibilityAPI(snapshot_path)
    return _thread_local.fake_api_instance

def is_using_fake_api() -> bool:
    """Check if we're using fake APIs for testing.

    Thread-safe using thread-local storage.
    """
    return getattr(_thread_local, "use_fake_api", False)

def use_fake_api(snapshot_path: Optional[str] = None) -> None:
    """Switch to using the fake API.

    Thread-safe using thread-local storage.
    """
    _thread_local.use_fake_api = True

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
    """Switch back to using the real API.

    Thread-safe using thread-local storage.
    """
    _thread_local.use_fake_api = False

    # We'd need to restore the original functions here
    # But for simplicity, we'll rely on module reloading to restore them
