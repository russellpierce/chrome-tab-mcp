# Chrome Tab Reader

> **Note:** This document is AI-authored with very limited human oversight.

![Test Extension](https://github.com/russellpierce/chrome-tab-mcp/actions/workflows/test-extension.yml/badge.svg)

Extract and analyze content from Chrome tabs using AI. Supports multiple access methods: Chrome extension, HTTP API, and MCP server.

## Quick Start for Existing Setups

Already have Chrome Tab Reader installed? Here's how to start it:

**Just using the extension:**
```bash
# Open Chrome, navigate to a page, click the extension icon → Extract Content
```

**Using the HTTP API:**
```bash
# Start the HTTP server (automatically binds to localhost only for security)
uv run chrome_tab_http_server.py

# Test it
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8888/api/health
```

**Using the MCP Server (with Ollama):**
```bash
# Required environment variables
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="llama2"

# Start the MCP server
uv run chrome_tab_mcp_server.py --ollama-url $OLLAMA_BASE_URL --model $OLLAMA_MODEL

# Or with authentication (if native host started with --require-auth)
export BRIDGE_AUTH_TOKEN="your-token-here"
uv run chrome_tab_mcp_server.py \
  --ollama-url $OLLAMA_BASE_URL \
  --model $OLLAMA_MODEL \
  --bridge-auth-token $BRIDGE_AUTH_TOKEN
```

**Optional: Native Messaging Bridge with Authentication**
```bash
# Default (no auth required)
python chrome_tab_native_host.py

# With authentication enabled
python chrome_tab_native_host.py --require-auth
```

**Key Environment Variables:**
- `OLLAMA_BASE_URL` - URL of your Ollama server (e.g., `http://localhost:11434`)
- `OLLAMA_MODEL` - Model to use (e.g., `llama2`, `qwen`)
- `BRIDGE_AUTH_TOKEN` - Optional auth token for native bridge (get from extension popup)

**Configuration Files:**
- Linux: `~/.config/chrome-tab-reader/tokens.json`
- macOS: `~/Library/Application Support/chrome-tab-reader/tokens.json`
- Windows: `%APPDATA%\chrome-tab-reader\tokens.json`

---

## Quick Start for New Setups

First time setting up Chrome Tab Reader? Follow these steps:

### 1. Install the Chrome Extension

```bash
# Install Node.js dependencies
npm install

# Load the extension in Chrome:
# 1. Open chrome://extensions/
# 2. Enable "Developer mode" (top right)
# 3. Click "Load unpacked"
# 4. Select the extension/ directory
```

### 2. Get Your Access Token

```bash
# Click the extension icon in Chrome
# Your access token is shown at the top
# Click "Copy JSON" or "Download Config File"
```

### 3. Configure Token Authentication (if using HTTP API or authenticated bridge)

```bash
# The extension provides a ready-to-use tokens.json
# Save it to the platform-specific location shown above, or use:
./setup_token.sh
```

### 4. Install Python Dependencies

```bash
# Option A: Using uv (recommended)
# uv handles dependencies automatically via PEP 723 inline metadata

# Option B: Using uv pip
uv pip install -r requirements.txt
```

### 5. Start Using It!

Now jump to the **[Quick Start for Existing Setups](#quick-start-for-existing-setups)** above to start the services you need.

---

## Features

- **Three-Phase Content Extraction:**
  1. Trigger lazy-loading by simulating scroll
  2. Wait for DOM stability (handles dynamic content)
  3. Extract clean content with Readability.js

- **Intelligent Content Cleaning:** Removes navigation, ads, and footer content
- **Keyword Filtering:** Extract content between specific keywords
- **Token-Based Access Control:** Secure HTTP API with bearer token authentication
- **Browser Extension UI:** Simple popup interface for content extraction
- **Cross-Platform:** Works on Windows, macOS, and Linux

## Components

This repository contains three ways to access Chrome tab content:

### 1. Chrome Extension (Recommended - Cross-platform)
- Browser extension for Chrome/Chromium
- Three-phase content extraction (lazy-loading, DOM stability, Readability.js)
- Direct DOM access for reliable extraction
- Generates secure access tokens for API authentication
- Works on Windows, macOS, Linux

### 2. HTTP Server (FastAPI)
- REST API for programmatic access built with FastAPI
- **Automatic OpenAPI 3.0 specification** generation from code
- **Interactive API documentation** at `/docs` (Swagger UI) and `/redoc`
- Endpoints for content extraction and tab navigation
- **Token-based authentication** for security
- Can be called from scripts, MCP server, or other tools
- See: `chrome_tab_http_server.py`

### 3. MCP Server (Cross-platform via Native Messaging)
- Model Context Protocol server for Claude Code
- Uses Chrome Native Messaging for direct extension communication
- Cross-platform support (Windows, macOS, Linux)
- Integrates with local Ollama AI models
- Superior three-phase extraction via browser extension
- See: `chrome_tab_mcp_server.py`, `README_MCP.md`, and `NATIVE_MESSAGING_SETUP.md`

## Quick Start

### Extension Setup

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

### HTTP Server Setup (Optional)

If you want to use the HTTP API:

1. **Get your access token:**
   - Click the extension icon
   - Copy the access token shown at the top

2. **Configure authentication:**
   ```bash
   ./setup_token.sh
   # Or manually create the tokens.json file (see extension/docs for location)
   ```

3. **Start the HTTP server:**

   **Option A - Using uv (recommended):**
   ```bash
   uv run chrome_tab_http_server.py
   ```

   **Option B - Using uv pip:**
   ```bash
   uv pip install -r requirements.txt
   python chrome_tab_http_server.py
   ```

4. **Explore the API:**
   - **Interactive Swagger UI:** http://localhost:8888/docs
   - **ReDoc Documentation:** http://localhost:8888/redoc
   - **OpenAPI Spec (JSON):** http://localhost:8888/openapi.json

5. **Test it:**
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        http://localhost:8888/api/health
   ```

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

**Quick Start:** See [tests/TESTING_QUICK_START.md](tests/TESTING_QUICK_START.md)

**Detailed Guide:** See [tests/README.md](tests/README.md)

### Manual Testing

For comprehensive manual testing, see:
- `extension/TESTING.md` - Testing checklist
- `tests/BROWSER_EXTENSION_TESTING.md` - Detailed testing guide

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

## Access Control

**All HTTP API endpoints require Bearer token authentication.**

The extension generates a unique cryptographic token on first install. This token must be configured in the HTTP server to allow API access.

### Why Token Authentication?

- Prevents unauthorized localhost access from malicious scripts
- Allows multiple clients with different tokens
- Easy to rotate if compromised
- Industry-standard OAuth2 bearer token pattern

### Setup Guide

See **[ACCESS_CONTROL_SETUP.md](ACCESS_CONTROL_SETUP.md)** for detailed instructions.

**Quick setup:**
```bash
./setup_token.sh
```

## Usage Examples

### Using the Extension UI

1. Click the extension icon
2. Click "Extract Content"
3. View extracted content in the popup

### Using the HTTP API

```bash
# Get current tab info
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8888/api/current_tab

# Extract content from current tab
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"action": "extract_current_tab", "strategy": "three-phase"}' \
     http://localhost:8888/api/extract
```

### Using from Python

```python
import requests

TOKEN = "your-token-here"
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

response = requests.post(
    "http://localhost:8888/api/extract",
    headers=headers,
    json={"action": "extract_current_tab", "strategy": "three-phase"}
)

data = response.json()
print(data['content'])
```

## Project Structure

```
chrome-tab-mcp/
├── extension/              # Chrome extension files
│   ├── manifest.json       # Extension manifest
│   ├── content_script.js   # Content extraction logic
│   ├── service_worker.js   # Background service worker (token gen)
│   ├── popup.html          # Extension popup UI (shows token)
│   ├── popup.js            # Popup logic
│   └── lib/                # Third-party libraries
│       ├── readability.min.js
│       └── dompurify.min.js
├── tests/                  # Automated tests
│   ├── installation.test.js
│   ├── extraction.test.js
│   ├── ui.test.js
│   └── test-utils.js
├── chrome_tab_http_server.py  # HTTP API server (with auth)
├── chrome_tab_mcp_server.py   # MCP server (macOS)
├── setup_token.sh             # Token setup helper
├── tokens.json.example        # Token config template
└── package.json               # Node dependencies
```

## CI/CD

This project includes automated testing via GitHub Actions:

- **Push/PR to main branches**: Runs full test suite on Node.js 20
- **Pull Requests**: Quick validation tests with summary in PR
- **Manual trigger**: Can be run manually from Actions tab

### Running Tests in CI

Tests automatically run on:
- Push to `main`, `master`, `develop`, or `claude/*` branches
- Pull requests to `main` or `master`
- Manual workflow dispatch

The CI environment:
- Installs Chromium automatically
- Runs all 32 tests
- Generates coverage reports
- Uploads test artifacts

View workflow runs in the [Actions tab](https://github.com/russellpierce/chrome-tab-mcp/actions).

## Security

- ✅ Token-based authentication on all API endpoints
- ✅ Cryptographically random 256-bit tokens
- ✅ Tokens stored securely in Chrome extension storage
- ✅ Server validates tokens on every request
- ✅ Support for multiple tokens (different clients)
- ✅ Easy token rotation/regeneration

See [ACCESS_CONTROL_SETUP.md](ACCESS_CONTROL_SETUP.md) for security best practices.

## Configuration Files

- `~/.chrome-tab-reader/tokens.json` - Valid access tokens
- `tokens.json.example` - Example configuration file
- `chrome_tab_mcp_config.json` - MCP server configuration (Claude Code)

## API Documentation

Start the HTTP server and visit:
```
http://localhost:8888/
```

## Platform Support

| Component | Windows | macOS | Linux |
|-----------|---------|-------|-------|
| Chrome Extension | ✅ | ✅ | ✅ |
| HTTP Server | ✅ | ✅ | ✅ |
| MCP Server (Native Messaging) | ✅ | ✅ | ✅ |

## Browser Support

- ✅ Chrome (v88+)
- ✅ Edge (Chromium-based)
- ✅ Brave
- ❌ Firefox (Manifest v3 differences)

## Requirements

- Node.js v20 or higher (LTS recommended)
- Chrome/Chromium browser
- npm v10 or higher (comes with Node.js)
- Python 3.8+ (for HTTP/MCP servers)

## Documentation

- **Extension Setup:** `extension/SETUP.md`
- **Architecture:** `extension/ARCHITECTURE.md`
- **Testing Guide:** `extension/TESTING.md`
- **Test Documentation:** `tests/README.md`
- **Quick Testing:** `tests/TESTING_QUICK_START.md`
- **Access Control:** `ACCESS_CONTROL_SETUP.md`
- **Native Messaging Setup:** `NATIVE_MESSAGING_SETUP.md`

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

### 401 Unauthorized Errors (HTTP API)
- Verify token is correct (copy from extension popup)
- Check `~/.chrome-tab-reader/tokens.json` contains your token
- Restart HTTP server after updating tokens.json
- Ensure `Authorization: Bearer YOUR_TOKEN` header format

### Extension Not Generating Token
- Reload extension in chrome://extensions/
- Check browser console (F12) for errors
- Reinstall extension

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `npm test` to verify everything works
5. Submit a pull request

All tests must pass before merging.

## License

ISC / MIT

## Author

Russell Pierce (with AI assistance)
