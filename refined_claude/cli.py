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


def ax_traverse(parent, pred):
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


@click.command()
@click.option("--auto-approve/--no-auto-approve", default=True)
@click.option("--dry-run/--no-dry-run", default=False)
@click.option("--once/--no-once", default=False)
def cli(auto_approve: bool, dry_run: bool, once: bool):
    init_logging()
    # NB: Claude is only queried at process start (maybe an option to requery
    # every loop iteration
    apps = AppKit.NSWorkspace.sharedWorkspace().runningApplications()
    claude_apps = [
        ApplicationServices.AXUIElementCreateApplication(app.processIdentifier())
        for app in apps
        if app.localizedName() == "Claude"
    ]
    windows = [window for app in claude_apps for window in ax_attr(app, "AXWindows")]
    while True:
        log.info("Main loop iteration")
        if auto_approve:
            for window in windows:
                buttons = ax_traverse(
                    window,
                    lambda e: ax_attr(e, "AXRole", "") == "AXButton"
                    and ax_attr(e, "AXTitle", "") == "Allow for This Chat",
                )
                assert len(buttons) <= 1
                if buttons:
                    button = buttons[0]
                    log.info("Found 'Allow for this Chat' button: %s", button)
                    # TODO: allow verifying which tool is requested
                    if not dry_run:
                        HIServices.AXUIElementPerformAction(button, "AXPress")
        if once:
            return
        time.sleep(1)
