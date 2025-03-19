# refined-claude

[![PyPI](https://img.shields.io/pypi/v/refined-claude.svg)](https://pypi.org/project/refined-claude/)
[![Changelog](https://img.shields.io/github/v/release/ezyang/refined-claude?include_prereleases&label=changelog)](https://github.com/ezyang/refined-claude/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/ezyang/refined-claude/blob/master/LICENSE)

Accessibility refinements to Claude Desktop.  OS X only.

## Features

- **Auto approve.** Automatically approve tool usage requests.
- **Auto continue.** Automatically continue chats when they hit the reply
  size limit.

## Installation

Install this tool using `pip`:

```bash
uv tool install refined-claude
```

You will need to give Terminal permissions for Accessibility, if you haven't already.

## Usage

With a running instance of Claude Desktop, just run this in the background:
```bash
refined-claude
```

You can disable various features using ``--no-auto-approve`` or ``--no-auto-continue``.
