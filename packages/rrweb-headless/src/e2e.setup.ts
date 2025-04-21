import { chromium } from 'playwright';

/**
 * This setup file ensures that all necessary browser binaries are downloaded
 * before running the e2e tests.
 */
export default async function setup() {
  console.log('Setting up end-to-end test environment...');

  try {
    // This will trigger browser download if not already installed
    const browser = await chromium.launch({ headless: true });
    await browser.close();
    console.log('Browser dependencies are installed and ready');
  } catch (error) {
    console.error('Failed to set up browser dependencies:', error);
    throw error;
  }
}
