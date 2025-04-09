#!/usr/bin/env python3
"""
Test script that simulates the log.warning usage in the cli.py module.
"""

import sys
import os
import logging
import time

from refined_claude.logging import init_logging

def main():
    """Simulate the cli.py warning patterns."""
    # Initialize logging with our custom handlers and filters
    init_logging()

    # Get a logger
    log = logging.getLogger(__name__)

    print("Simulating log.warning calls from different locations in cli.py...")

    # Simulate a keyboard error warning (line 208 in cli.py)
    for i in range(3):
        log.warning(f"Error reading keyboard input: Simulated error {i}")
        time.sleep(0.5)

    # Simulate unrecognized message warning (line 442 in cli.py)
    for i in range(3):
        log.warning(f"unrecognized message test {i}")
        time.sleep(0.5)

    # Simulate can't find textarea warning (line 453 in cli.py)
    for i in range(3):
        log.warning(f"Can't find textarea: message {i}")
        time.sleep(0.5)

    # Simulate no send button warning (line 476 in cli.py)
    for i in range(3):
        log.warning("No send button found, skipping auto-continue")
        time.sleep(0.5)

    # Simulate unrecognized para role warning (line 634 in cli.py)
    for i in range(3):
        log.warning(f"unrecognized para role {i}")
        time.sleep(0.5)

    # Simulate unrecognized message warning at a different line (line 694 in cli.py)
    for i in range(3):
        log.warning(f"unrecognized message variant {i}")
        time.sleep(0.5)

    # Simulate could not find chat content element (line 706 in cli.py)
    for i in range(3):
        log.warning("Could not find chat content element")
        time.sleep(0.5)

    print("\nDone. Each warning type should have appeared exactly once.")

if __name__ == "__main__":
    main()
