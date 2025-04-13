from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional
from .accessibility import HAX

log = logging.getLogger(__name__)


@dataclass
class MessageInfo:
    """Represents a parsed message from the chat content."""
    type: str  # "user" or "assistant"
    content: List[str]  # List of parsed paragraphs
    hit_max_length: bool = False  # Whether this is a max length message


class UnrecognizedElementError(Exception):
    """Raised when an unrecognized element is encountered in strict mode."""
    pass


def parse_content_element(content_element, strict: bool = False):
    """Parse content element once and return structured data.

    This function unifies the parsing logic used by multiple features.

    Args:
        content_element: The HAX element containing the chat messages
        strict: When True, raises UnrecognizedElementError for unrecognized elements
               instead of issuing a warning

    Returns:
        List[MessageInfo]: List of parsed messages with metadata

    Raises:
        UnrecognizedElementError: When strict=True and an unrecognized element is found
    """
    if content_element is None:
        return []

    messages = content_element.children
    parsed_messages = []

    for i, message in enumerate(messages):
        # Skip certain message types
        match message:
            case HAX(role=""):
                log.debug("skipping no-role element %s", i)
                continue

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
                    content_blocks.append("\n".join(parse_para(para, strict=strict)))

                # Check if this is a max length message
                hit_max_length = False
                if message.children:  # Only check the last child if there are children
                    match message.children[-1]:
                        case HAX(
                            children=[
                                HAX(
                                    role="AXStaticText",
                                    value=value,
                                )
                            ]
                        ) if "hit the max length for a message" in value:
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
                    content_blocks.append("\n".join(parse_para(para, strict=strict)))

                parsed_messages.append(
                    MessageInfo(
                        type="user",
                        content=content_blocks,
                        hit_max_length=False,
                    )
                )

            # Some harmless things to skip, they tend to show up when you
            # switch tabs, these might be the loading elements
            case HAX(dom_class_list={"relative": True}):
                continue

            case HAX(dom_class_list={"sticky": True}):
                continue

            case HAX(dom_class_list={"h-full": True}):
                continue

            case HAX(role=""):
                log.debug("skipping no-role element %s", i)
                continue

            # Unrecognized message
            case _:
                error_msg = f"unrecognized message '{message.role}' {message.repr(2)}"
                if strict:
                    raise UnrecognizedElementError(error_msg)
                else:
                    log.warning(error_msg)
                    parsed_messages.append(
                        MessageInfo(
                            type="unknown",
                            content=[message.inner_text()],
                            hit_max_length=False,
                        )
                    )

    return parsed_messages


def parse_para(para, strict: bool = False):
    """Parse a paragraph into lines, handling lists as well.  Conventionally
    these lines are joined together with a single newline.

    Args:
        para: The paragraph element to parse
        strict: When True, raises UnrecognizedElementError for unrecognized elements
               instead of issuing a warning

    Returns:
        List[str]: The parsed paragraph lines

    Raises:
        UnrecognizedElementError: When strict=True and an unrecognized element is found
    """
    role = para.role
    ret = []
    if role == "AXGroup":
        ret.append(para.inner_text())
    elif role == "AXList":
        is_bullet = "list-disc" in para.dom_class_list
        for i, t in enumerate(para.children):
            parsed_t = parse_para(t, strict=strict)
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
    elif role == "":
        log.debug("skipping no-role element %s", para.repr())
    else:
        error_msg = f"unrecognized {role}, {para.repr()}"
        if strict:
            raise UnrecognizedElementError(error_msg)
        else:
            log.warning(error_msg)
            ret.append(para.inner_text())
    return ret


def get_message_stats(content_element, strict: bool = False):
    """Calculate message statistics from the content element.

    Args:
        content_element: The HAX element containing the chat messages
        strict: When True, raises UnrecognizedElementError for unrecognized elements
               instead of issuing a warning

    Returns:
        tuple: (message_count, last_assistant_msg_length)

    Raises:
        UnrecognizedElementError: When strict=True and an unrecognized element is found
    """
    if content_element is None:
        return 0, 0

    parsed_messages = parse_content_element(content_element, strict=strict)
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
