from __future__ import annotations

import time
import select
import sys
import logging
from typing import List
from rich.text import Text
from rich.console import Group
from rich.spinner import Spinner
from .accessibility import HAX

log = logging.getLogger(__name__)


def format_time(milliseconds):
    """Format milliseconds into a human-readable string.

    Returns "Xms" for the millisecond value.

    Args:
        milliseconds: Time in milliseconds

    Returns:
        str: Formatted time string with millisecond precision
    """
    return f"{milliseconds}ms"


def check_for_enter_key():
    """Check if the Enter key has been pressed.

    This is a non-blocking version that only looks for Enter key.

    Returns:
        True if Enter was pressed, False otherwise
    """
    if not sys.stdin.isatty():
        return False

    try:
        # Check if there's data to read with no timeout (non-blocking)
        if select.select([sys.stdin], [], [], 0)[0]:
            # Read a line (until Enter is pressed)
            line = sys.stdin.readline().strip()
            return True  # Any input followed by Enter will toggle pause
    except Exception as e:
        log.warning(f"Error reading keyboard input: {e}")

    return False


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
        # Add new fields to track iteration times
        self.last_iteration_timestamps = [time.time() for _ in windows]
        self.iteration_times = [0 for _ in windows]
        # Add field to track chat running state
        self.running_states = [False for _ in windows]

    def update_url(self, index: int, url: str):
        self.urls[index] = url if url else "Not a Claude chat"

    def update_web_view(self, index: int, web_view):
        self.web_views[index] = web_view

    def update_message_stats(self, index: int, message_count: int, last_assistant_length: int):
        self.message_counts[index] = message_count
        self.last_assistant_lengths[index] = last_assistant_length

    def update_iteration_time(self, index: int):
        """Update the iteration time for the specified window."""
        current_time = time.time()
        # Store iteration time in milliseconds, excluding sleep time
        self.iteration_times[index] = int((current_time - self.last_iteration_timestamps[index]) * 1000)
        self.last_iteration_timestamps[index] = current_time

    def update_segment_times(self, index: int, segment_times: dict):
        """Update the performance breakdown for the specified window.

        Args:
            index: Window index
            segment_times: Dictionary mapping segment codes to times in milliseconds
        """
        if not hasattr(self, 'segment_times'):
            self.segment_times = [{}] * len(self.windows)
        self.segment_times[index] = segment_times

    def update_running_state(self, index: int, running: bool):
        """Update the running state for the specified window.

        Args:
            index: Window index
            running: True if the chat is running, False otherwise
        """
        self.running_states[index] = running

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
                line.append("○")  # Static empty circle when paused
            # If chat is running, show animated spinner and green indicator
            elif self.running_states[i]:
                line.append(spinner.render(current_time))
                line.append(Text(" ⟳", style="bold green"))  # Green indicator when running
            # If chat is not running, show static character
            else:
                line.append("•")  # Static dot when chat is not running
                line.append(Text(" ■", style="dim"))  # Dim square when stopped
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

            # Add message count, last assistant message length, and iteration time if available
            if self.message_counts[i] > 0:
                # Compact format: "[12m, 345c, 30s]" instead of "12 messages, last assistant: 345 chars, iteration: 30 seconds"
                line.append(" [")
                line.append(Text(f"{self.message_counts[i]}m", style="cyan"))

                if self.last_assistant_lengths[i] > 0:
                    line.append(", ")
                    line.append(Text(f"{self.last_assistant_lengths[i]}c", style="green"))

                if self.iteration_times[i] > 0:
                    line.append(", ")
                    line.append(Text(format_time(self.iteration_times[i]), style="yellow"))

                    # Add segment times if available
                    if hasattr(self, 'segment_times') and self.segment_times[i]:
                        line.append(" (")
                        segments = self.segment_times[i].items()
                        segment_texts = []
                        for code, time_ms in segments:
                            segment_texts.append(f"{code}:{time_ms}ms")
                        line.append(Text(", ".join(segment_texts), style="cyan"))
                        line.append(")")

                line.append("]")
            elif url and url.startswith("https://claude.ai/chat/"):
                # If we have a valid Claude URL but no messages detected
                line.append(" [")
                line.append(Text("no content", style="yellow dim"))
                line.append("]")

            lines.append(line)
        return Group(*lines)
