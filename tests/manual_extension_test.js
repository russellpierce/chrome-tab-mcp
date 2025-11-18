#!/usr/bin/env node
/**
 * Manual Extension Test Script
 *
 * This script allows you to manually test the Chrome extension
 * without requiring Jest. It uses the same test-utils as the automated tests.
 *
 * Usage:
 *     node tests/manual_extension_test.js [test_name]
 *
 * Available tests:
 *     - files: Verify extension files exist
 *     - load: Test extension loading in Chrome
 *     - extract: Test basic content extraction
 *     - libraries: Test Readability/DOMPurify libraries
 *     - real: Test extraction on a real website
 *     - all: Run all tests (default)
 *
 * Requirements:
 *     - Chrome/Chromium installed
 *     - npm dependencies installed (npm install)
 */

const {
  verifyExtensionFiles,
  launchBrowserWithExtension,
  loadTestPage,
  extractContent,
  checkLibrariesLoaded,
  testAgainstRealSite,
  delay
} = require('./test-utils');

// Color output helpers
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function header(message) {
  console.log('\n' + '='.repeat(60));
  log(message, 'blue');
  console.log('='.repeat(60) + '\n');
}

async function testExtensionFiles() {
  header('Test 1: Extension Files');

  log('Checking if all required extension files exist...', 'yellow');

  const result = verifyExtensionFiles();

  console.log(`Extension path: ${result.extensionPath}`);

  if (result.allExist) {
    log('✓ All required files exist:', 'green');
    result.existing.forEach(file => console.log(`  - ${file}`));
    return true;
  } else {
    log('✗ Missing files:', 'red');
    result.missing.forEach(file => console.log(`  - ${file}`));
    log('\nPlease ensure all extension files are present.', 'yellow');
    return false;
  }
}

async function testExtensionLoading() {
  header('Test 2: Extension Loading');

  log('Launching Chrome with extension loaded...', 'yellow');
  log('(A Chrome window will open - this is normal)', 'yellow');

  let browser = null;

  try {
    const { browser: b, extensionId } = await launchBrowserWithExtension();
    browser = b;

    if (extensionId) {
      log(`✓ Extension loaded successfully with ID: ${extensionId}`, 'green');

      // Keep browser open for a moment so user can see it
      log('\nBrowser will remain open for 3 seconds...', 'yellow');
      await delay(3000);

      await browser.close();
      return true;
    } else {
      log('✗ Extension ID not found', 'red');
      log('The extension may not have loaded properly.', 'yellow');
      await browser.close();
      return false;
    }
  } catch (error) {
    log(`✗ Failed to launch browser: ${error.message}`, 'red');
    if (browser) {
      await browser.close();
    }
    return false;
  }
}

async function testBasicExtraction() {
  header('Test 3: Basic Content Extraction');

  log('Launching Chrome and testing content extraction...', 'yellow');

  let browser = null;
  let page = null;

  try {
    const { browser: b, extensionId } = await launchBrowserWithExtension();
    browser = b;

    if (!extensionId) {
      throw new Error('Extension failed to load');
    }

    log('Loading test page...', 'yellow');
    page = await browser.newPage();
    await loadTestPage(page, 'test-simple.html');

    log('Extracting content with three-phase strategy...', 'yellow');
    const result = await extractContent(page, { strategy: 'three-phase' });

    if (result.status === 'success') {
      log('✓ Content extraction successful:', 'green');
      console.log(`  Title: ${result.title}`);
      console.log(`  URL: ${result.url}`);
      console.log(`  Content length: ${result.content.length} characters`);
      console.log(`  Extraction time: ${result.extraction_time_ms}ms`);
      console.log(`  Content preview: ${result.content.substring(0, 100)}...`);

      await page.close();
      await browser.close();
      return true;
    } else {
      log(`✗ Extraction failed: ${result.error}`, 'red');
      await page.close();
      await browser.close();
      return false;
    }
  } catch (error) {
    log(`✗ Test failed: ${error.message}`, 'red');
    if (page) await page.close();
    if (browser) await browser.close();
    return false;
  }
}

async function testLibraries() {
  header('Test 4: Readability & DOMPurify Libraries');

  log('Testing if content script libraries are loaded...', 'yellow');

  let browser = null;
  let page = null;

  try {
    const { browser: b, extensionId } = await launchBrowserWithExtension();
    browser = b;

    if (!extensionId) {
      throw new Error('Extension failed to load');
    }

    log('Opening test page...', 'yellow');
    page = await browser.newPage();
    await page.goto('https://example.com', { waitUntil: 'networkidle0' });
    await delay(2000); // Wait for content script injection

    log('Checking libraries...', 'yellow');
    const libs = await checkLibrariesLoaded(page);

    console.log(`  Readability: ${libs.readability ? '✓' : '✗'}`);
    console.log(`  DOMPurify: ${libs.dompurify ? '✓' : '✗'}`);

    const success = libs.readability && libs.dompurify;

    if (success) {
      log('✓ All libraries loaded successfully', 'green');
    } else {
      log('✗ Some libraries failed to load', 'red');
    }

    await page.close();
    await browser.close();
    return success;
  } catch (error) {
    log(`✗ Test failed: ${error.message}`, 'red');
    if (page) await page.close();
    if (browser) await browser.close();
    return false;
  }
}

async function testRealWebsite() {
  header('Test 5: Real Website Extraction');

  log('Testing extraction on a real website...', 'yellow');
  log('Target: https://github.com/russellpierce/chrome-tab-mcp', 'yellow');

  let browser = null;

  try {
    const { browser: b, extensionId } = await launchBrowserWithExtension();
    browser = b;

    if (!extensionId) {
      throw new Error('Extension failed to load');
    }

    const result = await testAgainstRealSite(
      browser,
      'https://github.com/russellpierce/chrome-tab-mcp'
    );

    if (result && result.status === 'success') {
      log('✓ Real website extraction successful:', 'green');
      console.log(`  Title: ${result.title}`);
      console.log(`  Content length: ${result.content.length} characters`);

      await browser.close();
      return true;
    } else {
      log('✗ Real website extraction failed', 'red');
      await browser.close();
      return false;
    }
  } catch (error) {
    log(`✗ Test failed: ${error.message}`, 'red');
    if (browser) await browser.close();
    return false;
  }
}

async function main() {
  console.log('='.repeat(60));
  log('Chrome Extension - Manual Test Suite', 'blue');
  console.log('='.repeat(60));

  // Parse command line argument
  const testName = process.argv[2] || 'all';

  const results = {};

  try {
    // Always check files first
    if (testName === 'files' || testName === 'all') {
      results.files = await testExtensionFiles();

      // If files test fails, don't continue with other tests
      if (!results.files && testName === 'all') {
        log('\n✗ Stopping tests: Required files missing', 'red');
        printSummary(results);
        process.exit(1);
      }
    }

    if (testName === 'load' || testName === 'all') {
      results.load = await testExtensionLoading();
    }

    if (testName === 'extract' || testName === 'all') {
      results.extract = await testBasicExtraction();
    }

    if (testName === 'libraries' || testName === 'all') {
      results.libraries = await testLibraries();
    }

    if (testName === 'real' || testName === 'all') {
      results.real = await testRealWebsite();
    }

    printSummary(results);

    // Exit with appropriate code
    const allPassed = Object.values(results).every(r => r === true);
    process.exit(allPassed ? 0 : 1);

  } catch (error) {
    log(`\n✗ Fatal error: ${error.message}`, 'red');
    console.error(error);
    process.exit(1);
  }
}

function printSummary(results) {
  console.log('\n' + '='.repeat(60));
  log('Test Summary', 'blue');
  console.log('='.repeat(60));

  if (Object.keys(results).length === 0) {
    log('No tests were run.', 'yellow');
    log('Usage: node tests/manual_extension_test.js [test_name]', 'yellow');
    log('Available tests: files, load, extract, libraries, real, all', 'yellow');
    return;
  }

  for (const [name, passed] of Object.entries(results)) {
    const status = passed ? '✓ PASS' : '✗ FAIL';
    const color = passed ? 'green' : 'red';
    const paddedName = name.padEnd(20);
    log(`${paddedName} ${status}`, color);
  }

  console.log('='.repeat(60) + '\n');
}

// Run main function
if (require.main === module) {
  main().catch(error => {
    log(`\n✗ Unhandled error: ${error.message}`, 'red');
    console.error(error);
    process.exit(1);
  });
}

module.exports = {
  testExtensionFiles,
  testExtensionLoading,
  testBasicExtraction,
  testLibraries,
  testRealWebsite
};
