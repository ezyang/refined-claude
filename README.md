# Sublime Claude Extension

This Chrome extension automatically clicks the 'Allow for this chat' button in modal dialogs and provides notifications when Claude responses are complete.

## Features

1. **Auto-click 'Allow for this chat'** - Automatically clicks the modal dialog button
2. **Response Completion Notification** - Shows a desktop notification when Claude finishes generating a response
3. **Continue Button Auto-click** - Automatically clicks the Continue button when it appears

## Development

This is a Chrome Manifest V3 extension that uses:

- TypeScript for type safety
- tsup for bundling

### Build Instructions

The extension uses different bundling formats for its components:

1. **Background Service Worker** - Uses ES modules format as required by MV3
2. **Content Script** - Uses IIFE (Immediately Invoked Function Expression) format

To build the extension:

```bash
# From the project root
pnpm build

# Or from the extension directory
cd packages/extension
pnpm build
```

### Important Notes about MV3 and Bundling

Chrome Manifest V3 has specific requirements for JavaScript bundles:

- **Service Workers** must use ES modules format with `"type": "module"` in the manifest
- **Content Scripts** must use plain scripts (IIFE) with no imports/exports

The build configuration in `tsup.config.ts` handles this correctly with separate build configurations for each file type:

```typescript
// Background script (service worker) for MV3 - ES Module format
{
  entry: ['src/background.ts'],
  format: ['esm'],
  // ...
}

// Content script for MV3 - IIFE format (no modules)
{
  entry: ['src/index.ts'],
  format: ['iife'],
  globalName: 'SCContentScript',
  // ...
}
```

### Development Workflow

For local development with auto-reloading:

```bash
pnpm dev
```

Then load the `dist` directory as an unpacked extension in Chrome.

## Testing

Run tests with:

```bash
pnpm test
```
