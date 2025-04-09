#!/usr/bin/env python3
"""
Test the CLI structure to ensure subcommands are properly registered.
"""

import sys
import os
import unittest
from unittest.mock import patch
from click.testing import CliRunner

# Mock the required modules
mock_ApplicationServices = unittest.mock.MagicMock()
mock_HIServices = unittest.mock.MagicMock()
mock_AppKit = unittest.mock.MagicMock()
mock_Quartz = unittest.mock.MagicMock()

sys.modules['ApplicationServices'] = mock_ApplicationServices
sys.modules['HIServices'] = mock_HIServices
sys.modules['AppKit'] = mock_AppKit
sys.modules['Quartz'] = mock_Quartz

# Now import our CLI
from refined_claude.cli import cli


class TestCLIStructure(unittest.TestCase):
    """Test the CLI structure."""

    def setUp(self):
        """Set up the test runner."""
        self.runner = CliRunner()

    def test_cli_base_command(self):
        """Test that the CLI has the correct base command."""
        result = self.runner.invoke(cli, ['--help'])
        self.assertEqual(result.exit_code, 0)

        # Check that the base help output includes our description
        self.assertIn("Refined Claude - Improvements for Claude Desktop", result.output)

        # Check that both subcommands are listed
        self.assertIn("run", result.output)
        self.assertIn("snapshot", result.output)

    def test_run_command(self):
        """Test that the run command is registered."""
        result = self.runner.invoke(cli, ['run', '--help'])
        self.assertEqual(result.exit_code, 0)

        # Check that options are included
        self.assertIn("--auto-approve", result.output)
        self.assertIn("--auto-continue", result.output)
        self.assertIn("--test-mode", result.output)

    def test_snapshot_command(self):
        """Test that the snapshot command is registered."""
        result = self.runner.invoke(cli, ['snapshot', '--help'])
        self.assertEqual(result.exit_code, 0)

        # Check that options are included
        self.assertIn("--output", result.output)
        self.assertIn("-o", result.output)

    @patch('refined_claude.cli.run')
    def test_default_to_run_command(self, mock_run):
        """Test that the CLI defaults to the 'run' command when no subcommand is specified."""
        # Call CLI without specifying a subcommand
        result = self.runner.invoke(cli, [])

        # Verify that the run command was invoked
        self.assertEqual(result.exit_code, 0)
        mock_run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
