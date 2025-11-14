# Chrome Tab Reader

Extract and analyze content from Chrome tabs using AI. Supports multiple access methods: Chrome extension, HTTP API, and MCP server.

## Components

This repository contains three ways to access Chrome tab content:

### 1. Chrome Extension (Recommended - Cross-platform)
- **Browser extension** for Chrome/Chromium
- Three-phase content extraction (lazy-loading, DOM stability, Readability.js)
- Direct DOM access for reliable extraction
- Works on Windows, macOS, Linux
- See: `extension/` directory

### 2. HTTP Server
- **REST API** for programmatic access
- Endpoints for content extraction and tab navigation
- **Token-based authentication** for security
- Can be called from scripts, MCP server, or other tools
- See: `chrome_tab_http_server.py`

### 3. MCP Server (macOS only)
- **Model Context Protocol** server for Claude Code
- Uses AppleScript to extract tab content
- Integrates with local Ollama AI models
- See: `chrome_tab_mcp_server.py` and `README_MCP.md`

## Quick Start

### Extension Setup

1. **Install the extension:**
   ```bash
   # Navigate to chrome://extensions/
   # Enable "Developer mode"
   # Click "Load unpacked"
   # Select the extension/ directory
   ```

2. **Get your access token:**
   - Click the extension icon
   - Copy the access token shown at the top

3. **Configure authentication (for HTTP server):**
   ```bash
   ./setup_token.sh
   # Or manually create ~/.chrome-tab-reader/tokens.json
   ```

4. **Start the HTTP server:**
   ```bash
   python chrome_tab_http_server.py
   ```

5. **Test it:**
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        http://localhost:8888/api/health
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

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Chrome Browser                                 │
│  ┌───────────────────────────────────────────┐  │
│  │  Chrome Tab Reader Extension              │  │
│  │  • Generates access token                 │  │
│  │  • Extracts content (3-phase)             │  │
│  │  • Displays in popup UI                   │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
                    │
                    │ Token displayed in UI
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  HTTP Server (localhost:8888)                   │
│  • Validates bearer tokens                      │
│  • Provides REST API                            │
│  • Calls AppleScript (macOS)                    │
│  • Or uses Chrome extension extraction          │
└─────────────────────────────────────────────────┘
                    │
                    │ Authenticated requests
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  Your Scripts / MCP Server                      │
│  • Include token in requests                    │
│  • Process extracted content                    │
└─────────────────────────────────────────────────┘
```

## Configuration Files

- `~/.chrome-tab-reader/tokens.json` - Valid access tokens
- `tokens.json.example` - Example configuration file
- `chrome_tab_mcp_config.json` - MCP server configuration (Claude Code)

## API Documentation

Start the HTTP server and visit:
```
http://localhost:8888/
```

## Security

- ✅ Token-based authentication on all API endpoints
- ✅ Cryptographically random 256-bit tokens
- ✅ Tokens stored securely in Chrome extension storage
- ✅ Server validates tokens on every request
- ✅ Support for multiple tokens (different clients)
- ✅ Easy token rotation/regeneration

See [ACCESS_CONTROL_SETUP.md](ACCESS_CONTROL_SETUP.md) for security best practices.

## Files

- `extension/` - Chrome extension source code
  - `manifest.json` - Extension manifest (Manifest V3)
  - `service_worker.js` - Background service worker (token generation)
  - `content_script.js` - Content extraction logic (3-phase)
  - `popup.html/js` - Extension UI (displays token)
- `chrome_tab_http_server.py` - HTTP API server with token auth
- `chrome_tab_mcp_server.py` - MCP server (macOS only)
- `chrome_tab.scpt` - AppleScript for tab extraction (macOS)
- `setup_token.sh` - Helper script for token configuration
- `tokens.json.example` - Example tokens configuration
- `ACCESS_CONTROL_SETUP.md` - Detailed security setup guide

## Platform Support

| Component | Windows | macOS | Linux |
|-----------|---------|-------|-------|
| Chrome Extension | ✅ | ✅ | ✅ |
| HTTP Server | ✅ | ✅ | ✅ |
| MCP Server | ❌ | ✅ | ❌ |

## Design Documentation

- [BROWSER_EXTENSION_DESIGN.md](BROWSER_EXTENSION_DESIGN.md) - Extension architecture
- [BROWSER_EXTENSION_TESTING.md](BROWSER_EXTENSION_TESTING.md) - Testing guide
- [DESIGN.md](DESIGN.md) - Overall design decisions
- [README_MCP.md](README_MCP.md) - MCP server documentation

## Troubleshooting

### 401 Unauthorized Errors

- Verify token is correct (copy from extension popup)
- Check `~/.chrome-tab-reader/tokens.json` contains your token
- Restart HTTP server after updating tokens.json
- Ensure `Authorization: Bearer YOUR_TOKEN` header format

### Extension Not Generating Token

- Reload extension in chrome://extensions/
- Check browser console (F12) for errors
- Reinstall extension

### HTTP Server Not Starting

- Check if port 8888 is already in use
- Verify Python 3.8+ is installed
- Check server logs for specific errors

## License

MIT

## Author

Russell Pierce (with AI assistance)
