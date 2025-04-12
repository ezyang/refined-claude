from __future__ import annotations

import click
import AppKit
import time
import logging
from typing import Optional
from rich.live import Live

from .logging import init_logging
from .console import console
from .accessibility import HAX, extract_web_view, get_chat_url, find_chat_content_element
from .accessibility_api import RealAccessibilityAPI
from .ui import SpinnerURLView, check_for_enter_key
from .parsing import get_message_stats
from .features import (
    TimingSegment,
    run_auto_approve,
    run_auto_continue,
    run_notify_on_complete,
    run_snapshot_history,
    check_chat_running_state,
    ContinueHistory
)

log = logging.getLogger(__name__)


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Refined Claude - Improvements for Claude Desktop"""
    if ctx.invoked_subcommand is None:
        # If no subcommand is specified, run the 'run' command with default arguments
        ctx.invoke(run)


@cli.command()
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
    "--verbose/--no-verbose",
    default=False,
    help="Show debug log messages",
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
@click.option(
    "--test-mode",
    type=click.Path(exists=True),
    default=None,
    help="Run in test mode using a fake accessibility API with the specified snapshot file",
)
def run(
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
    verbose: bool,
    test_mode: str | None,
):
    init_logging(verbose)

    # Check if we're in test mode and set up the fake API if needed
    fake_api = None
    if test_mode:
        log.info(f"Running in test mode using snapshot: {test_mode}")
        from .fake_accessibility import init_fake_api
        fake_api = init_fake_api(test_mode)

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
    if test_mode:
        # We already set up the fake API earlier
        api = fake_api  # This is defined from init_fake_api in the test_mode condition above
    else:
        # Create a real API instance
        api = RealAccessibilityAPI()

    apps = AppKit.NSWorkspace.sharedWorkspace().runningApplications()
    claude_apps = [
        HAX(api.AXUIElementCreateApplication(app.processIdentifier()), api)
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
        # live.stop()
        while True:
            # Check for keyboard input to toggle pause state
            if check_for_enter_key():
                paused = view.toggle_pause()
                log.info(f"Pause state toggled: {'paused' if paused else 'resumed'}")

            # Skip processing if paused, but still update the display
            if view.paused:
                live.update(view)
                continue

            # Start timestamp for active time measurement
            iteration_start_time = time.time()

            log.debug("Start iteration")
            for i, window in enumerate(windows):
                # Dictionary to track segment times with letter codes
                segment_times = {}

                log.debug("Window %s", window)
                # Extract web view first - we don't track this timing as it's cheap
                web_view = extract_web_view(window)
                view.update_web_view(i, web_view)

                if web_view is None:
                    log.debug("Could not extract web view, skipping")
                    view.update_url(i, "No web view")
                    continue

                url = get_chat_url(web_view)
                view.update_url(i, url)

                if url is None:
                    log.debug("Not a Claude chat URL, skipping")
                    continue

                # Segment A: Auto approve
                if auto_approve:
                    with TimingSegment(segment_times, 'A'):
                        run_auto_approve(web_view, dry_run)

                # Find content element - we don't track this timing as it's cheap
                content_element = find_chat_content_element(web_view)

                # Features that require content_element
                if content_element:
                    # Segment M: Message stats
                    with TimingSegment(segment_times, 'M'):
                        message_count, last_assistant_length = get_message_stats(content_element)
                        view.update_message_stats(i, message_count, last_assistant_length)

                    # Check for running state (even if notify_on_complete is disabled)
                    with TimingSegment(segment_times, 'R'):
                        # Check if the chat is running
                        is_running = check_chat_running_state(content_element)

                        # Update running state
                        if running[i] and not is_running:
                            running[i] = False
                            log.debug("Chat is no longer running")
                        elif not running[i] and is_running:
                            running[i] = True
                            log.debug("Chat is now running")

                        # Update running state in the UI view
                        view.update_running_state(i, running[i])

                    # Segment N: Notify on complete
                    if notify_on_complete:
                        with TimingSegment(segment_times, 'N'):
                            run_notify_on_complete(web_view, running, i, content_element)

                    # Segment C: Auto continue
                    if auto_continue:
                        with TimingSegment(segment_times, 'C'):
                            run_auto_continue(web_view, dry_run, continue_history, i, content_element)

                    # Segment S: Snapshot history
                    if snapshot_history:
                        with TimingSegment(segment_times, 'S'):
                            run_snapshot_history(content_element, snapshot_history)

                # Update segment times
                view.update_segment_times(i, segment_times)

                # Calculate active time spent in milliseconds
                iteration_time_ms = int((time.time() - iteration_start_time) * 1000)
                # Update iteration time (the active processing time only)
                view.iteration_times[i] = iteration_time_ms
                # Reset the timestamp for next iteration
                view.last_iteration_timestamps[i] = time.time()

            # Refresh the live display with updated URLs
            live.update(view)

            if once:
                return

            time.sleep(0.5)


# Add the snapshot command as a subcommand of 'cli'
from .snapshot import snapshot_command
cli.add_command(snapshot_command, name="snapshot")
