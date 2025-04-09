#!/usr/bin/env python3
"""
Test script for the once-only warning functionality.
"""

import sys
import os
import logging

from refined_claude.logging import init_logging

def main():
    """Test the once-only warning functionality."""
    # Initialize logging with our custom handlers and filters
    init_logging()

    # Get a logger
    log = logging.getLogger(__name__)

    print("Testing once-only warnings:")
    print("===========================")

    # First warning at this line should appear
    log.warning("This warning should appear (first occurrence at line %d)", 20)
    # Second warning at the same line should be filtered out
    log.warning("This warning should NOT appear (second occurrence at line %d)", 22)

    # Warning from a different line should appear
    log.warning("This warning should appear (different line %d)", 25)

    # Different message at same line as first warning should still be filtered out
    log.warning("This warning has different text but should NOT appear (same line as first)")

    print("\nInfo messages should always appear:")
    print("=================================")

    # Info messages should always appear regardless of duplication
    log.info("This info message should always appear (line %d)", 34)
    log.info("This info message should always appear too (line %d)", 35)

    print("\nDone.")

if __name__ == "__main__":
    main()
