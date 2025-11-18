# Chrome Tab Reader

> **Note:** This document is AI-authored with human oversight.

![Test Extension](https://github.com/russellpierce/chrome-tab-mcp/actions/workflows/test-extension.yml/badge.svg)

Extract and analyze content from Chrome tabs using AI through the Model Context Protocol (MCP). Works cross-platform with Chrome extension + Native Messaging or HTTP API.

## Overview

Chrome Tab Reader provides AI-powered webpage content extraction with three access methods:

1. **MCP Server + Extension** (Recommended) - Cross-platform, direct browser integration
2. **HTTP API Server** - For programmatic access and custom integrations
3. **Extension Standalone** - Manual content extraction via popup UI

## Quick Start (MCP + Extension)

The recommended setup uses the MCP server with browser extension for AI-powered content analysis.

### Prerequisites

- Chrome/Chromium browser
- Python 3.8+
- Ollama running locally
- Node.js 20+ (for extension tests)

### 1. Install Extension

```bash
# Load extension in Chrome
# 1. Open chrome://extensions/
# 2. Enable "Developer mode" (top right)
# 3. Click "Load unpacked"
# 4. Select the extension/ directory
```

See [extension/SETUP.md](extension/SETUP.md) for detailed setup.

### 2. Install Native Messaging Host

```bash
# Linux/macOS
./install_native_host.sh <your-extension-id>

# Windows
.\install_native_host.ps1 <your-extension-id>
```

See [NATIVE_MESSAGING_SETUP.md](NATIVE_MESSAGING_SETUP.md) for platform-specific instructions.

### 3. Start MCP Server

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start MCP server
uv run chrome_tab_mcp_server.py --ollama-url http://localhost:11434 --model llama2
```

### 4. Use with Claude Code

The MCP server provides the `process_chrome_tab` tool for extracting and analyzing webpage content through Claude Code.

## Features

- **Three-Phase Content Extraction:** Lazy-loading detection, DOM stability waiting, Readability-based noise removal
- **Cross-Platform:** Windows, macOS, Linux support via Native Messaging
- **AI-Powered Analysis:** Integrates with local Ollama models
- **Secure:** Local processing, no external data sharing
- **Flexible:** Keyword filtering, custom prompts, multiple extraction strategies

## Components

### 1. Browser Extension

Cross-platform Chrome/Chromium extension with sophisticated content extraction.

- Three-phase extraction (lazy-loading, DOM stability, Readability.js)
- Native Messaging for direct MCP integration
- Token generation for HTTP API access
- **Docs:** [extension/README.md](extension/README.md) | [extension/ARCHITECTURE.md](extension/ARCHITECTURE.md) | [extension/SETUP.md](extension/SETUP.md)

### 2. MCP Server

Model Context Protocol server for Claude Code integration.

- Cross-platform via Native Messaging (Windows, macOS, Linux)
- Legacy AppleScript mode (macOS only)
- Ollama integration for AI analysis
- **Docs:** [NATIVE_MESSAGING_SETUP.md](NATIVE_MESSAGING_SETUP.md)
- **Code:** `chrome_tab_mcp_server.py`, `chrome_tab_native_host.py`

### 3. HTTP API Server (Optional)

FastAPI-based REST API for programmatic access.

- OpenAPI 3.0 specification with Swagger UI
- Token-based authentication
- Direct extension communication
- **Docs:** [ACCESS_CONTROL_SETUP.md](ACCESS_CONTROL_SETUP.md)
- **Code:** `chrome_tab_http_server.py`

## Testing

### Automated Tests

```bash
npm test
```

This runs comprehensive extension tests including installation, extraction, and UI validation.

**Documentation:**
- **Quick Start:** [tests/TESTING_QUICK_START.md](tests/TESTING_QUICK_START.md)
- **Detailed Guide:** [tests/README.md](tests/README.md)
- **Manual Testing:** [extension/TESTING.md](extension/TESTING.md) | [tests/BROWSER_EXTENSION_TESTING.md](tests/BROWSER_EXTENSION_TESTING.md)

### CI/CD

Automated tests run on GitHub Actions for all PRs and pushes to main branches.

View workflow runs: [GitHub Actions](https://github.com/russellpierce/chrome-tab-mcp/actions)

## Platform Support

| Component | Windows | macOS | Linux |
|-----------|---------|-------|-------|
| Chrome Extension | ✅ | ✅ | ✅ |
| MCP Server (Native Messaging) | ✅ | ✅ | ✅ |
| HTTP Server | ✅ | ✅ | ✅ |
| Legacy AppleScript | ❌ | ✅ | ❌ |

**Browser Support:** Chrome 88+, Edge (Chromium), Brave

## Documentation

### Setup & Configuration
- **Extension Setup:** [extension/SETUP.md](extension/SETUP.md)
- **Native Messaging:** [NATIVE_MESSAGING_SETUP.md](NATIVE_MESSAGING_SETUP.md)
- **HTTP API & Access Control:** [ACCESS_CONTROL_SETUP.md](ACCESS_CONTROL_SETUP.md)

### Architecture & Development
- **Extension Architecture:** [extension/ARCHITECTURE.md](extension/ARCHITECTURE.md)
- **Extension Development:** [extension/README.md](extension/README.md)

### Testing
- **Quick Start:** [tests/TESTING_QUICK_START.md](tests/TESTING_QUICK_START.md)
- **Test Suite Documentation:** [tests/README.md](tests/README.md)
- **Manual Testing:** [extension/TESTING.md](extension/TESTING.md)
- **E2E Testing:** [tests/BROWSER_EXTENSION_TESTING.md](tests/BROWSER_EXTENSION_TESTING.md)
- **Native Messaging Tests:** [tests/TESTING_NATIVE_MESSAGING.md](tests/TESTING_NATIVE_MESSAGING.md)

## Project Structure

```
chrome-tab-mcp/
├── extension/              # Browser extension
│   ├── manifest.json
│   ├── content_script.js
│   ├── service_worker.js
│   └── lib/               # Readability.js, DOMPurify
├── tests/                 # Automated tests
├── chrome_tab_mcp_server.py      # MCP server
├── chrome_tab_native_host.py     # Native messaging bridge
├── chrome_tab_http_server.py     # HTTP API server
└── install_native_host.sh        # Setup script
```

## Troubleshooting

### Extension Issues

**Extension doesn't load:**
- Verify all files exist in `extension/` directory
- Check for errors in `chrome://extensions/`
- Reload extension after changes

**Content extraction fails:**
- Check browser console for errors (F12)
- Verify Readability.js and DOMPurify are loaded
- Try "simple" strategy instead of "three-phase"

### MCP Server Issues

**Native messaging connection fails:**
- Run installation script: `./install_native_host.sh <extension-id>`
- Check logs: `tail -f ~/.chrome-tab-reader/native_host.log`
- Verify extension ID in manifest matches your extension
- See [NATIVE_MESSAGING_SETUP.md](NATIVE_MESSAGING_SETUP.md#troubleshooting)

**Ollama errors:**
- Ensure Ollama is running: `ollama list`
- Check URL configuration: default is `http://localhost:11434`
- Verify model is installed: `ollama pull llama2`

### HTTP API Issues

**401 Unauthorized:**
- Get token from extension popup
- Configure tokens.json (see [ACCESS_CONTROL_SETUP.md](ACCESS_CONTROL_SETUP.md))
- Restart HTTP server after updating tokens

**See component-specific documentation for detailed troubleshooting.**

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `npm test` to verify
5. Submit a pull request

All tests must pass before merging.

## Requirements

- **Node.js:** v20+ (LTS recommended) - for extension tests
- **Python:** 3.8+ - for MCP/HTTP servers
- **Browser:** Chrome 88+, Edge (Chromium), or Brave
- **Ollama:** For AI analysis (local installation)

## License

ISC / MIT

## Author

Russell Pierce (with AI assistance)
