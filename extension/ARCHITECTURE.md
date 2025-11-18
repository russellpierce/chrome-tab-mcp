# Chrome Tab Reader Extension - Architecture

> **Note:** This document is AI-authored with very limited human oversight.

## Overview

A Chrome/Chromium browser extension that provides cross-platform (Mac/Windows/Linux) webpage content extraction and AI analysis. The extension communicates with a localhost MCP server to process content through Ollama.

## Design Philosophy

- **Single responsibility:** Extract page content reliably
- **Zero setup friction:** Install extension, use immediately
- **Sophisticated extraction:** Handle lazy-loading, SPAs, noise removal
- **Graceful degradation:** Fallback to innerText if advanced extraction fails
- **Security first:** Sanitize all extracted content

## Communication Architecture

### Extension as Service Provider (Server-Initiated)

```
Claude Code
    ↓
MCP Server (calls process_chrome_tab via MCP protocol)
    ↓
MCP Server makes HTTP request to Extension API
    POST http://127.0.0.1:8888/api/extract
    {
      "action": "extract_current_tab",
      "strategy": "three-phase"
    }
    ↓
Extension receives request
    ↓
Content Script executes 3-phase extraction
    Phase 1: Trigger lazy-loading
    Phase 2: Wait for DOM stability
    Phase 3: Extract with Readability.js
    ↓
Extension returns HTTP response to MCP Server
    {
      "content": "extracted text",
      "status": "success",
      "extraction_time_ms": 4523
    }
    ↓
MCP Server processes with Ollama
    ↓
MCP Server returns analysis to Claude Code
```

**Key Points:**
- Extension acts as **service provider** (HTTP server on localhost:8888)
- MCP server is the **client** requesting content
- MCP server initiates all requests
- Extension can extract current tab OR navigate to URL
- Content flows: Extension → MCP Server → Ollama → Claude Code

### Extension API Endpoints

Extension listens on `http://127.0.0.1:8888` and provides:

**1. Extract Current Tab**
```
POST /api/extract
{
  "action": "extract_current_tab",
  "strategy": "three-phase"  // or "simple" for just innerText
}

Response:
{
  "content": "page text content",
  "title": "page title",
  "url": "https://example.com",
  "extraction_time_ms": 4500,
  "status": "success"
}
```

**2. Open URL and Extract**
```
POST /api/navigate_and_extract
{
  "url": "https://example.com/article",
  "strategy": "three-phase",
  "wait_for_ms": 5000  // optional: extra wait after page loads
}

Response:
{
  "content": "page text content",
  "title": "page title",
  "url": "https://example.com/article",
  "extraction_time_ms": 8200,
  "status": "success"
}
```

**3. Get Current Tab Info**
```
GET /api/current_tab

Response:
{
  "url": "https://example.com",
  "title": "Example Domain",
  "tab_id": 123456
}
```

**4. Health Check**
```
GET /api/health

Response:
{
  "status": "ok",
  "extension_version": "1.0.0"
}
```

### Why This Architecture Is Better

| Aspect | Old (Wrong) | New (Correct) |
|--------|------------|--------------|
| **Initiation** | Extension pulls (user-driven) | MCP server pulls (programmatic) |
| **Navigation** | Manual or not supported | Extension handles URL opens |
| **Multi-page** | Can't extract across URLs | MCP server can navigate and extract multiple pages |
| **Error handling** | Extension shows popup errors | MCP server handles errors properly |
| **Integration** | Extension is standalone | Extension is browser automation service |
| **Claude Code usage** | Limited (popup only) | Full power (extract any page, navigate) |

### WebSocket Alternative (Future)

For streaming large content or real-time updates:

```javascript
const ws = new WebSocket('ws://127.0.0.1:8888/api/stream-extract');
ws.send(JSON.stringify({
    action: "extract_current_tab",
    stream_large_content: true
}));
ws.onmessage = (event) => {
    const chunk = JSON.parse(event.data);
    // Handle streamed content chunks
};
```

**Decision:** v1 uses HTTP for simplicity. WebSocket available as upgrade in v2.

## Component Architecture

```
extension/
├── manifest.json              # Manifest v3 configuration
├── service_worker.js          # HTTP server on port 8888 (main service)
│   ├── POST /api/extract
│   ├── POST /api/navigate_and_extract
│   ├── GET /api/current_tab
│   └── GET /api/health
├── content_script.js          # DOM extraction (3-phase strategy)
│   ├── Phase 1: Trigger lazy-loading
│   ├── Phase 2: Wait for DOM stability
│   └── Phase 3: Extract with Readability.js
├── lib/
│   ├── readability.min.js    # Mozilla Readability.js
│   └── dompurify.min.js      # DOMPurify sanitizer
├── popup.html                 # Optional: Manual testing UI
├── popup.js                   # Optional: Manual extraction trigger
├── styles/
│   └── popup.css
├── images/
│   ├── icon-16.png
│   ├── icon-48.png
│   └── icon-128.png
├── ARCHITECTURE.md           # This file
├── SETUP.md                  # Installation & configuration
├── TESTING.md                # Testing procedures
└── DEVELOPMENT.md            # Development guide
```

**Service Worker Role:**
- Runs as background service (persists even when popup is closed)
- Starts HTTP server on `http://127.0.0.1:8888`
- Receives requests from MCP server
- Delegates extraction to content script
- Handles navigation (chrome.tabs API)
- Returns results to MCP server

**Content Script Role:**
- Runs in page context (has DOM access)
- Performs actual extraction when requested
- Can't access cross-origin resources
- Runs 3-phase extraction pipeline

**Popup Role:**
- Optional manual interface for testing
- Not required for normal operation
- Useful for debugging extraction strategy
- Shows extraction logs and timing

## Content Extraction Strategy

Three-phase extraction designed to capture full, clean webpage content:

### Phase 1: Trigger Lazy-Loading (2-5 seconds)

Simulates user scrolling to trigger lazy-loading patterns:

```javascript
async function triggerLazyLoading() {
    let lastHeight = document.body.scrollHeight;

    // Scroll to bottom up to 5 times
    for (let i = 0; i < 5; i++) {
        window.scrollTo(0, document.body.scrollHeight);
        await sleep(500);

        // Check if new content loaded
        let newHeight = document.body.scrollHeight;
        if (newHeight === lastHeight) break; // No more content
        lastHeight = newHeight;
    }

    window.scrollTo(0, 0); // Return to top
}
```

**Handles:**
- Infinite scroll pages (Twitter, Reddit, etc.)
- Pagination "Load More" buttons
- Lazy-loaded image galleries

### Phase 2: Wait for DOM Stability (up to 30 seconds)

Uses MutationObserver to detect when dynamic content stops loading:

```javascript
async function waitForDOMStability(timeoutMs = 30000) {
    // Resolves when DOM hasn't changed for 2 seconds
    // Hard timeout at 30 seconds

    return new Promise((resolve) => {
        let stableTimer;
        const observer = new MutationObserver((mutations) => {
            clearTimeout(stableTimer);

            // Reset timer: wait 2 seconds without changes
            stableTimer = setTimeout(() => {
                observer.disconnect();
                resolve();
            }, 2000);
        });

        // Only track structural changes, not style/class
        observer.observe(document.documentElement, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['src', 'href', 'data-src']
        });

        // Hard timeout after 30 seconds
        setTimeout(() => {
            observer.disconnect();
            resolve();
        }, timeoutMs);
    });
}
```

**Handles:**
- Single-page apps (React, Vue) still rendering
- Form autofill and dynamic updates
- Live feeds and real-time content
- Image lazy-loading (data-src tracking)

### Phase 3: Extract & Clean with Readability.js

Uses Mozilla's proven content extraction algorithm:

```javascript
function extractCleanContent() {
    try {
        const reader = new Readability(document.cloneNode(true));
        const article = reader.parse();

        if (article && article.textContent) {
            // Sanitize to prevent injection
            return DOMPurify.sanitize(article.textContent);
        }
    } catch (error) {
        console.warn("Readability failed:", error);
    }

    // Fallback to simple innerText
    return document.body.innerText;
}
```

**Benefits:**
- ✅ Removes navigation, sidebars, ads, comments
- ✅ Extracts main article/content only
- ✅ Proven by Firefox Reader View
- ✅ ~15KB gzipped (minimal overhead)

## API Interface: Extension ↔ MCP Server

Extension acts as HTTP **server** on port 8888. MCP server acts as **client** making requests.

### Extension API Endpoints

**Base URL:** `http://127.0.0.1:8888`

#### POST /api/extract

Extract content from the currently active tab.

**Request:**
```json
{
  "action": "extract_current_tab",
  "strategy": "three-phase"
}
```

**Response:**
```json
{
  "status": "success",
  "content": "full page text content...",
  "title": "Page Title",
  "url": "https://example.com/page",
  "extraction_time_ms": 4523,
  "strategy_used": "three-phase"
}
```

#### POST /api/navigate_and_extract

Navigate to a URL and extract its content.

**Request:**
```json
{
  "action": "navigate_and_extract",
  "url": "https://example.com/article",
  "strategy": "three-phase",
  "wait_for_ms": 3000
}
```

**Response:**
```json
{
  "status": "success",
  "content": "full page text content...",
  "title": "Article Title",
  "url": "https://example.com/article",
  "extraction_time_ms": 7200,
  "navigation_time_ms": 2500,
  "strategy_used": "three-phase"
}
```

#### GET /api/current_tab

Get info about the currently active tab.

**Response:**
```json
{
  "tab_id": 123456,
  "url": "https://example.com",
  "title": "Example Domain",
  "is_loading": false
}
```

#### GET /api/health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "extension_version": "1.0.0",
  "port": 8888,
  "readability_available": true,
  "dompurify_available": true
}
```

### Configuration

MCP server needs to know the extension is at `http://127.0.0.1:8888`.

Configure in chrome_tab_mcp_server.py:
```python
EXTENSION_API_URL = "http://127.0.0.1:8888"

def process_chrome_tab(system_prompt=None, start=None, end=None):
    # Make request to extension
    response = requests.post(
        f"{EXTENSION_API_URL}/api/extract",
        json={"action": "extract_current_tab", "strategy": "three-phase"}
    )
    content = response.json()["content"]

    # Process with Ollama
    analysis = call_ollama(content, system_prompt)
    return analysis
```

## Message Flow

### MCP Server → Extension (Initial Request)

```
MCP Server (called by Claude Code)
    ↓
Makes HTTP POST to Extension /api/extract
{
  "action": "extract_current_tab",
  "strategy": "three-phase"
}
```

### Extension Processes Request

```
Service Worker receives request
    ↓
Sends message to Content Script on active tab
    {
      "action": "extractContent",
      "strategy": "three-phase"
    }
    ↓
Content Script runs 3-phase extraction
    Phase 1: Trigger lazy-loading
    Phase 2: Wait for DOM stability
    Phase 3: Extract with Readability.js
    ↓
Content Script returns extracted content to Service Worker
```

### Extension → MCP Server (Response)

```
Service Worker receives content from Content Script
    ↓
HTTP Response to MCP Server
{
  "status": "success",
  "content": "...",
  "title": "...",
  "url": "...",
  "extraction_time_ms": 4523
}
```

### MCP Server → Ollama → Claude Code

```
MCP Server receives content from Extension
    ↓
Calls Ollama API with content
    ↓
Ollama returns analysis
    ↓
MCP Server returns analysis to Claude Code
```

### Multi-Page Example

```
MCP Server needs to analyze multiple articles

Loop:
  1. POST /api/navigate_and_extract {"url": "article1.com"}
  2. Wait for response (7-10 seconds)
  3. Process content with Ollama
  4. Store result
  5. POST /api/navigate_and_extract {"url": "article2.com"}
  6. Repeat...

Finally: Return aggregated analysis to Claude Code
```

## Error Handling

### Graceful Degradation

| Error | Handling |
|-------|----------|
| Lazy-loading fails | Continue to DOM stability phase |
| DOM stability timeout | Exit at 30 seconds and extract anyway |
| Readability fails | Fallback to `document.body.innerText` |
| MCP server offline | Show user-friendly error message |
| Large content | Send anyway (HTTP POST handles large payloads) |
| Timeout from Ollama | Show timeout message after 9 minutes |

### User-Facing Messages

- "Triggering lazy-loading..." (Phase 1)
- "Waiting for page to stabilize..." (Phase 2)
- "Extracting content..." (Phase 3)
- "Processing with AI..." (waiting for Ollama)
- "Analysis complete" (success)
- "Error: [specific message]" (failure)

## Security Considerations

### XSS Prevention

All extracted content is sanitized with **DOMPurify** before sending to server:

```javascript
const clean = DOMPurify.sanitize(article.textContent);
```

### Content Isolation

- Extension only reads text content (no HTML)
- No scripts are executed from extracted content
- No credentials or sensitive data included in requests

### Network Security

- Only connects to localhost (http://127.0.0.1:3000)
- No external network requests
- No API keys or credentials in requests

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Total extraction time | <10 seconds | 2-5s lazy + 0-3min DOM + 0.1s readability |
| Bundle size | <100KB | readability.js ~40KB, dompurify ~10KB |
| Memory usage | <50MB | Monitor during extraction |
| Popup response time | <100ms | Click to extraction start |
| Results display | <500ms | After Ollama returns |

## Browser Compatibility

### Manifest v3 (Modern Standard)

- ✅ Chrome 88+
- ✅ Chromium 88+
- ✅ Edge 88+
- ✅ Brave 1.21+
- ⚠️ Firefox (limited Manifest v3 support, may need fork)

### Platform Support

- ✅ macOS (Intel & Apple Silicon)
- ✅ Windows 10/11
- ✅ Linux (Ubuntu 20.04+)

## Testing Strategy

See `TESTING.md` for comprehensive test plan covering:

- Unit tests (individual extraction phases)
- Integration tests (extension ↔ MCP server)
- End-to-end tests (full workflow)
- Cross-browser testing
- Performance testing
- Security testing
- Error handling scenarios

## Future Enhancements

### v2 Potential Features

1. **Custom Configuration**
   - Settings page to configure MCP server URL
   - Save user preferences (default system prompt, etc.)

2. **Bidirectional Communication**
   - WebSocket connection for Claude Code → Extension triggering
   - More flexible integration with MCP

3. **Content History**
   - Store extraction history
   - Replay previous analyses

4. **Advanced Filtering**
   - UI for complex content filtering
   - Regex pattern matching

5. **Multi-Tab Processing**
   - Extract from multiple tabs
   - Aggregate results

6. **Browser Compatibility**
   - Safari support (requires native messaging)
   - Firefox (Manifest v2 compatibility)

---

**Status:** Production Architecture
**Version:** 1.0
**Last Updated:** November 13, 2025
