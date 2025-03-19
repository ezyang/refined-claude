# refined-claude

[![PyPI](https://img.shields.io/pypi/v/refined-claude.svg)](https://pypi.org/project/refined-claude/)
[![Changelog](https://img.shields.io/github/v/release/ezyang/refined-claude?include_prereleases&label=changelog)](https://github.com/ezyang/refined-claude/releases)
[![Tests](https://github.com/ezyang/refined-claude/actions/workflows/test.yml/badge.svg)](https://github.com/ezyang/refined-claude/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/ezyang/refined-claude/blob/master/LICENSE)

Accessibility refinements to Claude Desktop

## Installation

Install this tool using `pip`:
```bash
pip install refined-claude
```
## Usage

For help, run:
```bash
refined-claude --help
```
You can also use:
```bash
python -m refined_claude --help
```
## Development

To contribute to this tool, first checkout the code. Then create a new virtual environment:
```bash
cd refined-claude
python -m venv venv
source venv/bin/activate
```
Now install the dependencies and test dependencies:
```bash
pip install -e '.[test]'
```
To run the tests:
```bash
python -m pytest
```
