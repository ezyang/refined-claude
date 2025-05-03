# Chrome Extension Icons

This directory contains the icons used by the Chrome extension in various sizes:

- `icon16.png` - 16x16 pixels, used in the Chrome extension list
- `icon48.png` - 48x48 pixels, used in the Chrome Web Store
- `icon128.png` - 128x128 pixels, used in the Chrome Web Store and installation

These icons are packaged with the extension using the `publicDir` feature of tsup, which copies them to the distribution directory during the build process.

## Adding New Icons

To add or update icons:

1. Place new icon files in this directory
2. Update the `manifest.json` file if necessary
3. Run `pnpm build` from the extension directory to package them with the extension

Refer to Chrome's documentation for more details on extension icons:
https://developer.chrome.com/docs/extensions/reference/manifest/icons
