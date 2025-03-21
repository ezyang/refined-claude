import click
import Quartz
import AppKit
import ApplicationServices
import HIServices
import time
import logging
import subprocess
import json
from collections import defaultdict
from .logging import init_logging


not_set = object()
log = logging.getLogger(__name__)

# Debugging utils



def ax_dump_element(parent, depth=None):
    r = []

    def traverse(index, element, level):
        if element is None:
            return

        if ax_attr(element, "AXRole", "") == "AXStaticText":
            value = ax_attr(element, "AXValue", "(n/a)")
            r.append("_" * level + " " + str(index) + " " + value)
        else:
            r.append(
                "_" * level
                + " "
                + str(index)
                + " <"
                + ax_attr(element, "AXRole", "")
                + " "
                + ax_dump_attrs(element)
                + ">"
            )

        if depth is not None and level == depth:
            return

        children = ax_attr(element, "AXChildren", [])
        for i, child in enumerate(children):
            traverse(i, child, level + 1)

    traverse(0, parent, 0)
    return "\n".join(r)


def ax_dump_attrs(element):
    r = []
    attribute_names = ApplicationServices.AXUIElementCopyAttributeNames(element, None)
    if not attribute_names[1]:
        return ""
    for attribute in attribute_names[1]:
        if attribute not in {
            "AXTitle",
            "AXDescription",
            "AXDOMClassList",
            "AXDOMIdentifier",
        }:
            continue
        value = ApplicationServices.AXUIElementCopyAttributeValue(
            element, attribute, None
        )
        if not value[1]:
            continue
        r.append(f"{attribute}={str(value[1]).replace('\n', '')}")
    return " ".join(r)


# Utilities


class HAX:
    def __init__(self, elem):
        self.elem = elem  # underlying pyobjc

    def _get(self, name, default=not_set):
        return ax_attr(self.elem, name, default)

    @property
    def role(self):
        return self._get("AXRole")

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
        return self._get("AXWindows", "")

    @property
    def value(self):
        return self._get("AXValue", "")

    @property
    def children_by_class(self):
        ret = defaultdict(list)
        for c in self.children:
            for k in c.dom_class_list:
                ret[k].append(c)
        return ret

    def repr(self, depth):
        return ax_dump_element(self.elem, depth)

    def __repr__(self):
        return self.repr(0)

    def findall(self, pred):
        results = []

        def traverse(element):
            if element is None:
                return
            if pred(element):
                results.append(element)
            for child in element.children:
                traverse(child)

        traverse(parent)
        return results

    # TODO: children_by_XXX


def ax_attr(element, attribute, default=not_set):
    error, value = ApplicationServices.AXUIElementCopyAttributeValue(
        element, attribute, None
    )
    if error:
        if default is not not_set:
            return default
        raise ValueError(f"Error getting attribute {attribute}: {error}")
    return value


def ax_role(element):
    return ax_attr(element, "AXRole", "")


def ax_children(element):
    return ax_attr(element, "AXChildren", [])


def ax_dom_class_list(element):
    return ax_attr(element, "AXDOMClassList", [])


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


def parse_text(t):
    """Flatten element into plain text only (space separated).  Use as terminal
    rendering call; also good for debugging."""
    ret = []

    def traverse(element):
        if element is None:
            return

        if ax_role(element) == "AXStaticText":
            value = ax_attr(element, "AXValue")
            if value:
                ret.append(value)

        for child in ax_children(element):
            traverse(child)

    traverse(t)
    return "".join(ret)


def parse_para(para):
    """Parse a paragraph into lines, handling lists as well.  Conventionally
    these lines are joined together with a single newline."""
    role = ax_role(para)
    ret = []
    if role == "AXGroup":
        ret.append(parse_text(para))
    elif role == "AXList":
        is_bullet = "list-disc" in ax_dom_class_list(para)
        for i, t in enumerate(ax_children(para)):
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
    else:
        log.info("unrecognized %s", role)
        ret.append(parse_text(para))
    return ret


def parse_messages(parent):
    """Parse interleaved user/assistant messages"""
    # TODO: Make the output result more structured

    ZOOM = 1

    messages = ax_attr(parent, "AXChildren", [])
    ret = []  # messages
    for i, message in enumerate(messages):
        if i != ZOOM:
            continue
        message_classes = ax_attr(message, "AXDOMClassList", [])
        if 'group/thumbnail' in message_classes:
            log.info("skipping thumbnail at %s", i)
            continue
        #if 'group' in message_classes:
        #    inner_message = ax_children(message)[0]
        #else:
        inner_message = message
        ret_message = []  # paragraphs
        inner_message_classes = ax_attr(inner_message, "AXDOMClassList", [])
        if "w-8" in inner_message_classes:
            log.info("skipping %s message trailer", len(messages) - 1)
            break
        if "font-claude-message" in inner_message_classes:
            label = "Assistant: "
            log.info("assistant message %s", parse_text(inner_message)[:40])
            # assistant message
            for j, para in enumerate(ax_children(inner_message)):
                if "absolute" in ax_attr(para, "AXDOMClassList", []):
                    break  # message end
                ret_message.append("\n".join(parse_para(para)))
        else:
            label = "User: "
            log.info("user message %s", parse_text(inner_message)[:40])
            for j, para in enumerate(ax_children(inner_message)):
                if j == 0:
                    continue  # skip username
                if "absolute" in ax_attr(para, "AXDOMClassList", []):
                    break  # message end
                ret_message.append("\n".join(parse_para(para)))
        ret.append(label + "\n\n" + "\n\n".join(ret_message))
        if i == ZOOM:
            print("#####")
            print(ax_dump_element(message))
            break

    return "\n\n----\n\n".join(ret)


def run_auto_approve(window, dry_run):
    buttons = window.findall(lambda e: e.role == "AXButton" and e.title == "Allow for This Chat")
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


def run_notify_on_complete(window, running: list[int]):
    stop_response = ax_findall(
        window,
        lambda e: ax_attr(e, "AXRole", "") == "AXButton"
        and ax_attr(e, "AXDescription", "") == "Stop Response",
    )
    if running[0] and not stop_response:
        log.info("Detected chat response finished")
        running[0] = False
        subprocess.check_call(
            [
                "osascript",
                "-e",
                'display notification "Claude response finished" with title "Claude" sound name "Glass"',
            ]
        )
    elif not running[0] and stop_response:
        log.info("Detected chat response started")
        running[0] = True


def find_chat_content_element(window):
    window = HAX(window)
    match window:
        case HAX(children_by_class={"RootView": [
            HAX(children_by_class={"NonClientView": [
                HAX(children_by_class={"NativeFrameViewMac": [
                    HAX(children_by_class={"ClientView": [
                        HAX(children=[_, web_area])
                    ]})
                ]})
            ]})
        ]}):
            log.info("Found WebArea: %s", web_area.repr(0))
        case _:
            log.error("Couldn't find WebArea: %s", window.repr(5))
            return None

    match web_area:
        case HAX(children=[
            HAX(children_by_class={"w-full": [
                HAX(children_by_class={"relative": [
                    target_group
                ]})
            ]})
        ]):
            log.info("Found target content group: %s", target_group.repr(0))
        case _:
            log.error("Couldn't find content group: %s", web_area.repr(3))
            return None

    return target_group.elem


def run_snapshot_history(window, output_file=None):
    """Capture text content from the chat and optionally save to a file."""
    content_element = find_chat_content_element(window)
    if not content_element:
        log.info("Could not find chat content element")
        return

    log.info("Taking snapshot of chat content")
    text_content = parse_messages(content_element)

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
@click.option("--auto-approve/--no-auto-approve", default=True)
@click.option("--auto-continue/--no-auto-continue", default=True)
@click.option("--notify-on-complete/--no-notify-on-complete", default=True)
@click.option(
    "--snapshot-history",
    type=click.Path(),
    default=None,
    help="Capture chat content and save to specified file",
)
@click.option("--dry-run/--no-dry-run", default=False)
@click.option("--once/--no-once", default=False)
def cli(
    auto_approve: bool,
    auto_continue: bool,
    notify_on_complete: bool,
    snapshot_history: str,
    dry_run: bool,
    once: bool,
):
    init_logging()
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
    running = [False]
    log.info("Windows: %s", windows)

    while True:
        log.info("Start iteration")
        for window in windows:

            # TEMP
            run_snapshot_history(window, snapshot_history)
            return

            log.info("Window %s", window)
            if auto_approve:
                run_auto_approve(window, dry_run)
            if auto_continue:
                run_auto_continue(window, dry_run)
            if notify_on_complete:
                run_notify_on_complete(window, running)
            if snapshot_history:
                run_snapshot_history(window, snapshot_history)
        if once:
            return
        time.sleep(1)
