#!/usr/bin/env node

import { runTestData } from './index';
import path from 'path';

async function main() {
  console.log('Running rrweb headless test on sample data...');

  try {
    // Default path is relative to the dist directory where this will be executed
    const testDataPath = process.argv[2] || '../../testdata/approve-tool.json';
    const absolutePath = path.resolve(process.cwd(), testDataPath);

    console.log(`Using test data from: ${absolutePath}`);

    const result = await runTestData(testDataPath);

    console.log('Test completed successfully');
    console.log('Results:');
    console.log(JSON.stringify(result, null, 2));

    if (result.elementExists) {
      console.log('✅ Z-modal element was found in the replay');
      process.exit(0);
    } else {
      console.log('❌ Z-modal element was NOT found in the replay');
      process.exit(1);
    }
  } catch (error) {
    console.error('Error running test:', error);
    process.exit(1);
  }
}

main();
