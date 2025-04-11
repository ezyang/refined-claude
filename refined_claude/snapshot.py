from __future__ import annotations

import click
import Quartz
import AppKit
import time
import logging
import os
import sys
import xml.etree.ElementTree as ET
import xml.dom.minidom
from typing import Dict, Any, Optional, Set, List
from contextlib import contextmanager

from .accessibility import HAX
from .accessibility_api import RealAccessibilityAPI

log = logging.getLogger(__name__)

def escape_attr_value(value: str) -> str:
    """
    Escape the attribute value by replacing backslashes and newline characters
    (plus other common whitespace, if desired) with their escaped forms.
    Order is important: first escape backslashes to avoid double conversion.
    """
    # Escape backslashes.
    value = value.replace('\\', '\\\\')
    # Escape newline, carriage return, and tab characters.
    value = value.replace('\n', '\\n')
    value = value.replace('\r', '\\r')
    value = value.replace('\t', '\\t')
    return value

# Define which attributes we want to capture in our snapshot
# These should cover all attributes used in the application
ATTRIBUTES_TO_CAPTURE = {
    "AXValue",
    "AXTitle",
    "AXDescription",
    "AXDOMClassList",
    "AXDOMIdentifier",
    "AXURL",
}

def create_element_xml(element: HAX, element_id: int) -> ET.Element:
    """Convert a HAX element to an XML element with attributes."""
    # Create XML element with the role as the tag name
    role = element.role or "Unknown"
    xml_element = ET.Element(role)  # No longer adding id attribute

    # Add attributes used in our application
    attribute_names = element._dir()

    for attr_name in attribute_names:
        if attr_name not in ATTRIBUTES_TO_CAPTURE:
            continue

        value = element._get(attr_name, None)
        if value is None:
            continue

        # Skip empty string values
        if isinstance(value, str) and value == "":
            continue

        # Convert various types to string representation suitable for XML
        if attr_name == "AXDOMClassList":
            # Convert all elements to strings
            class_list = [str(cls) for cls in value]

            if not class_list:
                continue

            # Validate that no class contains spaces (which would break the format)
            for class_name in class_list:
                if ' ' in class_name:
                    log.warning(f"Class '{class_name}' contains spaces, which may cause parsing issues")
                    assert ' ' not in class_name, f"Class name '{class_name}' contains spaces"

            # Join classes with spaces as typically done in HTML/CSS
            xml_element.set(attr_name, escape_attr_value(" ".join(class_list)))
        elif isinstance(value, (str, int, float, bool)):
            # Basic types can be converted directly to strings and escaped
            xml_element.set(attr_name, escape_attr_value(str(value)))
        else:
            # For other types, use a simple string representation and escape
            try:
                xml_element.set(attr_name, escape_attr_value(str(value)))
            except Exception as e:
                log.warning(f"Could not convert {attr_name} to string: {e}")

    return xml_element

def traverse_accessibility_tree(element: HAX, parent_xml: ET.Element, element_id_counter: Dict[str, int]) -> None:
    """Recursively traverse the accessibility tree and build XML representation."""
    if element is None:
        return

    # Generate a unique ID for this element (for internal tracking only)
    element_id = element_id_counter["next"]
    element_id_counter["next"] += 1

    # Create XML element for current accessibility element
    xml_element = create_element_xml(element, element_id)
    parent_xml.append(xml_element)

    # Process children
    children = element.children
    for child in children:
        traverse_accessibility_tree(child, xml_element, element_id_counter)

def dump_accessibility_tree(app: HAX) -> ET.Element:
    """Dump the entire accessibility tree from the root node."""
    # Create root XML element
    root = ET.Element("AccessibilityTree")

    # Add metadata
    metadata = ET.SubElement(root, "Metadata")
    metadata.set("timestamp", str(int(time.time())))
    metadata.set("app", "Claude")

    # Counter for generating unique element IDs
    element_id_counter = {"next": 1}

    # Start traversal from app windows
    for window in app.windows:
        window_element = create_element_xml(window, element_id_counter["next"])
        element_id_counter["next"] += 1
        root.append(window_element)

        # Traverse all children
        for child in window.children:
            traverse_accessibility_tree(child, window_element, element_id_counter)

    return root

def pretty_print_xml(element: ET.Element) -> str:
    """Convert XML element to a nicely formatted string."""
    rough_string = ET.tostring(element, 'utf-8')
    reparsed = xml.dom.minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def find_claude_app() -> Optional[HAX]:
    """Find the Claude application if it's running."""
    api = RealAccessibilityAPI()
    apps = AppKit.NSWorkspace.sharedWorkspace().runningApplications()
    claude_apps = [
        HAX(app.processIdentifier(), api)
        for app in apps
        if app.localizedName() == "Claude"
    ]

    if not claude_apps:
        return None

    return claude_apps[0]

@click.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="claude_accessibility_snapshot.xml",
    help="Output file path for the accessibility tree snapshot",
)
@click.option(
    "--verbose/--no-verbose",
    default=False,
    help="Show debug log messages",
)
def snapshot_command(output: str, verbose: bool):
    """Create a snapshot of the Claude application's accessibility tree."""
    # Configure logging
    logging_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Find Claude application
    log.info("Looking for Claude application...")
    claude_app = find_claude_app()

    if claude_app is None:
        log.error("Claude application not found. Is it running?")
        sys.exit(1)

    log.info("Claude application found, creating accessibility tree snapshot...")

    # Create the snapshot
    root = dump_accessibility_tree(claude_app)

    # Save to file
    xml_string = pretty_print_xml(root)
    with open(output, "w", encoding="utf-8") as f:
        f.write(xml_string)

    log.info(f"Accessibility tree snapshot saved to {output}")
