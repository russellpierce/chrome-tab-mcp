# Chrome Tab Reader Extension

A Chrome extension that extracts and analyzes webpage content with AI assistance using a three-phase extraction process.

## Features

- **Three-Phase Content Extraction:**
  1. Trigger lazy-loading by simulating scroll
  2. Wait for DOM stability (handles dynamic content)
  3. Extract clean content with Readability.js

- **Intelligent Content Cleaning:** Removes navigation, ads, and footer content
- **Keyword Filtering:** Extract content between specific keywords
- **Browser Extension UI:** Simple popup interface for content extraction

## Quick Start

### Installation

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Load the extension in Chrome:**
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode" (top right)
   - Click "Load unpacked"
   - Select the `extension/` directory
   - Extension should appear with a green checkmark

3. **Verify it works:**
   - Navigate to any webpage (e.g., https://example.com)
   - Click the extension icon
   - Click "Extract Content"
   - Content should appear in the popup

## Testing

### Automated Tests (Recommended)

Run automated tests to verify the extension works correctly:

```bash
npm test
```

This will:
- ✅ Verify all extension files are present
- ✅ Load the extension in Chrome
- ✅ Test content extraction functionality
- ✅ Test the UI and popup

**Quick Start:** See [TESTING_QUICK_START.md](TESTING_QUICK_START.md)

**Detailed Guide:** See [tests/README.md](tests/README.md)

### Manual Testing

For comprehensive manual testing, see:
- `extension/TESTING.md` - Testing checklist
- `BROWSER_EXTENSION_TESTING.md` - Detailed testing guide

## Project Structure

```
chrome-tab-mcp/
├── extension/              # Chrome extension files
│   ├── manifest.json       # Extension manifest
│   ├── content_script.js   # Content extraction logic
│   ├── service_worker.js   # Background service worker
│   ├── popup.html          # Extension popup UI
│   ├── popup.js            # Popup logic
│   └── lib/                # Third-party libraries
│       ├── readability.min.js
│       └── dompurify.min.js
├── tests/                  # Automated tests
│   ├── installation.test.js
│   ├── extraction.test.js
│   ├── ui.test.js
│   └── test-utils.js
└── package.json            # Node dependencies
```

## Development

### Run Tests During Development

```bash
# Run all tests
npm test

# Run specific test suite
npm run test:install
npm run test:extraction
npm run test:ui

# Watch mode (re-run on changes)
npm run test:watch
```

### Test Before Committing

Always run tests before committing changes:

```bash
npm test
```

All tests should pass before submitting a pull request.

## Documentation

- **Extension Setup:** `extension/SETUP.md`
- **Architecture:** `extension/ARCHITECTURE.md`
- **Testing Guide:** `extension/TESTING.md`
- **Test Documentation:** `tests/README.md`
- **Quick Testing:** `TESTING_QUICK_START.md`

## Browser Support

- ✅ Chrome (v88+)
- ✅ Edge (Chromium-based)
- ✅ Brave
- ❌ Firefox (Manifest v3 differences)

## Requirements

- Node.js v14 or higher
- Chrome/Chromium browser
- npm (comes with Node.js)

## Troubleshooting

### Extension doesn't load
- Check that all files exist in `extension/` directory
- Look for errors in `chrome://extensions/`
- Reload the extension after changes

### Tests fail
- Ensure Chrome/Chromium is installed
- Run `npm install` to install dependencies
- See `tests/README.md` for detailed troubleshooting

### Content extraction doesn't work
- Check browser console for errors
- Verify Readability and DOMPurify are loaded
- Try the "simple" strategy instead of "three-phase"

## License

ISC

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `npm test` to verify everything works
5. Submit a pull request

All tests must pass before merging.
