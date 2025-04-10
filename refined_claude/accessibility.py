from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, List, Optional, Dict

from .accessibility_api import (
    AccessibilityElement,
    not_set
)

log = logging.getLogger(__name__)



class HAX:
    def __init__(self, elem_or_pid, api):
        self.api = api  # Store the API reference

        # Handle the case where elem_or_pid is a process ID
        if isinstance(elem_or_pid, int):
            self.elem = self.api.AXUIElementCreateApplication(elem_or_pid)
        else:
            self.elem = elem_or_pid  # underlying accessibility element

    def _get(self, name, default=not_set):
        """Get an accessibility attribute from an element.

        This method works with both real and fake APIs, using the current API implementation.
        """
        error, value = self.api.AXUIElementCopyAttributeValue(self.elem, name, None)
        if error:
            if default is not not_set:
                return default
            raise ValueError(f"Error getting attribute {name}: {error}")
        return value

    def _dir(self):
        """Get all attribute names for this element."""
        error, attribute_names = self.api.AXUIElementCopyAttributeNames(
            self.elem, None
        )
        if error:
            return []
        return attribute_names

    @property
    def role(self):
        return self._get("AXRole", "")

    @property
    def dom_class_list(self):
        # Return a dict rather than set so we can pattern match on it
        return {k: True for k in self._get("AXDOMClassList", [])}

    @property
    def children(self):
        # Pass the API reference to child HAX objects
        return [HAX(e, self.api) for e in self._get("AXChildren", [])]

    @property
    def title(self):
        return self._get("AXTitle", "")

    @property
    def description(self):
        return self._get("AXDescription", "")

    @property
    def windows(self):
        # Pass the API reference to child HAX objects
        return [HAX(w, self.api) for w in self._get("AXWindows", [])]

    @property
    def value(self):
        return self._get("AXValue", "")

    @value.setter
    def value(self, v):
        result = self.api.AXUIElementSetAttributeValue(self.elem, "AXValue", v)
        if result != 0:
            raise RuntimeError(f"Failed to set value on {self}")

    @property
    def parent(self):
        r = self._get("AXParent", "")
        if r is not None:
            # Pass the API reference to parent HAX object
            return HAX(r, self.api)
        else:
            return None

    @property
    def children_by_class(self):
        ret = defaultdict(list)
        for c in self.children:
            for k in c.dom_class_list:
                ret[k].append(c)
        return ret

    @property
    def url(self):
        """Get the URL of the element if it has an AXURL attribute."""
        url = self._get("AXURL", None)
        return str(url) if url is not None else None

    def inner_text(self):
        """Flatten element into plain text only (space separated).  Use as terminal
        rendering call; also good for debugging."""
        ret = []

        def traverse(element):
            if element is None:
                return

            if element.role == "AXStaticText":
                value = element.value
                if value:
                    ret.append(value)

            for child in element.children:
                traverse(child)

        traverse(self)
        return "".join(ret)

    def repr(self, depth=None):
        return ax_dump_element(self, depth)

    def __repr__(self):
        return self.repr(0)

    def press(self):
        self.api.AXUIElementPerformAction(self.elem, "AXPress")

    def findall(self, pred):
        results = []

        def traverse(element):
            if element is None:
                return
            if pred(element):
                results.append(element)
            for child in element.children:
                traverse(child)

        traverse(self)
        return results


# Debugging utils
def ax_dump_element(hax_parent, depth=None):
    r = []

    def traverse(index, hax, level):
        if hax is None:
            return

        if hax.role == "AXStaticText":
            value = hax.value
            r.append("_" * level + " " + str(index) + " " + value)
        else:
            r.append(
                "_" * level
                + " "
                + str(index)
                + " <"
                + hax.role
                + " "
                + ax_dump_attrs(hax)
                + ">"
            )

        if depth is not None and level == depth:
            return

        children = hax.children
        for i, child in enumerate(children):
            traverse(i, child, level + 1)

    traverse(0, hax_parent, 0)
    return "\n".join(r)


def ax_dump_attrs(hax):
    r = []
    attribute_names = hax._dir()
    if not attribute_names:
        return ""

    for attribute in attribute_names:
        if attribute not in {
            "AXTitle",
            "AXDescription",
            "AXDOMClassList",
            "AXDOMIdentifier",
            "AXURL",
        }:
            continue

        value = hax._get(attribute, None)
        if value is None:
            continue

        r.append(f"{attribute}={str(value).replace('\n', '')}")
    return " ".join(r)


def extract_web_view(window):
    """Extract the web view from the window."""
    match window:
        case HAX(
            children_by_class={
                "RootView": [
                    HAX(
                        children_by_class={
                            "NonClientView": [
                                HAX(
                                    children_by_class={
                                        "NativeFrameViewMac": [
                                            HAX(
                                                children_by_class={
                                                    "ClientView": [
                                                        HAX(children=[_, web_area])
                                                    ]
                                                }
                                            )
                                        ]
                                    }
                                )
                            ]
                        }
                    )
                ]
            }
        ):
            log.debug("Found WebArea: %s", web_area.repr(0))
        case _:
            log.debug("Couldn't find WebArea: %s", window.repr(5))
            return None

    return web_area


def get_chat_url(web_view):
    """Check if the web view URL is a Claude chat URL."""
    import re

    url_str = web_view.url
    if url_str is not None:
        log.debug("Found WebArea URL: %s", url_str)
        if re.match(r"https://claude\.ai/chat/[0-9a-f-]+", url_str) is not None:
            return url_str
        else:
            return None
    else:
        log.warning("No AXURL attribute found in WebArea")
        return None


def find_chat_content_element(web_view):
    """Find the chat content element in the web view.

    Note: This function is called once in the main loop and its result is passed to multiple
    functions that need it, to avoid redundantly finding the same element multiple times.
    """
    match web_view:
        case (
            HAX(
                children=[
                    HAX(
                        children_by_class={
                            "relative": [
                                HAX(
                                    children_by_class={
                                        "relative": [
                                            HAX(
                                                children_by_class={
                                                    "relative": [target_group]
                                                }
                                            )
                                        ]
                                    }
                                )
                            ]
                        }
                    )
                ]
            )
            | HAX(
                children=[
                    HAX(
                        children_by_class={
                            "relative": [
                                HAX(children_by_class={"relative": [target_group]})
                            ]
                        }
                    )
                ]
            )
            | HAX(
                children_by_class={
                    "relative": [HAX(children_by_class={"relative": [target_group]})]
                }
            )
        ):
            log.debug("Found target content group: %s", target_group.repr(0))
        case _:
            log.debug("Couldn't find content group: %s", web_view.repr(3))
            return None

    return target_group
