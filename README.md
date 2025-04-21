# Sublime Claude

A TypeScript project for testing Chrome extension PageStateMatcher against rrweb recordings.

## Project Overview

This project demonstrates how to test Chrome extension content matchers without a full browser environment. It uses:

- **happy-dom**: A lightweight DOM implementation for Node.js
- **rrweb**: For recording and replaying web sessions
- **TypeScript**: For type safety and modern development experience
- **Jest**: For testing

## Features

- Shared code between Chrome extension and testing environment
- Custom implementation of Chrome's `PageStateMatcher` for testing
- Utilities to load and process rrweb recordings
- Test framework to verify matchers against recorded DOM states

## Project Structure

```
├── src/
│   ├── matchers/                 # Matchers implementations
│   │   ├── pageStateMatcher.ts   # Mock of Chrome's PageStateMatcher
│   │   └── index.ts
│   ├── utils/                    # Utility functions
│   │   ├── rrwebPlayer.ts        # rrweb recording loader and processor
│   │   └── index.ts
│   ├── extension/                # Chrome extension files
│   │   ├── background.ts         # Extension background script
│   │   └── manifest.json         # Extension manifest
│   ├── __tests__/                # Test files
│   │   └── pageStateMatcher.test.ts
│   ├── rules.ts                  # Shared rule definitions
│   └── index.ts                  # Main entry point
├── testdata/                     # rrweb recordings
│   └── approve-tool.json         # Recording of dialog popup
├── tsconfig.json                 # TypeScript configuration
├── jest.config.js                # Jest configuration
└── package.json                  # Project dependencies
```

## Getting Started

### Installation

```bash
npm install
```

### Running Tests

```bash
npm test
```

### Building the Extension

```bash
npm run build
```

## How It Works

1. The `PageStateMatcher` class mimics Chrome's API for matching DOM states
2. The `rrwebPlayer` utilities load rrweb recordings and process them into a virtual DOM
3. Tests verify that our matchers correctly identify the dialog in the recording
4. The same matcher code is used in both the extension and tests

## Use Cases

- Testing Chrome extension content scripts without a browser
- Verifying CSS selectors against recorded DOM states
- Sharing code between extension and testing environments
