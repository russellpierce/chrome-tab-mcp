# Chrome Tab Reader

> **Note:** This document is AI-authored with very limited human oversight.

![Test Extension](https://github.com/russellpierce/chrome-tab-mcp/actions/workflows/test-extension.yml/badge.svg)

**MCP server for Claude Code and other AI assistants** - Extract and analyze Chrome tab content using local Ollama models. Distill large web pages with cheap local AI before expensive cloud processing.

## Why Use Chrome Tab Reader?

**Problem:** Sending full web pages to Claude is expensive and clutters your context window.

**Solution:** Use a cheap local model (Ollama) to distill content first, then send only the summary to Claude.

**Benefits:**
- **Lower token costs** - Significantly reduce tokens sent to expensive cloud models
- **Cleaner context** - Keep your conversation focused on what matters
- **Better responses** - Less noise means Claude focuses on relevant information
- **Faster processing** - Smaller inputs mean quicker responses

**Example:**
- Original webpage: 50,000 tokens (entire article with ads, navigation, etc.)
- After local processing: 5,000 tokens (key facts and Q&A)
- Result: Substantial token reduction + cleaner context window

---

## Quick Start (MCP Server)

### Prerequisites

- **Chrome/Chromium** browser
- **Python 3.8+** with `uv` package manager
- **Ollama** with a model installed (e.g., `llama2`)
- **Claude Code** or another MCP client

### 1. Install Chrome Extension

```bash
# Install Node.js dependencies (for extension libraries)
npm install

# Load extension in Chrome:
# 1. Open chrome://extensions/
# 2. Enable "Developer mode" (top right)
# 3. Click "Load unpacked"
# 4. Select the extension/ directory
```

### 2. Install Native Messaging Host

```bash
# Get extension ID from Chrome (or use MCP tool find_extension_id() after setup)
# Click extension icon or check chrome://extensions/

# Linux/macOS
./install_native_host.sh <extension-id>

# Windows PowerShell
.\install_native_host.ps1 <extension-id>
```

### 3. Install and Start Ollama

```bash
# Install Ollama from https://ollama.ai

# Pull a model
ollama pull llama2           # Recommended: fast, good quality
ollama pull qwen2.5:7b       # Alternative: larger, better quality

# Start Ollama (usually starts automatically)
ollama serve
```

### 4. Configure MCP Server in Claude Code

Add to your Claude Code MCP configuration:

**Linux/macOS:** `~/.config/claude-code/mcp.json`
**Windows:** `%APPDATA%\claude-code\mcp.json`

```json
{
  "mcpServers": {
    "chrome-tab-reader": {
      "command": "uv",
      "args": [
        "run",
        "/absolute/path/to/chrome_tab_mcp_server.py",
        "--ollama-url", "http://localhost:11434",
        "--model", "llama2"
      ]
    }
  }
}
```

### 5. Test It!

Open Claude Code and ask:

> "Use check_connection_status to verify Chrome Tab Reader is working"

You should see all components connected. Then try:

> "Summarize the current webpage I have open in Chrome"

---

## Features

### Core Capabilities

- **🤖 AI-Powered Content Distillation** - Process web pages with local Ollama before Claude
- **📄 Three-Phase Extraction Pipeline** - Handles lazy-loading, dynamic content, and cleaning
- **🔧 4 MCP Tools** - Extract, analyze, diagnose, and troubleshoot
- **💰 Token Cost Optimization** - Reduce tokens sent to expensive models and keep context clean
- **🧹 Context Window Management** - Send only relevant information, not cluttered web pages
- **🌐 Cross-Platform** - Windows, macOS, Linux

### Three-Phase Content Extraction

The extension provides sophisticated content extraction that handles complex modern websites:

1. **Trigger Lazy-Loading** (2-5 sec) - Simulates scrolling to load infinite scroll, lazy images, "Load More" buttons
2. **Wait for DOM Stability** (up to 30 sec) - Handles SPAs (React/Vue), live feeds, dynamic forms
3. **Extract with Readability.js** - Mozilla's proven algorithm removes ads, navigation, sidebars

---

## MCP Tools

The MCP server exposes 4 tools for AI assistants:

### `process_chrome_tab(system_prompt=None)`

Extract and analyze current tab with local Ollama AI.

**Usage:**
```python
# Default Q&A analysis
process_chrome_tab()

# Custom summarization
process_chrome_tab(system_prompt="Summarize in 3 bullet points")

# Data extraction
process_chrome_tab(system_prompt="Extract all product names and prices as JSON")
```

---

### `get_raw_tab_content()`

Get raw extracted content without AI processing.

**Usage:**
```python
# Get raw content for custom processing
get_raw_tab_content()
```

---

### `check_connection_status()`

Diagnose connectivity of Chrome extension bridge and Ollama server.

**Usage:**
```python
check_connection_status()
# → Reports status of bridge, Ollama, and extension
```

---

### `find_extension_id()`

Find Chrome Tab Reader extension ID for native messaging setup.

**Usage:**
```python
find_extension_id()
# → Returns extension ID and installation instructions
```

**See [README_MCP.md](README_MCP.md) for detailed MCP documentation, troubleshooting, and advanced usage.**

---

## Alternative Access Methods

While MCP is the primary use case, Chrome Tab Reader also provides:

### HTTP API

REST API for programmatic access from scripts and applications.

- FastAPI server with automatic OpenAPI documentation
- Token-based authentication
- Interactive Swagger UI at `/docs`
- See **[README_HTTP.md](README_HTTP.md)** for complete documentation

**Quick start:**
```bash
uv run chrome_tab_http_server.py
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8888/api/health
```

### Extension UI

Simple browser extension popup for manual content extraction.

**Quick start:**
1. Click extension icon in Chrome
2. Click "Extract Content"
3. View extracted content in popup

---

## Testing

### Run All Tests

```bash
./run_tests.sh          # Run all tests (requires Chrome)
./run_tests.sh ci       # CI-safe tests (no Chrome needed)
```

### Automated Tests

```bash
# Extension tests (Jest + Puppeteer)
npm test

# Python tests (pytest)
./run_tests.sh unit         # Unit tests
./run_tests.sh e2e          # End-to-end tests
```

**Detailed testing guide:** [tests/README.md](tests/README.md)

---

## Project Structure

```
chrome-tab-mcp/
├── chrome_tab_mcp_server.py   # MCP server (primary entry point)
├── chrome_tab_http_server.py  # HTTP API server (alternative)
├── chrome_tab_native_host.py  # Native messaging bridge
│
├── extension/                  # Chrome extension
│   ├── manifest.json          # Extension configuration
│   ├── service_worker.js      # Background service
│   ├── content_script.js      # Content extraction (three-phase)
│   ├── popup.html/popup.js    # Extension UI
│   └── lib/                   # Readability.js, DOMPurify
│
├── tests/                      # Automated tests
│   ├── *.test.js              # JavaScript tests (Jest)
│   └── test_*.py              # Python tests (pytest)
│
├── README_MCP.md              # MCP server documentation
├── README_HTTP.md             # HTTP API documentation
├── NATIVE_MESSAGING_SETUP.md  # Native messaging setup guide
├── ACCESS_CONTROL_SETUP.md    # Token authentication guide
└── CLAUDE.md                  # AI assistant development guide
```

---

## Platform Support

| Component | Windows | macOS | Linux |
|-----------|---------|-------|-------|
| MCP Server | ✅ | ✅ | ✅ |
| Chrome Extension | ✅ | ✅ | ✅ |
| HTTP Server | ✅ | ✅ | ✅ |

**Browsers:** Chrome (v88+), Edge (Chromium), Brave

---

## Requirements

- **Node.js** v20+ (for extension libraries)
- **Python** 3.8+ (for MCP/HTTP servers)
- **uv** (Python package manager)
- **Chrome/Chromium** browser
- **Ollama** (for MCP server)

---

## Troubleshooting

### MCP Server Won't Start

**Check Ollama:**
```bash
curl http://localhost:11434/api/tags
ollama list  # Verify model is installed
```

**Check Python:**
```bash
python --version  # Should be 3.8+
uv --version      # Should be installed
```

---

### "Cannot connect to native messaging bridge"

**Verify Chrome is running and extension loaded:**
```bash
# 1. Open Chrome
# 2. Visit chrome://extensions/
# 3. Look for "Chrome Tab Reader" with green checkmark
# 4. If not present, reinstall extension
```

**Verify native host installed:**
```bash
# Linux/macOS
ls ~/.config/google-chrome/NativeMessagingHosts/
# Should contain: com.chrome_tab_reader.host.json

# Windows
dir %APPDATA%\Google\Chrome\NativeMessagingHosts\
# Should contain: com.chrome_tab_reader.host.json
```

**Reinstall if needed:**
```bash
./install_native_host.sh <extension-id>
```

---

### "No content retrieved from Chrome tab"

**Check page is loaded:**
- Ensure webpage finished loading in Chrome
- Try a simple page like https://example.com first

**Use diagnostic tool:**
Ask Claude Code: "Use check_connection_status to diagnose the issue"

---

### More Troubleshooting

See detailed guides:
- [README_MCP.md](README_MCP.md) - MCP-specific troubleshooting
- [README_HTTP.md](README_HTTP.md) - HTTP API troubleshooting
- [NATIVE_MESSAGING_SETUP.md](NATIVE_MESSAGING_SETUP.md) - Native messaging issues

---

## Documentation

### Main Guides
- **[README_MCP.md](README_MCP.md)** - MCP server documentation (architecture, tools, troubleshooting)
- **[README_HTTP.md](README_HTTP.md)** - HTTP API documentation (endpoints, authentication, examples)
- **[NATIVE_MESSAGING_SETUP.md](NATIVE_MESSAGING_SETUP.md)** - Native messaging setup guide
- **[ACCESS_CONTROL_SETUP.md](ACCESS_CONTROL_SETUP.md)** - Token authentication guide
- **[CLAUDE.md](CLAUDE.md)** - AI assistant development guide

### Extension Documentation
- **[extension/SETUP.md](extension/SETUP.md)** - Extension installation
- **[extension/ARCHITECTURE.md](extension/ARCHITECTURE.md)** - Extension architecture
- **[extension/TESTING.md](extension/TESTING.md)** - Extension testing

### Testing Documentation
- **[tests/README.md](tests/README.md)** - Test suite documentation
- **[tests/TESTING_QUICK_START.md](tests/TESTING_QUICK_START.md)** - Quick testing guide

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_BASE_URL` | Ollama server URL | Required (e.g., `http://localhost:11434`) |
| `OLLAMA_MODEL` | Model name | Required (e.g., `llama2`, `qwen2.5:7b`) |
| `BRIDGE_AUTH_TOKEN` | Optional auth token for native bridge | None |
| `CHROME_TAB_LOG_EXCLUDE_URLS` | URLs to exclude from logs | None |

### Configuration Files

- **MCP Config:** `~/.config/claude-code/mcp.json` (Linux/macOS) or `%APPDATA%\claude-code\mcp.json` (Windows)
- **Tokens (HTTP API):** `~/.config/chrome-tab-reader/tokens.json` (Linux/macOS) or `%APPDATA%\chrome-tab-reader\tokens.json` (Windows)

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `./run_tests.sh all`
5. Submit a pull request

All tests must pass before merging.

---

## Security

- ✅ **Localhost-only binding** - Servers only accessible from local machine
- ✅ **Token-based authentication** - Cryptographically secure 256-bit tokens
- ✅ **Native messaging** - Secure Chrome extension communication
- ✅ **No external network access** - Content stays on your machine

See [ACCESS_CONTROL_SETUP.md](ACCESS_CONTROL_SETUP.md) for security best practices.

---

## License

ISC / MIT

## Author

Russell Pierce (with AI assistance)
