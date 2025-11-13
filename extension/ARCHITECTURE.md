# Chrome Tab Reader Extension - Architecture

## Overview

A Chrome/Chromium browser extension that provides cross-platform (Mac/Windows/Linux) webpage content extraction and AI analysis. The extension communicates with a localhost MCP server to process content through Ollama.

## Design Philosophy

- **Single responsibility:** Extract page content reliably
- **Zero setup friction:** Install extension, use immediately
- **Sophisticated extraction:** Handle lazy-loading, SPAs, noise removal
- **Graceful degradation:** Fallback to innerText if advanced extraction fails
- **Security first:** Sanitize all extracted content

## Communication Architecture

### Pull-Based Design (Current)

```
User clicks extension popup
        ↓
Extension extracts content from active tab
        ↓
Extension sends HTTP POST to MCP server
        ↓
MCP Server processes with Ollama
        ↓
MCP Server returns analysis
        ↓
Extension displays results in popup
```

**Key Points:**
- Extension always initiates requests
- MCP server cannot reach out to trigger extension
- Stateless HTTP communication (no persistent connections)
- Works with any network setup

### Future Enhancement: Bidirectional Communication

If future use cases require Claude Code to trigger extension extraction:

```javascript
// Extension would maintain WebSocket connection
const ws = new WebSocket('ws://127.0.0.1:3000/extension');
ws.onmessage = (event) => {
    const { action } = JSON.parse(event.data);
    // Extract and send back
};
```

**Decision:** Not implemented in v1.

## Component Architecture

```
extension/
├── manifest.json              # Manifest v3 configuration
├── popup.html                 # Popup UI
├── popup.js                   # Popup logic & event handlers
├── content_script.js          # DOM extraction (3-phase strategy)
├── service_worker.js          # MCP server communication
├── lib/
│   ├── readability.min.js    # Mozilla Readability.js
│   └── dompurify.min.js      # DOMPurify sanitizer
├── styles/
│   └── popup.css             # Popup styling
├── images/
│   ├── icon-16.png
│   ├── icon-48.png
│   └── icon-128.png
├── ARCHITECTURE.md           # This file
├── SETUP.md                  # Installation & configuration
├── TESTING.md                # Testing procedures
└── DEVELOPMENT.md            # Development guide
```

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

### Phase 2: Wait for DOM Stability (up to 3 minutes)

Uses MutationObserver to detect when dynamic content stops loading:

```javascript
async function waitForDOMStability(timeoutMs = 180000) {
    // Resolves when DOM hasn't changed for 2 seconds
    // Hard timeout at 3 minutes

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

        // Hard timeout after 3 minutes
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

### HTTP Endpoint

Extension sends HTTP POST requests to MCP server:

```
POST http://127.0.0.1:3000/tools/process_chrome_tab
Content-Type: application/json

{
  "content": "extracted page text",
  "system_prompt": "custom analysis instructions",
  "start": "optional: filter from keyword",
  "end": "optional: filter to keyword"
}
```

**Response:**

```json
{
  "analysis": "AI-generated analysis text"
}
```

### Configuration

Extension expects MCP server at `http://127.0.0.1:3000` by default.

Can be customized via extension settings page (future enhancement).

## Message Flow

### Popup → Content Script

```javascript
// Popup sends extraction request
chrome.tabs.sendMessage(tabId, {
    action: "extractContent",
    // or
    action: "extractFiltered",
    startKeyword: "Start section",
    endKeyword: "End section"
});

// Content script responds with extracted content
```

### Content Script → Service Worker

```javascript
// After extraction, send to service worker
chrome.runtime.sendMessage({
    action: "analyze",
    content: extractedContent,
    systemPrompt: userPrompt,
    startKeyword: userStartKw,
    endKeyword: userEndKw
});
```

### Service Worker → MCP Server

```javascript
// Service worker makes HTTP request to MCP server
const response = await fetch('http://127.0.0.1:3000/tools/process_chrome_tab', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        content: extractedContent,
        system_prompt: userPrompt,
        start: userStartKw,
        end: userEndKw
    }),
    timeout: 540000  // 9 minutes (3min extraction + 5min Ollama + buffer)
});

const result = await response.json();
```

## Error Handling

### Graceful Degradation

| Error | Handling |
|-------|----------|
| Lazy-loading fails | Continue to DOM stability phase |
| DOM stability timeout | Exit at 3 minutes and extract anyway |
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
