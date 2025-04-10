from __future__ import annotations

import logging
from typing import Any, List, Optional, Protocol, Tuple, TypeVar, runtime_checkable

# Constants for error codes (mirroring Objective-C constants)
kAXErrorSuccess = 0
kAXErrorNoValue = -25300
kAXErrorAttributeUnsupported = -25205

# Sentinel value for "not set" parameters
not_set = object()

log = logging.getLogger(__name__)

@runtime_checkable
class AccessibilityElement(Protocol):
    """Protocol for elements in the accessibility tree."""
    pass

# Type variable for the specific type of element
T = TypeVar('T', bound=AccessibilityElement)


class AccessibilityAPI:
    """Abstract base class for accessibility API implementations."""

    def AXUIElementCopyAttributeValue(self, element: T, attribute: str, out_value: Optional[Any] = None) -> Tuple[int, Any]:
        """Get an attribute value from an accessibility element.

        Args:
            element: The accessibility element.
            attribute: The name of the attribute to retrieve.
            out_value: Optional output parameter (not used in Python implementation).

        Returns:
            A tuple containing (error_code, value).
            If an error occurs, value will be None and error_code will be non-zero.
        """
        raise NotImplementedError("Subclasses must implement this method")

    def AXUIElementCopyAttributeNames(self, element: T, out_names: Optional[List[str]] = None) -> Tuple[int, List[str]]:
        """Get the names of all attributes of an accessibility element.

        Args:
            element: The accessibility element.
            out_names: Optional output parameter (not used in Python implementation).

        Returns:
            A tuple containing (error_code, attribute_names).
            If an error occurs, attribute_names will be an empty list and error_code will be non-zero.
        """
        raise NotImplementedError("Subclasses must implement this method")

    def AXUIElementSetAttributeValue(self, element: T, attribute: str, value: Any) -> int:
        """Set an attribute value on an accessibility element.

        Args:
            element: The accessibility element.
            attribute: The name of the attribute to set.
            value: The value to set.

        Returns:
            An error code (0 = success, non-zero = error).
        """
        raise NotImplementedError("Subclasses must implement this method")

    def AXUIElementPerformAction(self, element: T, action: str) -> int:
        """Perform an action on an accessibility element.

        Args:
            element: The accessibility element.
            action: The name of the action to perform.

        Returns:
            An error code (0 = success, non-zero = error).
        """
        raise NotImplementedError("Subclasses must implement this method")

    def AXUIElementCreateApplication(self, pid: int) -> T:
        """Create an accessibility element for an application.

        Args:
            pid: The process ID of the application.

        Returns:
            An accessibility element representing the application.
        """
        raise NotImplementedError("Subclasses must implement this method")


class RealAccessibilityAPI(AccessibilityAPI):
    """Implementation that uses the real macOS Accessibility APIs."""

    def AXUIElementCopyAttributeValue(self, element: T, attribute: str, out_value: Optional[Any] = None) -> Tuple[int, Any]:
        import ApplicationServices
        return ApplicationServices.AXUIElementCopyAttributeValue(element, attribute, out_value)

    def AXUIElementCopyAttributeNames(self, element: T, out_names: Optional[List[str]] = None) -> Tuple[int, List[str]]:
        import ApplicationServices
        return ApplicationServices.AXUIElementCopyAttributeNames(element, out_names)

    def AXUIElementSetAttributeValue(self, element: T, attribute: str, value: Any) -> int:
        import HIServices
        return HIServices.AXUIElementSetAttributeValue(element, attribute, value)

    def AXUIElementPerformAction(self, element: T, action: str) -> int:
        import HIServices
        return HIServices.AXUIElementPerformAction(element, action)

    def AXUIElementCreateApplication(self, pid: int) -> T:
        import ApplicationServices
        return ApplicationServices.AXUIElementCreateApplication(pid)
