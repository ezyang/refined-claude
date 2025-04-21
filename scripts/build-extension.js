/**
 * Build script for Chrome extension
 * Copies and processes necessary files to build the extension
 */

const fs = require('fs');
const path = require('path');

// Define paths
const rootDir = path.resolve(__dirname, '..');
const distDir = path.join(rootDir, 'dist');
const extensionDir = path.join(rootDir, 'dist', 'extension');
const srcExtensionDir = path.join(rootDir, 'src', 'extension');

// Create directories if they don't exist
if (!fs.existsSync(distDir)) {
  fs.mkdirSync(distDir);
}

if (!fs.existsSync(extensionDir)) {
  fs.mkdirSync(extensionDir);
}

// Create icons directory
const iconsDir = path.join(extensionDir, 'icons');
if (!fs.existsSync(iconsDir)) {
  fs.mkdirSync(iconsDir);
}

// Copy manifest.json
console.log('Copying manifest.json...');
fs.copyFileSync(
  path.join(srcExtensionDir, 'manifest.json'),
  path.join(extensionDir, 'manifest.json')
);

// Create placeholder icons
console.log('Creating placeholder icons...');
const iconSizes = [16, 32, 48, 128];
iconSizes.forEach(size => {
  const iconPath = path.join(iconsDir, `icon${size}.png`);
  if (!fs.existsSync(iconPath)) {
    console.log(`Creating placeholder icon: ${size}x${size}`);
    // This is just a dummy file creation - in a real project, you'd copy actual icon files
    fs.writeFileSync(iconPath, '');
  }
});

// Log success message
console.log('Build complete. Extension files are in:', extensionDir);
console.log('Note: You need to create actual icon files for a production extension.');
