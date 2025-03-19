import click
import Quartz
import AppKit
import ApplicationServices
import HIServices
import time
import logging
from .logging import init_logging


not_set = object()
log = logging.getLogger(__name__)


def ax_attr(element, attribute, default=not_set):
    error, value = ApplicationServices.AXUIElementCopyAttributeValue(
        element, attribute, None
    )
    if error:
        if default is not not_set:
            return default
        raise ValueError(f"Error getting attribute {attribute}: {error}")
    return value


def ax_ypos(e):
    pos = str(ax_attr(e, "AXPosition", ""))
    if "y:" in pos:
        y_part = pos.split("y:")[1].split()[0]
        return float(y_part)
    else:
        return 0.0


def ax_findall(parent, pred):
    results = []

    def traverse(element):
        if element is None:
            return

        if pred(element):
            results.append(element)

        children = ax_attr(element, "AXChildren", [])
        for child in children:
            traverse(child)

    traverse(parent)
    return results


def ax_dump(element):
    attribute_names = ApplicationServices.AXUIElementCopyAttributeNames(element, None)
    for attribute in attribute_names[1]:
        value = ApplicationServices.AXUIElementCopyAttributeValue(
            element, attribute, None
        )
        print(f"{attribute}: {value[1]}")


def run_auto_approve(window, dry_run):
    buttons = ax_findall(
        window,
        lambda e: ax_attr(e, "AXRole", "") == "AXButton"
        and ax_attr(e, "AXTitle", "") == "Allow for This Chat",
    )
    assert len(buttons) <= 1
    if not buttons:
        return
    button = buttons[0]
    log.info("Found 'Allow for this Chat' button: %s", button)
    # TODO: allow verifying which tool is requested
    if dry_run:
        log.info("Stopping now because of --dry-run")
        return
    HIServices.AXUIElementPerformAction(button, "AXPress")
    log.info("Pressed button")


def run_auto_continue(window, dry_run):
    max_length_msgs = ax_findall(
        window,
        lambda e: ax_attr(e, "AXRole", "") == "AXStaticText"
        and "hit the max length for a message" in ax_attr(e, "AXValue", ""),
    )
    retry_buttons = ax_findall(
        window,
        lambda e: ax_attr(e, "AXRole", "") == "AXButton"
        and ax_attr(e, "AXTitle", "") == "Retry",
    )
    watermark = max((ax_ypos(e) for e in max_length_msgs), default=None)
    if watermark is None:
        return
    log.info("Max length y-pos watermark is %s", watermark)
    if (retries_after := sum(1 for e in retry_buttons if ax_ypos(e) > watermark)) != 1:
        log.info(
            "But there were %s Retry buttons after, so not at end of chat",
            retries_after,
        )
        return
    log.info("Found 'hit the max length' at end of chat")
    (textarea,) = ax_findall(
        window,
        lambda e: ax_attr(e, "AXRole", "") == "AXTextArea"
        and (
            parent := ax_attr(
                e,
                "AXParent",
                None
                and parent is not None
                and ax_attr(parent, "AXTitle", "") == "Write your prompt to Claude",
            )
        ),
    )
    if (contents := ax_attr(textarea, "AXValue", "")) not in (
        "",
        "Reply to Claude...\n",
    ):
        log.info("But textbox already has contents '%s', aborting", contents)
        return
    if dry_run:
        log.info("Stopping now because of --dry-run")
        return
    result = HIServices.AXUIElementSetAttributeValue(textarea, "AXValue", "Continue")
    if result != 0:
        log.info("Failed to set values: %s", result)
        return
    (send_button,) = ax_findall(
        window,
        lambda e: ax_attr(e, "AXRole", "") == "AXButton"
        and ax_attr(e, "AXDescription", "") == "Send Message",
    )
    HIServices.AXUIElementPerformAction(send_button, "AXPress")


@click.command()
@click.option("--auto-approve/--no-auto-approve", default=True)
@click.option("--auto-continue/--no-auto-continue", default=True)
@click.option("--dry-run/--no-dry-run", default=False)
@click.option("--once/--no-once", default=False)
def cli(auto_approve: bool, auto_continue: bool, dry_run: bool, once: bool):
    init_logging()
    # NB: Claude is only queried at process start (maybe add an option to
    # requery every loop iteration
    apps = AppKit.NSWorkspace.sharedWorkspace().runningApplications()
    claude_apps = [
        ApplicationServices.AXUIElementCreateApplication(app.processIdentifier())
        for app in apps
        if app.localizedName() == "Claude"
    ]
    windows = [window for app in claude_apps for window in ax_attr(app, "AXWindows")]
    while True:
        log.info("Start iteration")
        for window in windows:
            log.info("Window %s", window)
            if auto_approve:
                run_auto_approve(window, dry_run)
            if auto_continue:
                run_auto_continue(window, dry_run)
        if once:
            return
        time.sleep(1)
