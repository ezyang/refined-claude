from __future__ import annotations

import logging
import subprocess
import time
from typing import NamedTuple, List, Optional
from contextlib import contextmanager
from .accessibility import HAX, get_chat_url
from .parsing import parse_content_element, format_messages

log = logging.getLogger(__name__)


# Track the last button press time for the "Allow for this chat" button
_last_allow_button_press_time = 0.0


class ContinueHistory(NamedTuple):
    url: str
    watermark: int


@contextmanager
def TimingSegment(segment_times, segment_code):
    """Context manager for timing code segments and recording the duration.

    Usage:
        segment_times = {}
        with TimingSegment(segment_times, 'U'):
            # Code to time

    Args:
        segment_times: Dictionary to store timing results
        segment_code: Single character code to identify the segment in the results

    Yields:
        None: The context manager doesn't provide a value, it just times the context
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = int((time.time() - start_time) * 1000)
        segment_times[segment_code] = duration


def run_auto_approve(web_view, dry_run):
    """Find and press the 'Allow for this chat' button for tool approvals.

    This optimized version uses a targeted traversal approach to find the tool approval dialog,
    then uses a limited findall only within that dialog to locate the button.
    Includes a back-off mechanism to prevent pressing the button too frequently.
    """
    global _last_allow_button_press_time

    # First, look for the dialog by using pattern matching on the parent elements
    # This is more efficient than using findall on the entire tree
    dialog = None

    # Look for the WebArea -> min-h-screen group -> bg-black group -> "Allow tool" dialog pattern
    match web_view:
        case HAX(role="AXWebArea", title="Claude"):
            for main_group in web_view.children:
                if main_group.role == "AXGroup" and "min-h-screen" in main_group.dom_class_list:
                    for modal_group in main_group.children:
                        if modal_group.role == "AXGroup" and "bg-black" in modal_group.dom_class_list:
                            for tool_dialog in modal_group.children:
                                if (tool_dialog.role == "AXGroup" and
                                    tool_dialog.title and
                                    tool_dialog.title.startswith("Allow tool")):
                                    dialog = tool_dialog
                                    log.debug("Found tool approval dialog using pattern matching")
                                    break

    # If dialog is found, look for the button only within the dialog
    if not dialog:
        log.debug("Dialog not found")
        return

    # Limit the search to the found dialog
    buttons = dialog.findall(
        lambda e: e.role == "AXButton" and e.title == "Allow for this chat"
    )
    if not buttons:
        log.warning("Button not found: %s", dialog.repr())
        return

    # Check if enough time has elapsed since the last button press
    current_time = time.time()
    elapsed_time = (current_time - _last_allow_button_press_time) * 1000  # Convert to milliseconds

    if elapsed_time < 1000:  # 1s back-off period
        log.debug("Skipping button press, too soon after previous press (%.2f ms elapsed)", elapsed_time)
        return

    button = buttons[0]
    log.info("Found 'Allow for this chat' button using optimized search")

    # Check if we're in dry-run mode
    if dry_run:
        log.info("Stopping now because of --dry-run")
        return

    # Update the last button press time and press the button
    _last_allow_button_press_time = current_time
    button.press()
    log.info("Pressed button")


def run_auto_continue(web_view, dry_run, continue_history, index, content_element):
    """Auto-continue Claude chats when they hit the reply size limit.

    Uses targeted traversal to find the textarea and send button, which is more
    efficient than using findall on the entire tree.
    """

    parsed_messages = parse_content_element(content_element)
    should_continue = False

    # Find the last hit_max_length message
    for i, message in enumerate(parsed_messages):
        if message.type == "assistant" and message.hit_max_length:
            log.debug(
                "assistant: hit the max length (%s, %s)",
                i,
                continue_history[index],
            )
            chat_url = get_chat_url(web_view)
            if (
                continue_history[index] is None
                or continue_history[index].url != chat_url
                or i > continue_history[index].watermark
            ):
                should_continue = True
                continue_history[index] = ContinueHistory(
                    url=chat_url, watermark=i
                )
            else:
                log.debug(
                    "...but we already attempted to continue this index, bail"
                )
                should_continue = False
        elif message.type == "assistant":
            log.debug("assistant: message")
            should_continue = False
        elif message.type == "user":
            log.debug("user: message")
            should_continue = False

    if not should_continue:
        log.debug("Trailing continue not found, all done")
        return
    log.info("Found 'hit the max length' at end of chat")

    # Find textarea and send button using pattern matching instead of findall
    textarea = None
    send_button = None

    # First find the sticky footer - this is a key pattern we can see in both run_notify_on_complete
    # and in the path information
    sticky_footer = None
    for child in content_element.children:
        match child:
            case HAX(role="AXGroup", dom_class_list=classes) if "sticky" in classes and "bottom-0" in classes:
                sticky_footer = child
                log.debug("Found sticky footer area by class")
                break

    if not sticky_footer:
        log.warning("Can't find sticky footer area")
        return

    # Find the input container with the textarea
    for child in sticky_footer.children:
        match child:
            case HAX(role="AXGroup") as input_container:
                # Look for the textarea in this container
                # First find the rounded container that holds the textarea
                for group in input_container.children:
                    match group:
                        case HAX(role="AXGroup", dom_class_list=classes) if "rounded-2xl" in classes:
                            # Once we find the rounded container, navigate to the ProseMirror textarea
                            # The path shows multiple nested containers, we need to go through each
                            for sub_group in group.children:
                                # The relative container
                                match sub_group:
                                    case HAX(role="AXGroup", dom_class_list=classes) if "relative" in classes:
                                        # The overflow container
                                        for overflow_container in sub_group.children:
                                            match overflow_container:
                                                case HAX(role="AXGroup", dom_class_list=classes) if "overflow-y-auto" in classes:
                                                    # Finally look for the ProseMirror textarea
                                                    for text_area in overflow_container.children:
                                                        match text_area:
                                                            case HAX(role="AXTextArea", dom_class_list=classes) if "ProseMirror" in classes:
                                                                textarea = text_area
                                                                log.debug("Found ProseMirror textarea using pattern matching")
                                                                break

    # If we couldn't find the textarea with pattern matching, fall back to findall
    if not textarea:
        log.warning(
            "Can't find textarea: %s",
            "\n".join(
                [e.repr() for e in web_view.findall(lambda e: e.role == "AXTextArea")]
            ),
        )
        return

    if (contents := textarea.value) not in (
        "",
        "Continue",
        "Reply to Claude...\n",
    ):
        log.info("But textbox already has contents '%s', aborting", contents)
        return
    textarea.value = "Continue"

    # Look for send button in the sticky footer
    # This approach is similar to how run_notify_on_complete finds buttons
    match sticky_footer.children:
        case [HAX(children=[HAX(children=[*_, HAX(children=[HAX(role="AXButton", description="Send message") as button])])])]:
            send_button = button

    if not send_button:
        log.warning("No send button found, skipping auto-continue")
        return

    if dry_run:
        log.info("Stopping now because of --dry-run")
        return

    send_button.press()
    log.info("Auto-continue triggered!")


def run_notify_on_complete(web_view, running: list[int], i: int, content_element):
    """Find the Stop Response button and track chat completion state.

    This optimized version uses a targeted traversal approach to find the
    Stop Response button at the expected position in the UI hierarchy.

    Args:
        web_view: The web view element
        running: List tracking the running state of each window
        i: The index of the current window
        content_element: Pre-found chat content element (optional)
    """
    # Use the provided content_element if available, otherwise don't check for stop button
    stop_button = None

    # Look for sticky footer by class rather than position
    sticky_footer = None
    for child in content_element.children:
        match child:
            case HAX(role="AXGroup", dom_class_list={"sticky": True, "bottom-0": True}):
                sticky_footer = child
                log.debug("Found sticky footer area by class")
                break

    if not sticky_footer:
        return

    if not sticky_footer.children:
        log.warning("Sticky footer has no children")
        return

    # Match first child as input container
    match sticky_footer.children[0]:
        case HAX(role="AXGroup") as input_container:

            if input_container.children:
                # Match first child as button container
                match input_container.children[0]:
                    case HAX(role="AXGroup") as button_container:

                        # Look for Stop Response button among the button container's children
                        for button in button_container.children:
                            match button:
                                case HAX(role="AXButton", description="Stop response"):
                                    stop_button = button
                                    log.debug("Found Stop Response button using targeted traversal")
                                    break

    # Process the button state
    if running[i] and not stop_button:
        log.info("Detected chat response finished")
        running[i] = False
        subprocess.check_call(
            [
                "osascript",
                "-e",
                'display notification "Claude response finished" with title "Claude" sound name "Glass"',
            ]
        )
    elif not running[i] and stop_button:
        log.info("Detected chat response started")
        running[i] = True


def run_snapshot_history(content_element, output_file=None):
    """Capture text content from the chat and optionally save to a file."""

    log.debug("Taking snapshot of chat content")
    parsed_messages = parse_content_element(content_element)
    text_content = format_messages(parsed_messages)

    if text_content:
        log.info("Captured %d text", len(text_content))

        if output_file:
            try:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                with open(output_file, "w") as f:
                    f.write(text_content)
                log.info("Saved snapshot to %s", output_file)
            except Exception as e:
                log.error("Failed to save snapshot: %s", e)
