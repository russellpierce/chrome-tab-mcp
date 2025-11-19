# Chrome Tab Reader - MCP Server

> **Note:** This document is AI-authored with very limited human oversight.

Model Context Protocol (MCP) server for Chrome Tab Reader. Integrates with Claude Code and other MCP clients to provide Chrome tab content extraction and AI-powered analysis using local Ollama models.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Available Tools](#available-tools)
- [Setup Guide](#setup-guide)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Advanced Topics](#advanced-topics)

---

## Overview

The Chrome Tab Reader MCP server enables AI assistants (like Claude Code) to:

1. **Extract content from Chrome tabs** - Uses the browser extension's three-phase extraction
2. **Process content with local AI** - Distills content using cheaper local Ollama models
3. **Return summarized information** - Reduces token costs for expensive cloud models

### Why Use This MCP?

**Cost Optimization & Context Management**: Process large web pages with a local model (free/cheap) before sending summarized content to expensive cloud models like Claude.

**Workflow**:
```
User asks about webpage
    ↓
MCP extracts tab content (three-phase extraction)
    ↓
Local Ollama processes content (cheap/free)
    ↓
MCP returns summary to Claude Code
    ↓
Claude uses summary to answer user (saves tokens + keeps context clean)
```

**Benefits**:
- **Lower costs**: Significant token reduction for expensive cloud models
- **Cleaner context**: Send only relevant information, not entire cluttered web pages
- **Better answers**: Claude focuses on key facts, not ads and navigation
- **Faster responses**: Smaller inputs process more quickly

**Example**:
- Original webpage: 50,000 tokens (entire article with ads, navigation, etc.)
- After local Ollama processing: 5,000 tokens (key facts and Q&A)
- Result: Substantial token savings + cleaner context window

---

## Architecture

### Component Overview

```
Claude Code (MCP Client)
    ↓
MCP Server (chrome_tab_mcp_server.py)
    ↓
┌─────────────────────────────────┬─────────────────────────────┐
│ Native Messaging Bridge         │ Ollama Server               │
│ (chrome_tab_native_host.py)     │ (localhost:11434)           │
│ TCP Server (localhost:8765)     │                             │
└─────────────────────────────────┘                             │
    ↓                                                            │
Chrome Extension                                                 │
    ↓                                                            │
Browser Tab Content ────────────────────────────────────────────┘
```

### Three-Phase Extraction Pipeline

The MCP server leverages the extension's sophisticated extraction:

**Phase 1: Trigger Lazy-Loading (2-5 seconds)**
- Simulates scrolling to trigger lazy-loaded content
- Handles infinite scroll, "Load More" buttons, lazy images
- Scrolls to bottom up to 5 times

**Phase 2: Wait for DOM Stability (up to 30 seconds)**
- Uses MutationObserver to detect when DOM stops changing
- Resolves when no changes for 2 consecutive seconds
- Handles SPAs (React/Vue), live feeds, dynamic forms

**Phase 3: Extract with Readability.js**
- Mozilla's proven content extraction algorithm
- Removes navigation, ads, sidebars, comments
- Sanitizes with DOMPurify
- Returns clean, readable text

---

## Available Tools

The MCP server exposes **4 tools** to calling LLMs:

### 1. `process_chrome_tab(system_prompt=None)`

Extracts content from current Chrome tab and processes it with Ollama AI.

**Parameters:**
- `system_prompt` (optional string): Custom AI analysis prompt. Defaults to Q&A extraction.

**Returns:**
- AI-generated analysis of the tab content (thinking tags stripped)

**Example:**
```python
# Default Q&A analysis
process_chrome_tab()

# Custom summarization
process_chrome_tab(system_prompt="Summarize in 3 bullets")

# Data extraction
process_chrome_tab(system_prompt="Extract all product names and prices as JSON")
```

**When to Use:**
- User asks about current webpage content
- Need AI-processed summary of page
- Want structured extraction from page

---

### 2. `get_raw_tab_content()`

Gets raw extracted content without AI processing.

**Parameters:** None

**Returns:**
- Raw cleaned text from Readability.js extraction
- Includes title, URL, and content length metadata

**Example:**
```python
# Get raw content for custom processing
raw_content = get_raw_tab_content()
# → "Title: Example Page\nURL: https://example.com\n..."
```

**When to Use:**
- Need full unprocessed content
- Ollama is unavailable or slow
- Want to process content with different prompts
- Debugging extraction issues

---

### 3. `check_connection_status()`

Diagnoses connectivity of Chrome extension bridge and Ollama server.

**Parameters:** None

**Returns:**
- Diagnostic report with status of all components:
  - Native messaging bridge connectivity
  - Ollama server availability
  - Extension installation status

**Example:**
```python
check_connection_status()
# → "=== Chrome Tab Reader Connection Status ===
#    1. Native Messaging Bridge:
#       ✓ Already connected
#    2. Ollama Server:
#       ✓ Ollama server is reachable
#       ✓ Model 'llama2' is available
#    3. Chrome Extension:
#       ✓ Extension found (1 installation)
#    ==="
```

**When to Use:**
- Troubleshooting extraction or AI failures
- Verifying setup before use
- Diagnosing connection issues

---

### 4. `find_extension_id()`

Finds Chrome Tab Reader extension ID on the system.

**Parameters:** None

**Returns:**
- Report of detected extension IDs and locations
- Installation instructions for native messaging

**Example:**
```python
find_extension_id()
# → "Chrome Tab Reader Extension Detected!
#    Extension ID: abcdefghijklmnopqrstuvwxyz123456
#    Version: 1.0.0
#    ..."
```

**When to Use:**
- Setting up native messaging host
- Verifying extension installation
- Getting extension ID for configuration

---

## Setup Guide

### Prerequisites

- **Chrome/Chromium browser** - Latest stable version
- **Chrome Tab Reader extension** - Installed and loaded
- **Python 3.8+** - For running the MCP server
- **uv** - Python package manager (recommended)
- **Ollama** - Local AI model server

### Step 1: Install Chrome Extension

```bash
# Navigate to repository
cd chrome-tab-mcp

# Install Node.js dependencies (for extension libraries)
npm install

# Load extension in Chrome:
# 1. Open chrome://extensions/
# 2. Enable "Developer mode" (top right)
# 3. Click "Load unpacked"
# 4. Select the extension/ directory
```

### Step 2: Install Native Messaging Host

```bash
# Get extension ID
# Open Chrome extension popup or use find_extension_id() tool after server starts

# Linux/macOS
./install_native_host.sh <extension-id>

# Windows PowerShell
.\install_native_host.ps1 <extension-id>
```

### Step 3: Install Ollama

Download and install from [ollama.ai](https://ollama.ai):

```bash
# Install Ollama (follow platform-specific instructions)

# Pull a model (examples)
ollama pull llama2           # Small, fast
ollama pull qwen2.5:7b       # Good balance
ollama pull qwen2.5:32b      # Larger, more capable

# Start Ollama server (usually starts automatically)
ollama serve
```

### Step 4: Configure MCP Server

**Option A: Environment Variables**

Create `.env` file in repository root:

```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
# Optional: BRIDGE_AUTH_TOKEN=your-token-here
```

**Option B: Command-Line Arguments**

```bash
uv run chrome_tab_mcp_server.py \
  --ollama-url http://localhost:11434 \
  --model llama2
```

### Step 5: Configure Claude Code

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

### Step 6: Start Native Host (if not auto-started)

The native host bridges the extension and MCP server:

```bash
# Default (no authentication)
python chrome_tab_native_host.py

# With authentication
python chrome_tab_native_host.py --require-auth
```

### Step 7: Verify Setup

Open Claude Code and ask:

> "Use check_connection_status to verify Chrome Tab Reader is working"

You should see all components connected.

---

## Usage Examples

### Example 1: Summarize Current Webpage

**User:** "Summarize the current webpage I have open in Chrome"

**Claude Code:** Uses `process_chrome_tab()` tool

**Result:**
```
The page is about Python programming best practices.

Q: What are the main topics covered?
A: The page covers code style, testing, documentation, and error handling.

Q: What is the recommended code style?
A: The page recommends following PEP 8 for consistent formatting.
...
```

---

### Example 2: Extract Structured Data

**User:** "Extract all product names and prices from this e-commerce page"

**Claude Code:** Uses `process_chrome_tab(system_prompt="Extract all product names and prices as JSON")`

**Result:**
```json
{
  "products": [
    {"name": "Widget A", "price": "$19.99"},
    {"name": "Widget B", "price": "$29.99"}
  ]
}
```

---

### Example 3: Get Raw Content for Analysis

**User:** "Show me the raw content from this page so I can analyze it myself"

**Claude Code:** Uses `get_raw_tab_content()`

**Result:**
```
Title: Example News Article
URL: https://example.com/article
Content length: 15234 characters

--- Content ---
The latest developments in AI technology...
[full article text]
```

---

### Example 4: Troubleshoot Connection Issues

**User:** "Chrome Tab Reader isn't working"

**Claude Code:** Uses `check_connection_status()`

**Result:**
```
=== Chrome Tab Reader Connection Status ===

1. Native Messaging Bridge:
   ✗ Connection failed
   → Check Chrome is running and extension is loaded

2. Ollama Server:
   ✓ Ollama server is reachable
   ✓ Model 'llama2' is available

3. Chrome Extension:
   ✓ Extension found (1 installation)
```

**Claude Code:** "The native messaging bridge isn't connected. Please ensure Chrome is running and the extension is loaded."

---

## Configuration

### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `OLLAMA_BASE_URL` | Yes* | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Yes* | Ollama model name | `llama2`, `qwen2.5:7b` |
| `BRIDGE_AUTH_TOKEN` | No | Auth token for native bridge | `your-token-here` |
| `CHROME_TAB_LOG_EXCLUDE_URLS` | No | URLs to exclude from logs | `example.com,test.local` |

*Required via environment variable or command-line argument

### Command-Line Arguments

```bash
uv run chrome_tab_mcp_server.py --help

Options:
  --ollama-url URL       Ollama server URL (required)
  --model MODEL          Ollama model name (required)
  --bridge-auth-token    Auth token for native bridge (optional)
```

### Model Selection

Choose an Ollama model based on your needs:

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| `llama2` | 3.8 GB | Fast | Good | General summarization |
| `qwen2.5:7b` | 4.7 GB | Medium | Better | Structured extraction |
| `qwen2.5:32b` | 20 GB | Slow | Best | Complex analysis |

**Recommendation:** Start with `llama2` for speed, upgrade to `qwen2.5:7b` for better quality.

---

## Troubleshooting

### Error: "Cannot connect to Ollama server"

**Cause:** Ollama is not running or wrong URL

**Solution:**
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve

# If using different host/port, update configuration
export OLLAMA_BASE_URL=http://192.168.1.100:11434
```

---

### Error: "Failed to connect to native messaging bridge"

**Cause:** Chrome not running, extension not loaded, or native host not installed

**Solution:**
```bash
# 1. Check Chrome is running
# Open Chrome browser

# 2. Verify extension is loaded
# Visit chrome://extensions/
# Look for "Chrome Tab Reader" with green checkmark

# 3. Check native host is installed
# Linux/macOS
ls ~/.config/google-chrome/NativeMessagingHosts/

# Windows
dir %APPDATA%\Google\Chrome\NativeMessagingHosts\

# 4. Reinstall native host if needed
./install_native_host.sh <extension-id>
```

---

### Error: "No content retrieved from Chrome tab"

**Cause:** No active tab, page is empty, or extraction failed

**Solution:**
```bash
# 1. Open a webpage in Chrome
# Navigate to any website (e.g., https://example.com)

# 2. Ensure page has loaded completely
# Wait for page to finish loading

# 3. Check browser console for errors
# Open Chrome DevTools (F12)
# Check for extension errors

# 4. Try simpler extraction
# Use get_raw_tab_content() to bypass AI processing
```

---

### Error: "Model not found"

**Cause:** Specified Ollama model is not installed

**Solution:**
```bash
# List available models
ollama list

# Pull the model you need
ollama pull llama2

# Or use a model you already have
export OLLAMA_MODEL=<installed-model-name>
```

---

### MCP Server Won't Start

**Cause:** Missing dependencies or configuration

**Solution:**
```bash
# Install dependencies
uv sync

# Check Python version
python --version  # Should be 3.8+

# Test server manually
uv run chrome_tab_mcp_server.py \
  --ollama-url http://localhost:11434 \
  --model llama2

# Check logs
tail -f mcp_server.log
```

---

### Slow Performance

**Cause:** Large pages, slow model, or network issues

**Solution:**
```bash
# Use faster model
export OLLAMA_MODEL=llama2  # Faster than qwen2.5:32b

# Reduce timeout for DOM stability
# (Edit extension/content_script.js if needed)

# Use raw content extraction
# get_raw_tab_content() is faster (no AI processing)
```

---

## Advanced Topics

### Custom System Prompts

Create specialized analysis by providing custom system prompts:

```python
# Sentiment analysis
process_chrome_tab(system_prompt="Analyze the sentiment of this article. Is it positive, negative, or neutral? Explain why.")

# Code extraction
process_chrome_tab(system_prompt="Extract all code snippets and identify the programming language for each.")

# Fact checking
process_chrome_tab(system_prompt="List all factual claims made in this article with their supporting evidence.")

# Translation summary
process_chrome_tab(system_prompt="Summarize this page in Spanish in 5 sentences.")
```

### Using Different Ollama Servers

Run Ollama on a different machine for better performance:

```bash
# Start Ollama on powerful server
# On server (192.168.1.100)
ollama serve --host 0.0.0.0

# Configure MCP to use remote Ollama
export OLLAMA_BASE_URL=http://192.168.1.100:11434
```

### Authentication for Native Bridge

Enable authentication for additional security:

```bash
# 1. Start native host with auth requirement
python chrome_tab_native_host.py --require-auth

# 2. Get token from extension popup
# Click extension icon, copy "Auth Token"

# 3. Configure MCP server
export BRIDGE_AUTH_TOKEN=<token-from-extension>
```

### Multiple Chrome Profiles

The MCP server searches all Chrome profiles. Use `find_extension_id()` to see all installations:

```python
find_extension_id()
# → Shows extension in all profiles
```

If extension is in multiple profiles, the first one found will be used.

### Logging Configuration

Adjust logging for debugging:

```python
# Edit chrome_tab_mcp_server.py
logging.basicConfig(
    level=logging.DEBUG,  # Change to INFO, WARNING, or ERROR
    ...
)

# Exclude specific URLs from logs (privacy)
export CHROME_TAB_LOG_EXCLUDE_URLS="privatesite.com,internal.company.local"
```

### Performance Tuning

Optimize for your workload:

**For Speed:**
- Use `llama2` model (smaller, faster)
- Use `get_raw_tab_content()` when AI processing not needed
- Reduce DOM stability timeout in extension

**For Quality:**
- Use `qwen2.5:32b` model (larger, slower, better)
- Use detailed system prompts
- Allow full three-phase extraction time

**For Large Pages:**
- Increase Ollama timeout (currently 5 minutes)
- Use streaming if available
- Process raw content in chunks

---

## Related Documentation

- [Main README](README.md) - Project overview and quick start
- [Extension Architecture](extension/ARCHITECTURE.md) - Extension internals
- [Native Messaging Setup](NATIVE_MESSAGING_SETUP.md) - Detailed bridge setup
- [Access Control Setup](ACCESS_CONTROL_SETUP.md) - Token authentication
- [CLAUDE.md](CLAUDE.md) - AI assistant development guide

---

## Support

For issues or questions:

1. **Check connection status**: Use `check_connection_status()` tool
2. **Review logs**: Check `mcp_server.log` in repository root
3. **GitHub Issues**: [chrome-tab-mcp/issues](https://github.com/russellpierce/chrome-tab-mcp/issues)

---

**Last Updated:** 2025-11-18
**Version:** 1.0
**Author:** Russell Pierce (with AI assistance)
