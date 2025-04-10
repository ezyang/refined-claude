#!/usr/bin/env python3
"""
Test the thread safety of the fake accessibility API.

NOTE: After the refactoring to use class-based API implementations,
thread-local storage is no longer used, so this test is modified to
just verify the basic API functionality across threads.
"""

import sys
import os
import unittest
import tempfile
import xml.etree.ElementTree as ET
import threading
import time
from unittest.mock import patch, MagicMock

# Mock the ApplicationServices and HIServices modules before importing our code
mock_ApplicationServices = MagicMock()
mock_HIServices = MagicMock()
sys.modules['ApplicationServices'] = mock_ApplicationServices
sys.modules['HIServices'] = mock_HIServices

# Now import our modules
from refined_claude.fake_accessibility import init_fake_api
from refined_claude.accessibility_api import RealAccessibilityAPI


class TestMultiThreadAccess(unittest.TestCase):
    """Test that the API works correctly across multiple threads."""

    def setUp(self):
        """Create a simple XML snapshot for testing."""
        # Create a temporary XML file
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.xml', delete=False)

        # Create a minimal accessibility tree
        root = ET.Element("AccessibilityTree")
        window = ET.SubElement(root, "AXWindow")
        window.set("id", "1")

        tree = ET.ElementTree(root)
        tree.write(self.temp_file.name)
        self.temp_file.close()

        # Create a fake API instance
        self.fake_api = init_fake_api(self.temp_file.name)

    def tearDown(self):
        """Clean up temporary files."""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_multi_thread_access(self):
        """Test that each thread can access the correct API implementation."""
        # In our new design, all threads share the same API implementation
        # So this test just verifies that multiple threads can access the API

        def thread_function(thread_id, results, lock):
            api = self.fake_api

            # Verify we can access the root elements
            root_elements = getattr(api, 'root_elements', None)

            with lock:
                # Just record success/failure
                results.append((thread_id, root_elements is not None))

            # Sleep to allow thread scheduling
            time.sleep(0.01)

        # Define a list to store results from different threads
        results = []
        result_lock = threading.Lock()

        # Create and start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(
                target=thread_function,
                args=(i, results, result_lock)
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify that each thread could access the API
        for thread_id, success in results:
            self.assertTrue(success, f"Thread {thread_id} failed to access the API")

        # Verify we got results from all threads
        self.assertEqual(len(results), 10)


if __name__ == "__main__":
    unittest.main()
