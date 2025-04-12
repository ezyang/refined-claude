# refined-claude

[![PyPI](https://img.shields.io/pypi/v/refined-claude.svg)](https://pypi.org/project/refined-claude/)
[![Changelog](https://img.shields.io/github/v/release/ezyang/refined-claude?include_prereleases&label=changelog)](https://github.com/ezyang/refined-claude/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/ezyang/refined-claude/blob/master/LICENSE)

Accessibility refinements to Claude Desktop.  OS X only.

## Features

- **Auto approve.** Automatically approve tool usage requests.  WARNING: MCP servers can take arbitrary actions, make sure you understand what actions your LLM may take in a chat and try to only install MCP servers which provide only safe/rollback-able operations.
- **Auto continue.** Automatically continue chats when they hit the reply
  size limit.
- **Once-only warnings.** Warning messages are only shown once per file location to reduce log noise.
- **Snapshot accessibility tree.** Create a snapshot of the Claude application's accessibility tree for testing purposes.

## Installation

Install this tool using `pip`:

```bash
uv tool install refined-claude
```

You will need to give Terminal permissions for Accessibility, if you haven't already. (System Settings -> Privacy & Security -> Accessibility -> +)

## Usage

With a running instance of Claude Desktop, just run this in the background:
```bash
refined-claude
```
Or explicitly with the run subcommand:
```bash
refined-claude run
```

The CLI defaults to the 'run' command when no subcommand is specified.

You can disable various features using ``--no-auto-approve`` or ``--no-auto-continue``. Use ``--no-default-features`` to disable all features by default (you can then selectively enable specific features as needed).

### Creating Accessibility Snapshots

To create a snapshot of the Claude application's accessibility tree for testing:

```bash
refined-claude snapshot --output snapshot.xml
```

### Running in Test Mode

You can run the application in test mode using a previously created snapshot:

```bash
refined-claude run --test-mode snapshot.xml
```

This allows testing the application without requiring the real Claude application to be running.

## Development

Clone the repo and install the development version tool using `pip`:

```bash
git clone https://github.com/ezyang/refined-claude.git
cd refined-claude
uv tool install . --reinstall
```

### Testing

To run the tests:

```bash
# Using pytest
pip install pytest pytest-xdist
pytest

# Or using the provided test command
test
```

#### Testing with Fake Accessibility APIs

The application includes a testing infrastructure that allows you to test functionality without requiring the real Claude application to be running. It works by:

1. Creating a snapshot of the Claude application's accessibility tree using the `snapshot` command
2. Using this snapshot with a fake implementation of the Accessibility APIs

To create a test that uses this infrastructure, see the example in `tests/test_fake_accessibility.py`.

#### Testing State Changes with Mocking

For features that rely on state changes (such as `notify_on_complete`), we use a combination of:

1. XML snapshots for the initial state
2. Mocking for simulating state changes

This approach is demonstrated in `tests/test_notify_on_complete_mocked.py`, where we:
- Use a snapshot for the initial UI state
- Mock specific functions like `check_chat_running_state` to simulate state transitions
- Test the logic that depends on these state changes

This pattern is particularly useful when testing features that respond to UI changes that are difficult to capture in static XML snapshots.

## Troubleshooting

Sometimes, refined-claude will fail to find the WebView on your open window.  This can happen if Claude is opened after you run refined-claude, or if you open refined-claude too soon after opening Claude.  Unfortunately, the most reliable way to fix this problem is to restart refined-claude.
