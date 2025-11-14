# Quick Start - Automated Testing

This guide will help you quickly run automated tests to verify the Chrome Tab Reader extension works correctly on your system.

## Prerequisites

- Node.js v20 or higher (LTS recommended)
- Chrome or Chromium browser installed
- Terminal/command line access

**Check your Node version:**
```bash
node --version  # Should show v20.x.x or higher
```

If you need to install/update Node.js, visit: https://nodejs.org/

## Quick Test (3 minutes)

### 1. Install Dependencies

```bash
npm install
```

### 2. Run Tests

```bash
npm test
```

That's it! The tests will:
- ✅ Verify all extension files are present
- ✅ Load the extension in Chrome
- ✅ Test content extraction
- ✅ Test the UI/popup

## Understanding Results

### All Tests Pass ✅

```
Test Suites: 3 passed, 3 total
Tests:       27 passed, 27 total
```

Your extension is working correctly!

### Some Tests Fail ❌

Check the error message:

**"Chrome/Chromium not found"**
- Install Chrome or Chromium
- Or set `CHROME_PATH=/path/to/chrome`

**"Extension files missing"**
- Make sure you're in the project root directory
- Verify `extension/` directory exists

**Timeout errors**
- Try running specific test suite: `npm run test:install`
- Check your internet connection

## Run Specific Tests

```bash
# Just check if extension can be installed
npm run test:install

# Just test content extraction
npm run test:extraction

# Just test the UI
npm run test:ui
```

## What Gets Tested?

### Installation (9 tests)
- All required files exist
- Extension loads in Chrome
- Libraries are available

### Content Extraction (12 tests)
- Extracts content from web pages
- Handles different page types
- Keyword filtering works
- Readability cleans content

### UI (6 tests)
- Popup opens
- Buttons work
- Communication with background works

## Next Steps

- **For detailed test documentation:** See `tests/README.md`
- **For manual testing:** See `extension/TESTING.md`
- **To contribute:** Run `npm test` before submitting changes

## Common Commands

```bash
# Run all tests
npm test

# Run tests and watch for changes
npm run test:watch

# Generate coverage report
npm run test:coverage

# Run with custom Chrome path
CHROME_PATH=/usr/bin/chromium npm test
```

## Need Help?

1. Read the error message carefully
2. Check `tests/README.md` for troubleshooting
3. Ensure Chrome/Chromium is installed
4. Verify `extension/` directory has all files

## Expected Time

- Installation: 1 minute
- Test run: 45-60 seconds
- Total: ~2-3 minutes

That's it! You now have automated tests to verify your extension works correctly. 🚀
