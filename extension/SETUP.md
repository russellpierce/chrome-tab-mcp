# Browser Extension Setup & Installation

> **Note:** This document is AI-authored with human oversight.

## Quick Start

### For Users

1. **Install extension**
   - Go to Chrome Web Store (when published)
   - Click "Add to Chrome"
   - Confirm permissions

2. **Start MCP server**
   ```bash
   cd /path/to/chrome-tab-mcp
   python chrome_tab_mcp_server.py --ollama-url http://localhost:11434 --model llama2
   ```

3. **Start Ollama**
   ```bash
   ollama serve
   ```

4. **Use the extension**
   - Open any webpage
   - Click extension icon
   - Click "Analyze"
   - Results appear in popup

---

## For Developers

### Prerequisites

- Node.js 16+ (for running tests, not required for extension itself)
- Chrome/Chromium/Edge/Brave browser
- MCP server running
- Ollama running

### Directory Structure

```
extension/
├── manifest.json              # Extension configuration (Manifest v3)
├── popup.html                 # Popup user interface
├── popup.js                   # Popup logic
├── content_script.js          # DOM content extraction (3-phase)
├── service_worker.js          # Background service worker
├── lib/
│   ├── readability.min.js    # Mozilla Readability.js (extract from DOM)
│   └── dompurify.min.js      # DOMPurify (sanitize extracted content)
├── styles/
│   └── popup.css             # Popup styling
├── images/
│   ├── icon-16.png
│   ├── icon-48.png
│   └── icon-128.png
├── SETUP.md                   # This file
├── ARCHITECTURE.md            # Design documentation
├── TESTING.md                 # Testing procedures
└── DEVELOPMENT.md             # Development guide
```

### Setting Up for Development

#### 1. Clone or Download

```bash
git clone https://github.com/russellpierce/chrome-tab-mcp
cd chrome-tab-mcp/extension
```

#### 2. Get Dependencies

Readability.js and DOMPurify are included as minified files in `lib/`.

If you need to update them:

```bash
# Get latest versions from npm
npm install @mozilla/readability dompurify

# Minify (requires build tools)
npx webpack --mode production
```

#### 3. Install Extension in Browser

**Chrome/Edge/Brave:**

1. Open browser DevTools: Right-click anywhere → "Inspect"
2. Go to `chrome://extensions/` (paste in address bar)
3. Enable "Developer Mode" (top right toggle)
4. Click "Load unpacked"
5. Select the `extension/` directory
6. Extension should appear in the list

**After installation:**
- Extension icon appears in toolbar
- Click icon to open popup
- Ready to test

#### 4. Start MCP Server

From project root:

```bash
# First time: install dependencies
pip install -r requirements.txt

# Run with Ollama on localhost
python chrome_tab_mcp_server.py --ollama-url http://localhost:11434 --model llama2

# Or with custom Ollama server
python chrome_tab_mcp_server.py --ollama-url http://192.168.1.100:11434 --model qwen
```

**What the server does:**
- Listens on `http://127.0.0.1:3000`
- Exposes `/tools/process_chrome_tab` endpoint
- Calls Ollama for analysis
- Returns results to extension

#### 5. Start Ollama

In a separate terminal:

```bash
ollama serve
```

First time:

```bash
# Pull a model (if not already done)
ollama pull llama2
ollama pull qwen

# Then serve
ollama serve
```

#### 6. Test the Extension

1. Open any webpage
2. Click extension icon in toolbar
3. Review defaults or enter custom prompt
4. Click "Analyze"
5. Watch progress messages
6. Results appear in popup

---

## File Descriptions

### manifest.json

Manifest v3 configuration. Defines:
- Extension name, version, description
- Permissions (activeTab, scripting, storage)
- Host permissions (localhost:3000)
- Content scripts, service worker, popup
- Icons

Update this if adding new permissions or UI.

### popup.html

Extension popup interface. Shows:
- System prompt textarea
- Keyword filtering inputs
- Analyze button
- Results display area
- Settings button

### popup.js

Popup logic:
- Handle "Analyze" button clicks
- Request content extraction from content script
- Send analysis request to service worker
- Display results
- Handle "Use default" prompt link
- Copy to clipboard functionality

### content_script.js

Runs in page context, performs 3-phase extraction:

1. **Phase 1:** Trigger lazy-loading (scroll to bottom)
2. **Phase 2:** Wait for DOM stability (2s after last change)
3. **Phase 3:** Extract with Readability.js

Exports:
- `extractPageContent()` - Full extraction pipeline
- `extractContentBetweenKeywords()` - Keyword filtering

### service_worker.js

Background service worker:
- Receives extraction requests from popup
- Makes HTTP POST to MCP server
- Handles errors gracefully
- Responds to popup with results

HTTP endpoint: `POST http://127.0.0.1:3000/tools/process_chrome_tab`

### lib/readability.min.js

Mozilla's Readability.js (minified):
- Extracts main article content from DOM
- Removes noise (nav, footer, sidebar, ads)
- Returns cleaned text and metadata

License: Apache 2.0

### lib/dompurify.min.js

DOMPurify sanitizer (minified):
- Removes XSS attack vectors from HTML
- Strips script tags and event handlers
- Safe for displaying user-extracted content

License: Mozilla Public License 2.0

### styles/popup.css

Popup styling:
- Layout and spacing
- Font sizing
- Colors
- Button styles
- Responsive design

---

## Configuration

### MCP Server URL

Default: `http://127.0.0.1:3000`

To change, edit `service_worker.js`:

```javascript
const MCP_SERVER_URL = "http://127.0.0.1:3000";  // Change this
```

Future enhancement: Make configurable via settings page.

### Timeout Settings

**Extraction timeout:**
- Lazy-loading: 5 seconds max (configurable in `content_script.js`)
- DOM stability: 30 seconds max (prevents excessive wait times)
- Readability: <1 second

**MCP request timeout:**
- 9 minutes total (3min extraction + 5min Ollama + buffer)
- Can increase in `service_worker.js` if needed

**Edit in content_script.js:**
```javascript
async function waitForDOMStability(timeoutMs = 30000) {
    // 30000 ms = 30 seconds
    // Change timeoutMs parameter to adjust
}
```

**Edit in service_worker.js:**
```javascript
timeout: 540000  // 9 minutes (in milliseconds)
```

### Custom System Prompt

Default: General webpage analysis

To change default, edit `popup.js`:

```javascript
const DEFAULT_SYSTEM_PROMPT =
    "You are a helpful AI assistant. Process the attached webpage...";
    // Change this string
```

---

## Development Workflow

### Making Changes

1. Edit files in `extension/` directory
2. Go to `chrome://extensions/`
3. Find extension and click "Reload"
4. Test changes

### Testing

Full testing guide: See `TESTING.md`

Quick smoke test:

```
1. Click extension icon
2. Click "Analyze" on example.com
3. Wait for results
4. Check DevTools console for errors
```

### Debugging

**View logs:**
- Open popup
- Press F12 for DevTools
- Console tab shows all logs

**View network requests:**
- DevTools → Network tab
- Run extraction
- Look for POST to `localhost:3000`

**View service worker errors:**
- Go to `chrome://extensions`
- Find Chrome Tab Reader
- Click "Service worker" under Inspect views

### Building for Distribution

When ready to release to Chrome Web Store:

```bash
# Create clean build
rm -rf build
mkdir build
cp -r extension/* build/

# Verify all files present
ls build/

# Create zip for submission
zip -r chrome-tab-reader.zip build/
```

Submit to Chrome Web Store:
- Go to https://chrome.google.com/webstore/devconsole
- Create new item
- Upload zip file
- Fill in store listing
- Submit for review

---

## Troubleshooting

### Extension doesn't appear

1. Check manifest.json is valid (no syntax errors)
2. Go to `chrome://extensions/`
3. Enable "Developer Mode"
4. Click "Load unpacked"
5. Select `extension/` directory
6. Reload page

### Extension appears but popup won't open

1. Check popup.html exists
2. Check popup.js has no syntax errors
3. Open DevTools console, look for errors
4. Reload extension

### "Cannot connect to MCP server"

1. Verify MCP server is running
2. Check port 3000 is not blocked
3. Try: `curl http://127.0.0.1:3000/` (should fail but show the server is listening)
4. Check MCP server logs for errors

### Extraction takes forever

1. DOM stability waiting for content to stabilize
2. Maximum wait is 30 seconds (by design)
3. If page keeps changing, hard timeout triggers
4. Try on a different page
5. Check browser console for JS errors on page

### Results are missing content

1. Readability.js may have failed (check console)
2. Fallback to innerText might not capture all content
3. Try on a different page
4. Check browser console for extraction errors

### Memory usage is high

1. Run garbage collection: DevTools → Memory → Collect garbage
2. Close popup if not using
3. If persistent, may be memory leak (report as bug)

### MCP server won't start

1. Check Python version: `python --version` (need 3.8+)
2. Check dependencies: `pip list | grep fastmcp`
3. Missing dependency? `pip install fastmcp requests`
4. Port 3000 already in use? `lsof -i :3000`

### Ollama won't respond

1. Check Ollama is running: `ollama list`
2. Check server URL: default is `http://localhost:11434`
3. Check model exists: `ollama list`
4. Try simple test: `curl http://localhost:11434/api/tags`

---

## Performance Optimization

### Bundle Size

Current:
- readability.js: ~40KB minified
- dompurify.js: ~10KB minified
- popup.js: ~2KB
- service_worker.js: ~1KB
- **Total: ~53KB uncompressed**

To optimize:
- Lazy-load readability.js only when needed
- Use dynamic imports for large libraries
- Minify popup.css and popup.js

### Extraction Speed

Current targets:
- Phase 1 (lazy-loading): <5 seconds
- Phase 2 (DOM stability): <30 seconds (typically 0-2 sec)
- Phase 3 (readability): <1 second

To optimize:
- Reduce lazy-load scroll cycles (line 14 in content_script.js)
- Reduce DOM stability timer (line 129 in content_script.js)
- Cache Readability parser between extractions

### Memory Usage

Current target: <50MB during extraction

To optimize:
- Clean up DOM mutation observer after stability detected
- Clear large objects after processing
- Use WeakMap for caching instead of Map

---

## Security Checklist

Before releasing to users:

- [ ] No API keys or credentials in code
- [ ] No hardcoded passwords
- [ ] DOMPurify sanitizing all extracted content
- [ ] No inline scripts in popup.html
- [ ] No eval() or Function() constructors
- [ ] CSP headers properly configured
- [ ] Only connecting to localhost
- [ ] Error messages don't expose system info

---

## Resources

- **Manifest v3 Docs:** https://developer.chrome.com/docs/extensions/mv3/
- **Readability.js:** https://github.com/mozilla/readability
- **DOMPurify:** https://github.com/cure53/DOMPurify
- **Chrome Extensions API:** https://developer.chrome.com/docs/extensions/reference/
- **Content Scripts:** https://developer.chrome.com/docs/extensions/mv3/content_scripts/
- **Service Workers:** https://developer.chrome.com/docs/extensions/mv3/service_workers/

---

**Status:** Setup Guide Complete
**Version:** 1.0
**Last Updated:** November 13, 2025
**Next Step:** Install extension and run tests
