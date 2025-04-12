from __future__ import annotations

import logging
import subprocess
import time
from typing import NamedTuple, List, Optional, Tuple, Any
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
def TimingSegment(segment_times: dict, segment_code: str) -> None:
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


def find_approve_button(web_view: HAX) -> Optional[Tuple[HAX, float]]:
    """Find the 'Allow for this chat' button for tool approvals.

    This is the read-only part that locates the button without manipulating the DOM.

    Args:
        web_view: The web view element

    Returns:
        Optional[Tuple[HAX, float]]: A tuple of (button, current_time) if found, None otherwise
    """
    global _last_allow_button_press_time

    # First, look for the dialog by using pattern matching on the parent elements
    # This is more efficient than using findall on the entire tree
    dialog = None

    # Look for the WebArea -> min-h-screen group -> bg-black group -> "Allow tool" dialog pattern
    match web_view:
        case HAX(role="AXWebArea") if hasattr(web_view, "title") and "Claude" in web_view.title:
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
        return None

    # Limit the search to the found dialog
    buttons = dialog.findall(
        lambda e: e.role == "AXButton" and e.title == "Allow for this chat"
    )
    if not buttons:
        log.warning("Button not found: %s", dialog.repr())
        return None

    # Check if enough time has elapsed since the last button press
    current_time = time.time()
    elapsed_time = (current_time - _last_allow_button_press_time) * 1000  # Convert to milliseconds

    if elapsed_time < 1000:  # 1s back-off period
        log.debug("Skipping button press, too soon after previous press (%.2f ms elapsed)", elapsed_time)
        return None

    button = buttons[0]
    log.info("Found 'Allow for this chat' button using optimized search")

    return (button, current_time)


def perform_auto_approve(button: HAX, current_time: float, dry_run: bool) -> bool:
    """Press the 'Allow for this chat' button for tool approvals.

    This is the DOM manipulation part that presses the button.

    Args:
        button: The button element to press
        current_time: The current time when the button was found
        dry_run: Boolean indicating if this is a dry run (no changes)

    Returns:
        bool: True if button was pressed, False otherwise
    """
    global _last_allow_button_press_time

    # Check if we're in dry-run mode
    if dry_run:
        log.info("Stopping now because of --dry-run")
        return False

    # Update the last button press time and press the button
    _last_allow_button_press_time = current_time
    button.press()
    log.info("Pressed button")
    return True


def run_auto_approve(web_view: HAX, dry_run: bool) -> None:
    """Find and press the 'Allow for this chat' button for tool approvals.

    This optimized version uses a targeted traversal approach to find the tool approval dialog,
    then uses a limited findall only within that dialog to locate the button.
    Includes a back-off mechanism to prevent pressing the button too frequently.

    This function now delegates to two separate functions:
    1. find_approve_button: Finds the button (read-only)
    2. perform_auto_approve: Presses the button (DOM manipulation)
    """
    # First check if there's a button to approve
    button_info = find_approve_button(web_view)

    # If no button or we're throttling, exit early
    if button_info is None:
        return

    # Unpack the button and current time
    button, current_time = button_info

    # Perform the DOM manipulation to press the button
    perform_auto_approve(button, current_time, dry_run)


def check_should_continue(web_view: HAX, continue_history: List[Optional[ContinueHistory]],
                          index: int, content_element: HAX) -> Optional[HAX]:
    """Determine if a Claude chat should be continued due to hitting reply size limit.

    This is the read-only part of auto-continue that does analysis without DOM manipulation.

    Args:
        web_view: The web view element
        continue_history: List tracking history of continuations
        index: The index of the current window
        content_element: Pre-found chat content element

    Returns:
        Optional[HAX]: The sticky footer element if continuation is needed, None otherwise
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
        return None

    log.info("Found 'hit the max length' at end of chat")

    # Find the sticky footer for later use in DOM manipulation part
    sticky_footer = None
    for child in content_element.children:
        match child:
            case HAX(role="AXGroup", dom_class_list=classes) if "sticky" in classes and "bottom-0" in classes:
                sticky_footer = child
                log.debug("Found sticky footer area by class")
                break

    if not sticky_footer:
        log.warning("Can't find sticky footer area")
        return None

    return sticky_footer


def perform_auto_continue(web_view: HAX, sticky_footer: HAX, dry_run: bool) -> bool:
    """Perform the actual auto-continuation by filling the textbox and pressing submit.

    This is the DOM manipulation part of auto-continue that interacts with form elements.

    Args:
        web_view: The web view element
        sticky_footer: The sticky footer element containing the input controls
        dry_run: Boolean indicating if this is a dry run (no changes)

    Returns:
        bool: True if auto-continue was triggered, False otherwise
    """
    # Find textarea and send button using pattern matching
    textarea = None
    send_button = None

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
        return False

    if (contents := textarea.value) not in (
        "",
        "Continue",
        "Reply to Claude...\n",
    ):
        log.info("But textbox already has contents '%s', aborting", contents)
        return False

    if dry_run:
        log.info("Stopping now because of --dry-run")
        return False

    textarea.value = "Continue"
    time.sleep(0.1)  # wait for textarea contents to propagate.  TODO: tune

    # Look for send button in the sticky footer
    # This approach is similar to how run_notify_on_complete finds buttons
    match sticky_footer.children:
        case [HAX(children=[HAX(children=[*_, HAX(children=[HAX(role="AXButton", description="Send message") as button])])])]:
            send_button = button

    if not send_button:
        log.warning("No send button found, skipping auto-continue")
        return False

    send_button.press()
    log.info("Auto-continue triggered!")
    return True


def run_auto_continue(web_view: HAX, dry_run: bool,
                      continue_history: List[Optional[ContinueHistory]],
                      index: int, content_element: HAX) -> None:
    """Auto-continue Claude chats when they hit the reply size limit.

    Uses targeted traversal to find the textarea and send button, which is more
    efficient than using findall on the entire tree.

    This function now delegates to two separate functions:
    1. check_should_continue: Analyzes if auto-continuation is needed (read-only)
    2. perform_auto_continue: Fills the textbox and submits the form (DOM manipulation)
    """
    # First do the read-only analysis to determine if we should continue
    sticky_footer = check_should_continue(web_view, continue_history, index, content_element)

    # If we shouldn't continue or couldn't find the sticky footer, exit early
    if sticky_footer is None:
        return

    # If we should continue, perform the DOM manipulation
    perform_auto_continue(web_view, sticky_footer, dry_run)


def check_chat_running_state(content_element: HAX) -> bool:
    """Find the Stop Response button to determine if a chat is running.

    Args:
        content_element: The chat content element

    Returns:
        bool: True if the Stop Response button is found (chat is running),
              False otherwise (chat is not running)
    """
    stop_button = None

    # Look for sticky footer by class
    sticky_footer = None
    for child in content_element.children:
        match child:
            case HAX(role="AXGroup", dom_class_list=classes) if "sticky" in classes and "bottom-0" in classes:
                sticky_footer = child
                log.debug("Found sticky footer area by class")
                break

    if not sticky_footer:
        return False

    # Match first child as input container
    match sticky_footer.children:
        case [HAX(role="AXGroup") as input_container, *_]:
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
                                    return True

    return False


def check_notify_state(content_element: HAX, running: List[bool], i: int) -> Optional[str]:
    """Check if a notification should be sent based on chat state.

    This is the read-only part that analyzes if notification is needed.

    Args:
        content_element: Pre-found chat content element
        running: List tracking the running state of each window
        i: The index of the current window

    Returns:
        Optional[str]: Notification type if needed ('finished' or 'started'), None otherwise
    """
    # Check if the chat is running
    is_running = check_chat_running_state(content_element)

    # Determine if a state change requires notification
    if running[i] and not is_running:
        return 'finished'
    elif not running[i] and is_running:
        return 'started'

    return None


def perform_notification(notification_type: str, running: List[bool], i: int) -> bool:
    """Send a notification and update running state.

    This is the system interaction part that displays notifications and updates state.

    Args:
        notification_type: Type of notification to send ('finished' or 'started')
        running: List tracking the running state of each window
        i: The index of the current window

    Returns:
        bool: True if notification was sent, False otherwise
    """
    if notification_type == 'finished':
        log.info("Detected chat response finished")
        running[i] = False
        subprocess.check_call(
            [
                "osascript",
                "-e",
                'display notification "Claude response finished" with title "Claude" sound name "Glass"',
            ]
        )
        return True
    elif notification_type == 'started':
        log.info("Detected chat response started")
        running[i] = True
        return True

    return False


def run_notify_on_complete(web_view: HAX, running: List[bool], i: int, content_element: HAX) -> None:
    """Find the Stop Response button and track chat completion state.
    Send notifications when the chat state changes.

    This function now delegates to two separate functions:
    1. check_notify_state: Analyzes if notification is needed (read-only)
    2. perform_notification: Sends notification and updates state (system interaction)

    Args:
        web_view: The web view element
        running: List tracking the running state of each window
        i: The index of the current window
        content_element: Pre-found chat content element
    """
    # First check if a notification should be sent
    notification_type = check_notify_state(content_element, running, i)

    # If no notification needed, exit early
    if notification_type is None:
        return

    # Perform the notification
    perform_notification(notification_type, running, i)


def capture_chat_content(content_element: HAX) -> Optional[str]:
    """Capture text content from the chat.

    This is the read-only part that extracts content without file operations.

    Args:
        content_element: Pre-found chat content element

    Returns:
        Optional[str]: Formatted text content if successful, None otherwise
    """
    log.debug("Taking snapshot of chat content")
    parsed_messages = parse_content_element(content_element)
    text_content = format_messages(parsed_messages)

    if text_content:
        log.info("Captured %d text", len(text_content))
        return text_content

    return None


def save_chat_snapshot(text_content: str, output_file: Optional[str]) -> bool:
    """Save chat content to a file.

    This is the file system interaction part that saves content to disk.

    Args:
        text_content: The formatted text content to save
        output_file: Path to the file where content should be saved

    Returns:
        bool: True if saved successfully, False otherwise
    """
    if not output_file:
        return False

    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(output_file, "w") as f:
            f.write(text_content)
        log.info("Saved snapshot to %s", output_file)
        return True
    except Exception as e:
        log.error("Failed to save snapshot: %s", e)
        return False


def run_snapshot_history(content_element: HAX, output_file: Optional[str] = None) -> None:
    """Capture text content from the chat and optionally save to a file.

    This function now delegates to two separate functions:
    1. capture_chat_content: Extracts content (read-only)
    2. save_chat_snapshot: Saves content to a file (file system interaction)
    """
    # First capture the content
    text_content = capture_chat_content(content_element)

    # If no content captured or no output file specified, exit early
    if not text_content or not output_file:
        return

    # Save the content to a file
    save_chat_snapshot(text_content, output_file)
