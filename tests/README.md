# Chrome Tab Reader Extension - Automated Tests

This directory contains automated tests for the Chrome Tab Reader extension. These tests verify that the extension can be installed and works as expected.

## Overview

The test suite includes:

- **Installation Tests** (`installation.test.js`): Verify extension files are present and extension loads correctly in Chrome
- **Content Extraction Tests** (`extraction.test.js`): Test the three-phase extraction process and content handling
- **UI Tests** (`ui.test.js`): Test the popup interface and user interactions

## Prerequisites

### Required Software

1. **Node.js** (v14 or higher)
   ```bash
   node --version
   ```

2. **Chrome or Chromium** browser installed at one of these paths:
   - `/usr/bin/google-chrome`
   - `/usr/bin/google-chrome-stable`
   - `/usr/bin/chromium`
   - `/usr/bin/chromium-browser`
   - `/snap/bin/chromium`
   - Custom path set via `CHROME_PATH` environment variable

3. **npm** (comes with Node.js)
   ```bash
   npm --version
   ```

### Install Dependencies

From the project root directory:

```bash
npm install
```

This will install:
- Jest (test framework)
- Puppeteer (browser automation)
- Supporting type definitions

## Running Tests

### Run All Tests

```bash
npm test
```

This runs all test suites and displays results.

### Run Specific Test Suites

**Installation tests only:**
```bash
npm run test:install
```

**Content extraction tests only:**
```bash
npm run test:extraction
```

**UI tests only:**
```bash
npm run test:ui
```

### Watch Mode

Automatically re-run tests when files change:

```bash
npm run test:watch
```

Press `q` to quit watch mode.

### Coverage Report

Generate test coverage report:

```bash
npm run test:coverage
```

Coverage report will be in the `coverage/` directory.

## Test Configuration

### Chrome Path

If Chrome/Chromium is not in a standard location, set the `CHROME_PATH` environment variable:

```bash
export CHROME_PATH=/path/to/chrome
npm test
```

Or for a single test run:

```bash
CHROME_PATH=/path/to/chrome npm test
```

### Test Timeout

Tests have a 60-second timeout by default. To change this, edit `jest.config.js`:

```javascript
module.exports = {
  testTimeout: 120000, // 2 minutes
  // ... other config
};
```

## What the Tests Verify

### Installation Tests

✅ All required extension files exist:
- `manifest.json`
- `content_script.js`
- `service_worker.js`
- `popup.html`
- `popup.js`
- `lib/readability.min.js`
- `lib/dompurify.min.js`

✅ `manifest.json` is valid JSON and properly configured

✅ Extension loads successfully in Chrome

✅ Service worker starts and runs

✅ Content scripts inject into web pages

✅ Required libraries (Readability, DOMPurify) load correctly

### Content Extraction Tests

✅ Basic extraction works on simple pages (example.com)

✅ Extraction includes page title and URL

✅ Handles empty pages gracefully

✅ Both "simple" and "three-phase" strategies work

✅ Extraction completes within reasonable time

✅ Keyword filtering works (start/end keywords)

✅ Keyword filtering is case-insensitive

✅ Readability.js removes navigation/ads/footer

✅ Handles pages with scripts and complex DOM

✅ Libraries are available in content script context

### UI Tests

✅ Popup opens successfully

✅ All UI elements are present:
- Tab title display
- Extract button
- Clear button
- Status area
- Content area

✅ Extract button triggers extraction

✅ Clear button clears content area

✅ Tab title updates with current page info

✅ Popup can communicate with service worker

✅ Errors display gracefully without crashes

## Test Structure

```
tests/
├── README.md              # This file
├── test-utils.js          # Shared utilities for testing
├── installation.test.js   # Installation & setup tests
├── extraction.test.js     # Content extraction tests
└── ui.test.js            # UI and popup tests
```

### Test Utilities (`test-utils.js`)

Provides helper functions:

- `verifyExtensionFiles()` - Check all extension files exist
- `launchBrowserWithExtension()` - Launch Chrome with extension loaded
- `createTestPage()` - Create a test page with custom content
- `waitForExtension()` - Wait for extension to be ready
- `getServiceWorker()` - Get the extension's service worker
- `openPopup()` - Open the extension popup
- `checkLibrariesLoaded()` - Verify Readability and DOMPurify are loaded

## Troubleshooting

### Chrome Not Found

**Error:** `Chrome/Chromium not found`

**Solution:** Install Chrome/Chromium or set `CHROME_PATH`:
```bash
# Ubuntu/Debian
sudo apt-get install chromium-browser

# Or set custom path
export CHROME_PATH=/usr/bin/chromium-browser
```

### Extension Fails to Load

**Error:** Extension files missing or service worker not running

**Solution:**
1. Verify all extension files are present:
   ```bash
   ls -la extension/
   ```
2. Check that libraries are built:
   ```bash
   ls -la extension/lib/
   ```

### Tests Timeout

**Error:** Tests exceed 60-second timeout

**Solution:**
1. Increase timeout in `jest.config.js`
2. Check internet connection (tests visit example.com)
3. Close other Chrome instances that might interfere

### Permission Errors

**Error:** `EACCES` or permission denied

**Solution:**
```bash
# Fix file permissions
chmod -R 755 extension/
chmod 644 extension/*.js extension/*.json extension/*.html
```

### Puppeteer Download Failed

**Error:** Failed to download Chrome during npm install

**Solution:** Puppeteer is configured to skip Chrome download (we use system Chrome).
If you see this error, it should not affect tests. If needed:
```bash
PUPPETEER_SKIP_DOWNLOAD=true npm install
```

## Running Tests in CI/CD

This project includes automated GitHub Actions workflows:

### Workflows Included

1. **`test-extension.yml`** - Comprehensive testing
   - Runs on push to main branches and PRs
   - Tests on Node.js 18 and 20
   - Installs Chromium automatically
   - Runs all test suites
   - Generates coverage reports
   - Can be triggered manually

2. **`pr-check.yml`** - Quick PR validation
   - Runs on pull requests
   - Fast validation of changes
   - Adds test summary to PR

### Viewing Test Results

Visit the [GitHub Actions tab](https://github.com/russellpierce/chrome-tab-mcp/actions) to see:
- Test run history
- Coverage reports
- Test artifacts
- Workflow logs

### Running Locally Like CI

To run tests exactly as CI does:

```bash
# Install dependencies (CI mode - uses package-lock.json)
npm ci

# Install Chromium (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y chromium-browser

# Run tests with explicit Chrome path
CHROME_PATH=/usr/bin/chromium-browser npm test
```

### Workflow Files

- `.github/workflows/test-extension.yml` - Main test workflow
- `.github/workflows/pr-check.yml` - PR validation workflow

## Writing New Tests

### Basic Test Template

```javascript
const { launchBrowserWithExtension } = require('./test-utils');

describe('My New Test Suite', () => {
  let browser;
  let extensionId;

  beforeAll(async () => {
    const result = await launchBrowserWithExtension();
    browser = result.browser;
    extensionId = result.extensionId;
  });

  afterAll(async () => {
    if (browser) {
      await browser.close();
    }
  });

  test('my test case', async () => {
    const page = await browser.newPage();
    // ... test logic
    await page.close();
  });
});
```

### Best Practices

1. **Always close pages:** Close pages in `afterEach` or after each test
2. **Use timeouts:** Add waits for async operations
3. **Clean up:** Close browser in `afterAll`
4. **Isolate tests:** Each test should be independent
5. **Use descriptive names:** Test names should clearly describe what's being tested

## Manual Testing

For tests that can't be automated, see:
- `extension/TESTING.md` - Comprehensive manual testing checklist
- `BROWSER_EXTENSION_TESTING.md` - Detailed manual testing guide

## Test Results

### Expected Output

When all tests pass:

```
PASS  tests/installation.test.js
  Extension Installation
    File Structure
      ✓ all required extension files exist (5ms)
      ✓ manifest.json is valid JSON (2ms)
      ✓ manifest.json has required permissions (1ms)
      ✓ manifest.json content scripts configuration is correct (2ms)
    Browser Loading
      ✓ extension loads in Chrome (3524ms)
      ✓ extension service worker is running (156ms)
      ✓ extension is ready within timeout (23ms)
      ✓ content script loads on test page (2456ms)
      ✓ libraries are loaded in content script (2134ms)

PASS  tests/extraction.test.js
  Content Extraction
    ...

PASS  tests/ui.test.js
  Extension UI
    ...

Test Suites: 3 passed, 3 total
Tests:       27 passed, 27 total
Snapshots:   0 total
Time:        45.231s
```

## Maintenance

### Updating Tests

When the extension changes:

1. Update test utilities if APIs change
2. Add new test cases for new features
3. Update expected values if output format changes
4. Keep test documentation current

### Performance

Tests should be fast:
- Installation tests: ~10-15 seconds
- Extraction tests: ~20-30 seconds
- UI tests: ~10-15 seconds
- Total: ~45-60 seconds

If tests are slower, investigate:
- Unnecessary waits
- Network issues
- Heavy page loads

## Support

For issues with tests:

1. Check this README for troubleshooting
2. Review test output for specific errors
3. Run tests with `--verbose` flag for more details:
   ```bash
   npm test -- --verbose
   ```

## License

Same as the main project.
