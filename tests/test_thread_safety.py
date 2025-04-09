#!/usr/bin/env python3
"""
Test the thread safety of the fake accessibility API.
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
from refined_claude.fake_accessibility import init_fake_api, use_fake_api, is_using_fake_api
from refined_claude.accessibility import set_using_fake_apis, is_using_fake_apis


class TestThreadSafety(unittest.TestCase):
    """Test the thread safety of the fake accessibility API."""

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

        # Initialize the fake API with the snapshot
        init_fake_api(self.temp_file.name)

    def tearDown(self):
        """Clean up temporary files."""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_thread_local_api_mode(self):
        """Test that API mode flags are thread-local."""
        # Define a list to store results from different threads
        results = []
        result_lock = threading.Lock()

        def thread_function(thread_id):
            # Set different API modes in different threads
            if thread_id % 2 == 0:
                set_using_fake_apis(True)
                use_fake_api()
            else:
                set_using_fake_apis(False)
                # Note: We don't call use_real_api() here since it would
                # require actually loading the real modules

            # Capture the value for the current thread
            with result_lock:
                results.append((
                    thread_id,
                    is_using_fake_apis(),
                    is_using_fake_api()
                ))

            # Sleep to allow thread scheduling
            time.sleep(0.01)

        # Create and start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=thread_function, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify that each thread saw the correct values
        for thread_id, cli_using_fake, fake_using_fake in results:
            expected_fake = (thread_id % 2 == 0)
            self.assertEqual(cli_using_fake, expected_fake)
            self.assertEqual(fake_using_fake, expected_fake)


if __name__ == "__main__":
    unittest.main()
