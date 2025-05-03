# Chrome Extension Asset Reorganization

This change reorganizes the Chrome extension's assets, particularly icons, to follow standard practices for Chrome extension development:

## Changes Made

1. Created a `public/images` directory to store static assets like icons

   - Follows the conventional pattern used in modern Chrome extension development
   - Makes the project structure more maintainable and scalable

2. Updated the `tsup.config.ts` to use the `publicDir` feature

   - Static assets are now automatically copied from `public` to `dist` during build
   - Added `onSuccess` hook to properly handle manifest.json
   - Ensures all assets are packaged correctly with the extension

3. Updated `manifest.json` to include proper icon references

   - Added the `icons` section with entries for different icon sizes
   - Icons are now referenced using relative paths from the extension root

4. Improved build scripts in `package.json`
   - Icons are copied from src to public/images as part of the build process
   - Additional step ensures icons in dist root are also copied to dist/images
   - Created directories as needed during prebuild
   - Simplified development workflow

## How to Test

Build and test the extension:

```bash
cd packages/extension
pnpm build
```

Then load the unpacked extension in Chrome from the `packages/extension/dist` directory:

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in the top right)
3. Click "Load unpacked" and select the `packages/extension/dist` directory
4. Verify the extension icon appears in the toolbar and is correctly displayed in the extensions list

## Troubleshooting

If you encounter icon loading issues:

1. Verify icon files exist in the correct location:

   ```bash
   ls -la dist/images/
   ```

   Make sure `icon16.png`, `icon48.png` and `icon128.png` are present in this directory

2. Check Chrome's console for errors

   - Open `chrome://extensions`
   - Find the extension and click "Errors" if available
   - This will show detailed error messages

3. Check manifest.json for correct paths:

   ```bash
   cat dist/manifest.json | grep -A 5 "icons"
   ```

   Ensure paths match the actual locations of the icon files

4. If errors persist, try the following:
   ```bash
   rm -rf dist
   pnpm build
   ```
   This will perform a clean build of the extension

The icon should now be packaged correctly with the extension and displayed properly in Chrome.
