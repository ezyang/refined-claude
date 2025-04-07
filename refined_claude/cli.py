from __future__ import annotations

import click
import Quartz
import AppKit
import ApplicationServices
import HIServices
import time
import logging
import subprocess
import json
import re
import select
import sys
import os
from typing import NamedTuple, List, Optional
from collections import defaultdict
from dataclasses import dataclass
from .logging import init_logging
from .console import console
from rich.live import Live
from rich.text import Text
from rich.console import Group
from rich.spinner import Spinner
from rich.markup import escape


not_set = object()
log = logging.getLogger(__name__)


class ContinueHistory(NamedTuple):
    url: str
    watermark: int


@dataclass
class MessageInfo:
    """Represents a parsed message from the chat content."""
    type: str  # "user" or "assistant"
    content: List[str]  # List of parsed paragraphs
    hit_max_length: bool = False  # Whether this is a max length message


# Class to manage the spinner and URL display for each window
class SpinnerURLView:
    def __init__(self, windows: List[HAX]):
        self.windows = windows
        # Use a compact single-character spinner
        self.spinners = [Spinner("line", text="") for _ in windows]
        self.urls = ["" for _ in windows]
        self.web_views = [None for _ in windows]
        self.paused = False
        # With the new implementation, we always use Enter key
        self.pause_key = "ENTER"
        # Add new fields to track message count and last assistant message length
        self.message_counts = [0 for _ in windows]
        self.last_assistant_lengths = [0 for _ in windows]

    def update_url(self, index: int, url: str):
        self.urls[index] = url if url else "Not a Claude chat"

    def update_web_view(self, index: int, web_view):
        self.web_views[index] = web_view

    def update_message_stats(self, index: int, message_count: int, last_assistant_length: int):
        self.message_counts[index] = message_count
        self.last_assistant_lengths[index] = last_assistant_length

    def toggle_pause(self):
        """Toggle the paused state"""
        self.paused = not self.paused
        return self.paused

    def __rich__(self):
        current_time = time.time()
        lines = []

        # Add pause indicator at the top if paused
        if self.paused:
            status_line = Text("⏸ PAUSED ⏸", style="bold white on red")
            status_line.append(" Press ")
            status_line.append(Text("ENTER", style="bold"))
            status_line.append(" to resume")
            lines.append(status_line)
        else:
            # Add a subtle hint about the pause key when not paused
            status_line = Text("Press ", style="dim")
            status_line.append(Text("ENTER", style="bold dim"))
            status_line.append(Text(" to pause", style="dim"))
            lines.append(status_line)

        for i, spinner in enumerate(self.spinners):
            line = Text()
            # If paused, don't animate the spinner
            if self.paused:
                line.append("○")  # Static circle instead of spinner when paused
            else:
                line.append(spinner.render(current_time))
            line.append(" ")

            # Style URL with appropriate color and underlining
            url = self.urls[i]
            if url and url != "Not a Claude chat":
                # Extract parts of the URL for sophisticated styling
                if url.startswith("https://claude.ai/chat/"):
                    # Format the URL to look more like a proper link
                    chat_id = url.split("/")[-1]

                    # Style protocol and domain
                    protocol_domain = Text("https://claude.ai", style="blue")
                    # Style path
                    path = Text("/chat/", style="blue")
                    # Style chat ID
                    id_part = Text(chat_id, style="bold blue underline")

                    # Append each styled part to the line
                    line.append(protocol_domain)
                    line.append(path)
                    line.append(id_part)
                else:
                    # For other URLs or unexpected formats, use default URL styling
                    line.append(Text(url, style="link", no_wrap=True))
            else:
                # For non-URLs
                line.append(Text(url if url else "", style="italic grey74", no_wrap=True))

            # Add message count and last assistant message length if available
            if self.message_counts[i] > 0:
                # Compact format: "12m, C:345c" instead of "12 messages, last assistant: 345 chars"
                line.append(" [")
                line.append(Text(f"{self.message_counts[i]}m", style="cyan"))

                if self.last_assistant_lengths[i] > 0:
                    line.append(", ")
                    line.append(Text(f"{self.last_assistant_lengths[i]}c", style="green"))

                line.append("]")
            elif url and url.startswith("https://claude.ai/chat/"):
                # If we have a valid Claude URL but no messages detected
                line.append(" [")
                line.append(Text("no content", style="yellow dim"))
                line.append("]")

            lines.append(line)
        return Group(*lines)


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


def ax_attr(element, attribute, default=not_set):
    error, value = ApplicationServices.AXUIElementCopyAttributeValue(
        element, attribute, None
    )
    if error:
        if default is not not_set:
            return default
        raise ValueError(f"Error getting attribute {attribute}: {error}")
    return value


# Utilities


def check_for_enter_key():
    """Check if the Enter key has been pressed.

    This is a simplified version that uses blocking input and only looks for Enter key.

    Returns:
        True if Enter was pressed, False otherwise
    """
    if not sys.stdin.isatty():
        return False

    try:
        # Check if there's data to read with a short timeout
        if select.select([sys.stdin], [], [], 0.1)[0]:
            # Read a line (until Enter is pressed)
            line = sys.stdin.readline().strip()
            return True  # Any input followed by Enter will toggle pause
    except Exception as e:
        log.warning(f"Error reading keyboard input: {e}")

    return False


class HAX:
    def __init__(self, elem):
        self.elem = elem  # underlying pyobjc

    def _get(self, name, default=not_set):
        return ax_attr(self.elem, name, default)

    def _dir(self):
        """Get all attribute names for this element."""
        error, attribute_names = ApplicationServices.AXUIElementCopyAttributeNames(
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
        # TODO: defaultdict maybe?
        return {k: True for k in self._get("AXDOMClassList", [])}

    @property
    def children(self):
        return [HAX(e) for e in self._get("AXChildren", [])]

    @property
    def title(self):
        return self._get("AXTitle", "")

    @property
    def description(self):
        return self._get("AXDescription", "")

    @property
    def windows(self):
        return [HAX(w) for w in self._get("AXWindows", "")]

    @property
    def value(self):
        return self._get("AXValue", "")

    @value.setter
    def value(self, v):
        result = HIServices.AXUIElementSetAttributeValue(self.elem, "AXValue", v)
        if result != 0:
            raise RuntimeError(f"Failed to set value on {self}")

    @property
    def parent(self):
        r = self._get("AXParent", "")
        if r is not None:
            return HAX(r)
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
    def ypos(self):
        pos = str(self._get("AXPosition", ""))
        if "y:" in pos:
            y_part = pos.split("y:")[1].split()[0]
            return float(y_part)
        else:
            return 0.0

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
        HIServices.AXUIElementPerformAction(self.elem, "AXPress")

    # TODO: caching mechanism
    # TODO: do the traversal once
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

    # TODO: children_by_XXX


# Auto approve


def run_auto_approve(web_view, dry_run):
    buttons = web_view.findall(
        lambda e: e.role == "AXButton" and e.title == "Allow for this chat"
    )
    assert len(buttons) <= 1
    if not buttons:
        return
    button = buttons[0]
    log.info("Found 'Allow for this chat' button")
    # TODO: allow verifying which tool is requested
    if dry_run:
        log.info("Stopping now because of --dry-run")
        return
    button.press()
    log.info("Pressed button")


# Auto continue


def run_auto_continue(web_view, dry_run, continue_history, index, content_element):
    """Auto-continue Claude chats when they hit the reply size limit."""

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
    textareas = web_view.findall(
        lambda e: e.role == "AXTextArea" and "ProseMirror" in e.dom_class_list
    )
    if len(textareas) != 1:
        log.warning(
            "Can't find textarea: %s",
            "\n".join(
                [e.repr() for e in web_view.findall(lambda e: e.role == "AXTextArea")]
            ),
        )
        return
    (textarea,) = textareas
    if (contents := textarea.value) not in (
        "",
        "Reply to Claude...\n",
    ):
        log.info("But textbox already has contents '%s', aborting", contents)
        return
    if dry_run:
        log.info("Stopping now because of --dry-run")
        return
    textarea.value = "Continue"
    send_buttons = web_view.findall(
        lambda e: e.role == "AXButton" and e.description == "Send Message",
    )
    if not send_buttons:
        # TODO: shift window into focus and try again
        log.warning("No send button found, skipping auto-continue")
        return
    send_button = send_buttons[0]
    send_button.press()
    log.info("Auto-continue triggered!")


# Notify on complete


def run_notify_on_complete(web_view, running: list[int], i: int):
    stop_response = web_view.findall(
        lambda e: e.role == "AXButton" and e.description == "Stop Response",
    )
    if running[i] and not stop_response:
        log.info("Detected chat response finished")
        running[i] = False
        subprocess.check_call(
            [
                "osascript",
                "-e",
                'display notification "Claude response finished" with title "Claude" sound name "Glass"',
            ]
        )
    elif not running[i] and stop_response:
        log.info("Detected chat response started")
        running[i] = True


# Snapshot history


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
            # TODO: This flashes when the Allow tool dialog shows up, maybe
            # make this an error when it's not that case
            log.debug("Couldn't find content group: %s", web_view.repr(3))
            return None

    return target_group


def parse_content_element(content_element):
    """Parse content element once and return structured data.

    This function unifies the parsing logic used by multiple features.

    Args:
        content_element: The HAX element containing the chat messages

    Returns:
        List[MessageInfo]: List of parsed messages with metadata
    """
    if content_element is None:
        return []

    messages = content_element.children
    parsed_messages = []

    for i, message in enumerate(messages):
        # Skip certain message types
        match message:
            case HAX(dom_class_list={"group/thumbnail": True}):
                log.debug("skipping thumbnail at %s", i)
                continue

            case HAX(dom_class_list={"cursor-pointer": True}):
                continue

            case HAX(dom_class_list={"p-1": True}):
                log.debug("skipping %s message trailer", len(messages) - 1)
                break

            # Assistant message
            case HAX(
                dom_class_list={"group": True},
                children_by_class={"font-claude-message": [inner]},
            ):
                # Parse the content
                content_blocks = []
                for para in inner.children:
                    if "absolute" in para.dom_class_list:
                        break  # message end
                    content_blocks.append("\n".join(parse_para(para)))

                # Check if this is a max length message
                hit_max_length = False
                if message.children:  # Only check the last child if there are children
                    match message.children[-1]:
                        case HAX(
                            children=[
                                HAX(
                                    role="AXStaticText",
                                    value="Claude hit the max length for a message and has paused its response. You can write Continue to keep the chat going.",
                                )
                            ]
                        ):
                            hit_max_length = True
                            log.debug("assistant: hit the max length (%s)", i)

                parsed_messages.append(
                    MessageInfo(
                        type="assistant",
                        content=content_blocks,
                        hit_max_length=hit_max_length,
                    )
                )

            # User message
            case (
                HAX(
                    dom_class_list={"group": True},
                    children=[HAX(role="AXStaticText"), *inners],
                )
                | HAX(
                    children=[
                        HAX(
                            dom_class_list={"group": True},
                            children=[HAX(role="AXStaticText"), *inners],
                        )
                    ]
                )
            ):
                content_blocks = []
                for para in inners:
                    if "absolute" in para.dom_class_list:
                        break  # message end
                    content_blocks.append("\n".join(parse_para(para)))

                parsed_messages.append(
                    MessageInfo(
                        type="user",
                        content=content_blocks,
                        hit_max_length=False,
                    )
                )

            # Unrecognized message
            case _:
                log.warning("unrecognized message %s", message.repr(2))
                parsed_messages.append(
                    MessageInfo(
                        type="unknown",
                        content=[message.inner_text()],
                        hit_max_length=False,
                    )
                )

    return parsed_messages


def parse_para(para):
    """Parse a paragraph into lines, handling lists as well.  Conventionally
    these lines are joined together with a single newline."""
    role = para.role
    ret = []
    if role == "AXGroup":
        ret.append(para.inner_text())
    elif role == "AXList":
        is_bullet = "list-disc" in para.dom_class_list
        for i, t in enumerate(para.children):
            parsed_t = parse_para(t)
            if not parsed_t:
                # Still generate an empty bullet
                parsed_t = [""]
            if is_bullet:
                leader = "* "
            else:
                leader = f"{i + 1}. "
            indent = " " * len(leader)
            ret.append(leader + parsed_t[0].strip())
            ret.extend(indent + x.strip() for x in parsed_t[1:])
    elif role == "AXButton":
        # Tool call button
        # TODO: this is the only place you can find out what tool was called
        ret.append(para.inner_text())
    else:
        log.warning("unrecognized %s, %s", role, para.repr())
        ret.append(para.inner_text())
    return ret


def get_message_stats(content_element):
    """Calculate message statistics from the content element.

    Args:
        content_element: The HAX element containing the chat messages

    Returns:
        tuple: (message_count, last_assistant_msg_length)
    """
    if content_element is None:
        return 0, 0

    parsed_messages = parse_content_element(content_element)
    message_count = len(parsed_messages)

    # Find the last assistant message and calculate its length
    last_assistant_msg_length = 0
    for message in reversed(parsed_messages):
        if message.type == "assistant":
            # Calculate total length of content in the message
            content_text = "\n\n".join(message.content)
            last_assistant_msg_length = len(content_text)
            break

    return message_count, last_assistant_msg_length


def format_messages(parsed_messages):
    """Format the parsed messages into a text representation.

    Args:
        parsed_messages: List of MessageInfo objects from parse_content_element

    Returns:
        str: Formatted text representation of the conversation
    """
    ret = []  # messages

    for message in parsed_messages:
        if message.type == "assistant":
            label = "Assistant: "
            content = "\n\n".join(message.content)
        elif message.type == "user":
            label = "User: "
            content = "\n\n".join(message.content)
        else:
            label = "Unknown: "
            content = "\n\n".join(message.content)

        ret.append(label + "\n\n" + content)

    return "\n\n----\n\n".join(ret)


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


@click.command()
@click.option(
    "--auto-approve/--no-auto-approve",
    default=None,
    help="Automatically approve tool usage requests (in default set)",
)
@click.option(
    "--only-auto-approve",
    is_flag=True,
    default=False,
    help="Only enable auto-approve and disable all other default features",
)
@click.option(
    "--auto-continue/--no-auto-continue",
    default=None,
    help="Automatically continue chats when they hit the reply size limit (in default set)",
)
@click.option(
    "--only-auto-continue",
    is_flag=True,
    default=False,
    help="Only enable auto-continue and disable all other default features",
)
@click.option(
    "--notify-on-complete/--no-notify-on-complete",
    default=None,
    help="Send a notification when Claude finishes responding (in default set)",
)
@click.option(
    "--only-notify-on-complete",
    is_flag=True,
    default=False,
    help="Only enable notify-on-complete and disable all other default features",
)
@click.option(
    "--snapshot-history",
    type=click.Path(),
    default=None,
    help="Capture chat content and save to specified file",
)
@click.option(
    "--only-snapshot-history",
    type=click.Path(),
    default=None,
    help="Only enable snapshot-history to specified file and disable all other default features",
)
@click.option(
    "--dry-run/--no-dry-run",
    default=False,
    help="Don't make any changes, just log what would happen",
)
@click.option(
    "--once/--no-once",
    default=False,
    help="Run once and exit instead of running continuously",
)
@click.option(
    "--default-features/--no-default-features",
    default=True,
    help="Use default values for features when not explicitly specified",
)
def cli(
    auto_approve: bool | None,
    only_auto_approve: bool,
    auto_continue: bool | None,
    only_auto_continue: bool,
    notify_on_complete: bool | None,
    only_notify_on_complete: bool,
    snapshot_history: str | None,
    only_snapshot_history: str | None,
    dry_run: bool,
    once: bool,
    default_features: bool,
):
    init_logging()

    # If --only-snapshot-history is provided, use that path for snapshot_history
    if only_snapshot_history is not None:
        snapshot_history = only_snapshot_history

    # Determine if any "only" flags are used
    any_only_flag = only_auto_approve or only_auto_continue or only_notify_on_complete or (only_snapshot_history is not None)

    # If any "only" flag is used, it overrides default_features
    if any_only_flag:
        default_features = False

    # First, determine the default state for unspecified flags
    default_state = True if default_features else False

    # Apply defaults for unspecified boolean flags
    if auto_approve is None:
        auto_approve = default_state
    if auto_continue is None:
        auto_continue = default_state
    if notify_on_complete is None:
        notify_on_complete = default_state

    # Handle the "only" flags, which override everything else when specified
    if any_only_flag:
        # Reset all features to False first
        auto_approve = False
        auto_continue = False
        notify_on_complete = False

        # Then enable only the specific feature(s) requested
        if only_auto_approve:
            auto_approve = True
        if only_auto_continue:
            auto_continue = True
        if only_notify_on_complete:
            notify_on_complete = True
        # Note: snapshot_history doesn't need special handling as it's path-based
    # Log which features are active
    active_features = []
    if auto_approve:
        active_features.append("auto-approve")
    if auto_continue:
        active_features.append("auto-continue")
    if notify_on_complete:
        active_features.append("notify-on-complete")
    if snapshot_history is not None:
        active_features.append(f"snapshot-history={snapshot_history}")

    # Pause with Enter key is always active
    active_features.append("pause-key='ENTER'")

    log.info("Active features: %s", ", ".join(active_features) if active_features else "none")

    # NB: Claude is only queried at process start (maybe add an option to
    # requery every loop iteration
    apps = AppKit.NSWorkspace.sharedWorkspace().runningApplications()
    claude_apps = [
        HAX(ApplicationServices.AXUIElementCreateApplication(app.processIdentifier()))
        for app in apps
        if app.localizedName() == "Claude"
    ]
    log.info("Apps: %s", claude_apps)
    windows = [window for app in claude_apps for window in app.windows]
    running = [False] * len(windows)
    continue_history = [None] * len(windows)
    log.info("Windows: %s", windows)

    view = SpinnerURLView(windows)

    # Start the live display
    with Live(view, console=console, refresh_per_second=8, auto_refresh=True) as live:
        while True:
            # Check for keyboard input to toggle pause state
            if check_for_enter_key():
                paused = view.toggle_pause()
                log.info(f"Pause state toggled: {'paused' if paused else 'resumed'}")

            # Skip processing if paused, but still update the display
            if view.paused:
                live.update(view)
                time.sleep(0.1)
                continue

            log.debug("Start iteration")
            for i, window in enumerate(windows):
                log.debug("Window %s", window)
                # Extract web view first
                web_view = extract_web_view(window)
                view.update_web_view(i, web_view)

                if web_view is None:
                    log.debug("Could not extract web view, skipping")
                    view.update_url(i, "No web view")
                    continue

                # Check if the URL is a Claude chat URL
                url = get_chat_url(web_view)
                view.update_url(i, url)

                if url is None:
                    log.debug("Not a Claude chat URL, skipping")
                    continue

                # Only perform operations if we have a valid web view with Claude chat URL
                # Find the chat content element once if needed
                content_element = None
                # Always find content element to get message statistics, regardless of features
                content_element = find_chat_content_element(web_view)
                if not content_element:
                    log.debug("Could not find chat content element")
                else:
                    # Calculate and update message statistics for the status bar
                    message_count, last_assistant_length = get_message_stats(content_element)
                    view.update_message_stats(i, message_count, last_assistant_length)

                # Run features that don't require content_element
                if auto_approve:
                    run_auto_approve(web_view, dry_run)
                if notify_on_complete:
                    run_notify_on_complete(web_view, running, i)

                # Run features that require content_element only if we found it
                if content_element:
                    # Parse content element once for all features that need it
                    if auto_continue:
                        run_auto_continue(web_view, dry_run, continue_history, i, content_element)
                    if snapshot_history:
                        run_snapshot_history(content_element, snapshot_history)

            # Refresh the live display with updated URLs
            live.update(view)

            if once:
                return
            time.sleep(1)
