# refined-claude

[![PyPI](https://img.shields.io/pypi/v/refined-claude.svg)](https://pypi.org/project/refined-claude/)
[![Changelog](https://img.shields.io/github/v/release/ezyang/refined-claude?include_prereleases&label=changelog)](https://github.com/ezyang/refined-claude/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/ezyang/refined-claude/blob/master/LICENSE)

Accessibility refinements to Claude Desktop.  OS X only.

## Features

- **Auto approve.** Automatically approve tool usage requests.  WARNING: MCP servers can take arbitrary actions, make sure you understand what actions your LLM may take in a chat and try to only install MCP servers which provide only safe/rollback-able operations.
- **Auto continue.** Automatically continue chats when they hit the reply
  size limit.

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

You can disable various features using ``--no-auto-approve`` or ``--no-auto-continue``. Use ``--no-default-features`` to disable all features by default (you can then selectively enable specific features as needed).

## Development

Clone the repo and install the development version tool using `pip`:

```bash
git clone https://github.com/ezyang/refined-claude.git
cd refined-claude
uv tool install . --reinstall
```

## Troubleshooting

Sometimes, refined-claude will fail to find the WebView on your open window.  This can happen if Claude is opened after you run refined-claude, or if you open refined-claude too soon after opening Claude.  Unfortunately, the most reliable way to fix this problem is to restart refined-claude.
