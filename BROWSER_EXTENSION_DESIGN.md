# Chrome Tab Reader Browser Extension Design

## Overview

A Chrome/Chromium browser extension that provides cross-platform (Mac/Windows/Linux) access to the Chrome Tab Reader MCP server. The extension directly communicates with a locally-running MCP server via HTTP, extracting webpage content and sending it for AI analysis.

**Key Advantage:** True zero-friction cross-platform support. Install once, use normally. No special Chrome flags, no profile setup, no AppleScript, no platform-specific code.

## Current Architecture vs Extension Architecture

### Current State (AppleScript-only)
```
Claude Code → MCP Server → AppleScript → Chrome DOM
                ↓
            Ollama Server
```

### Proposed Extension Architecture
```
Chrome Tab Reader Extension → localhost MCP Server → Ollama Server
(All platforms)                    ↑
                          (Claude Code not required)
```

**Key Innovation:** The extension can run independently or work with Claude Code MCP protocol.

## Extension Architecture

### Component Structure

```
Browser Extension (Manifest v3)
├── content_script.js
│   └── Extracts text from active tab DOM
├── popup.html / popup.js
│   └── User interface for analysis options
├── service_worker.js
│   └── Handles background tasks, MCP communication
├── styles/
│   └── popup.css
└── manifest.json
```

### Data Flow

```
1. User opens extension popup
   ↓
2. Shows options: system_prompt, start keyword, end keyword
   ↓
3. User clicks "Analyze"
   ↓
4. Content script extracts: document.body.innerText from active tab
   ↓
5. Service worker sends HTTP POST to localhost MCP server:
   POST http://127.0.0.1:3000/tools/process_chrome_tab
   {
     "system_prompt": "...",
     "start": "...",
     "end": "..."
   }
   ↓
6. MCP server processes:
   - Runs AppleScript OR direct local processing
   - Calls Ollama
   - Returns analysis
   ↓
7. Extension receives response and displays in popup
```

## API Design: Extension ↔ MCP Server

### HTTP Interface for Extension

Since the MCP server uses the Model Context Protocol (designed for Claude), we need to expose an HTTP endpoint for the extension.

**Option A: Add HTTP REST endpoint to MCP server** (Recommended)

```python
# New endpoint in chrome_tab_mcp_server.py
@app.post("/tools/process_chrome_tab")
async def http_process_chrome_tab(
    system_prompt: str = None,
    start: str = None,
    end: str = None,
    content: str = None  # Extension passes extracted content
) -> str:
    """
    HTTP endpoint for browser extension.
    Extension provides extracted content directly.
    """
    # Process with Ollama and return analysis
```

**Extension sends raw content:**
```javascript
// Extension API call
const response = await fetch('http://127.0.0.1:3000/tools/process_chrome_tab', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        content: document.body.innerText,
        system_prompt: userInputPrompt,
        start: userStartKeyword,
        end: userEndKeyword
    })
});

const analysis = await response.json();
```

**Option B: Reuse existing MCP protocol**

More complex; would require extension to implement MCP client protocol. Not recommended for simplicity.

### Configuration for Extension

Extension needs to know where the MCP server is running.

**Configuration Method 1: Default localhost**
```
http://127.0.0.1:3000  (default, no configuration needed)
```

**Configuration Method 2: Settings page**
```
Extension settings page allows user to configure:
- MCP Server URL
- Default system prompt
- Save other preferences
```

**Configuration file (extension_config.json)**
```json
{
  "mcp_server_url": "http://127.0.0.1:3000",
  "default_system_prompt": "Process the attached webpage...",
  "connect_timeout_ms": 5000,
  "operation_timeout_ms": 300000
}
```

## Extension UI Design

### Popup Interface (when extension icon clicked)

```
┌─────────────────────────────────────┐
│  Chrome Tab Reader                  │
├─────────────────────────────────────┤
│                                     │
│ System Prompt:                      │
│ ┌────────────────────────────────┐  │
│ │ [Custom prompt text area]      │  │
│ │ [or select "Default"]          │  │
│ └────────────────────────────────┘  │
│                                     │
│ Filter Content (Optional):          │
│ From keyword: [_____________]       │
│ To keyword:   [_____________]       │
│                                     │
│ [Analyze]  [Settings]               │
│                                     │
└─────────────────────────────────────┘
```

### Results Display

```
┌─────────────────────────────────────┐
│ Analysis Results                    │
├─────────────────────────────────────┤
│                                     │
│ [Processing...]                     │
│                                     │
│ [or on completion]                  │
│                                     │
│ <scroll analysis text>              │
│                                     │
│ [Copy to Clipboard]  [Close]        │
│                                     │
└─────────────────────────────────────┘
```

## Manifest v3 Configuration

```json
{
  "manifest_version": 3,
  "name": "Chrome Tab Reader",
  "version": "1.0.0",
  "description": "Analyze webpage content with AI",
  "permissions": [
    "activeTab",
    "scripting",
    "storage"
  ],
  "host_permissions": [
    "http://127.0.0.1:3000/*",
    "http://localhost:3000/*"
  ],
  "action": {
    "default_popup": "popup.html",
    "default_title": "Chrome Tab Reader"
  },
  "background": {
    "service_worker": "service_worker.js"
  },
  "icons": {
    "16": "images/icon-16.png",
    "48": "images/icon-48.png",
    "128": "images/icon-128.png"
  }
}
```

## Implementation Components

### 1. Content Script (content_script.js)

```javascript
// Extracts text from active tab
// Runs in page context (can access DOM directly)

function extractPageContent() {
    return document.body.innerText;
}

function extractContentBetweenKeywords(content, startKeyword, endKeyword) {
    const startIdx = content.toLowerCase().indexOf(startKeyword.toLowerCase());
    if (startIdx === -1) return "";

    const afterStart = content.substring(startIdx + startKeyword.length);
    const endIdx = afterStart.toLowerCase().indexOf(endKeyword.toLowerCase());
    if (endIdx === -1) return "";

    return afterStart.substring(0, endIdx).trim();
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "extractContent") {
        const content = extractPageContent();
        sendResponse({ content: content });
    }
    else if (request.action === "extractFiltered") {
        const content = extractPageContent();
        const filtered = extractContentBetweenKeywords(
            content,
            request.startKeyword,
            request.endKeyword
        );
        sendResponse({ content: filtered });
    }
});
```

### 2. Service Worker (service_worker.js)

```javascript
// Handles communication with MCP server

const MCP_SERVER_URL = "http://127.0.0.1:3000";

async function analyzePage(content, systemPrompt, startKeyword, endKeyword) {
    try {
        const response = await fetch(`${MCP_SERVER_URL}/tools/process_chrome_tab`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                content: content,
                system_prompt: systemPrompt,
                start: startKeyword,
                end: endKeyword
            }),
            timeout: 300000  // 5 minute timeout
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data.analysis || data;
    } catch (error) {
        return `Error: ${error.message}`;
    }
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener(async (request, sender, sendResponse) => {
    if (request.action === "analyze") {
        const result = await analyzePage(
            request.content,
            request.systemPrompt,
            request.startKeyword,
            request.endKeyword
        );
        sendResponse({ result: result });
    }
});
```

### 3. Popup UI (popup.html)

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <link rel="stylesheet" href="styles/popup.css">
</head>
<body>
    <div class="container">
        <h2>Chrome Tab Reader</h2>

        <form id="analysisForm">
            <div class="form-group">
                <label for="systemPrompt">System Prompt:</label>
                <textarea id="systemPrompt"
                          placeholder="How should the AI analyze this page?"
                          rows="3"></textarea>
                <small><a href="#" id="useDefault">Use default</a></small>
            </div>

            <div class="form-group">
                <label for="startKeyword">From keyword (optional):</label>
                <input type="text" id="startKeyword"
                       placeholder="Start extraction from...">
            </div>

            <div class="form-group">
                <label for="endKeyword">To keyword (optional):</label>
                <input type="text" id="endKeyword"
                       placeholder="End extraction at...">
            </div>

            <button type="submit" class="btn-analyze">Analyze</button>
            <button type="button" class="btn-settings">Settings</button>
        </form>

        <div id="results" class="results hidden">
            <h3>Analysis Results</h3>
            <div id="resultContent"></div>
            <button type="button" class="btn-copy">Copy to Clipboard</button>
            <button type="button" class="btn-close">Close</button>
        </div>

        <div id="loading" class="loading hidden">
            <p>Processing...</p>
        </div>
    </div>

    <script src="popup.js"></script>
</body>
</html>
```

### 4. Popup Script (popup.js)

```javascript
const DEFAULT_SYSTEM_PROMPT =
    "You are a helpful AI assistant. Process the attached webpage. " +
    "Think about the questions someone might ask of the contents on this page and provide the answers. " +
    "Certainly extract any key information that does not fit in the question and response format. " +
    "Your total response must be smaller than the contents of the page you were provided.";

document.getElementById('analysisForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const systemPrompt = document.getElementById('systemPrompt').value || DEFAULT_SYSTEM_PROMPT;
    const startKeyword = document.getElementById('startKeyword').value;
    const endKeyword = document.getElementById('endKeyword').value;

    // Show loading state
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('results').classList.add('hidden');

    // Get content from active tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    chrome.tabs.sendMessage(tab.id, {
        action: startKeyword || endKeyword ? "extractFiltered" : "extractContent",
        startKeyword: startKeyword,
        endKeyword: endKeyword
    }, (response) => {
        // Send to MCP server
        chrome.runtime.sendMessage({
            action: "analyze",
            content: response.content,
            systemPrompt: systemPrompt,
            startKeyword: startKeyword,
            endKeyword: endKeyword
        }, (result) => {
            displayResults(result.result);
        });
    });
});

document.getElementById('useDefault').addEventListener('click', (e) => {
    e.preventDefault();
    document.getElementById('systemPrompt').value = DEFAULT_SYSTEM_PROMPT;
});

function displayResults(analysis) {
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('results').classList.remove('hidden');
    document.getElementById('resultContent').textContent = analysis;
}

document.querySelector('.btn-copy').addEventListener('click', () => {
    const text = document.getElementById('resultContent').textContent;
    navigator.clipboard.writeText(text);
    alert('Copied to clipboard!');
});

document.querySelector('.btn-close').addEventListener('click', () => {
    document.getElementById('results').classList.add('hidden');
});

document.querySelector('.btn-settings').addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
});
```

## Consolidation Strategy: Extension vs AppleScript

### Option 1: Extension as Primary (Recommended)

```
macOS:   Extension only (drop AppleScript)
Windows: Extension only (no PowerShell needed)
Linux:   Extension only (no xdotool needed)

Benefits:
✅ Single codebase for all platforms
✅ Zero platform-specific code
✅ Easier to maintain
✅ Perfect UX (install once, use normally)
✅ No special configuration needed

Trade-offs:
⚠️ Users must install extension (vs AppleScript being native)
⚠️ Requires Chrome Web Store submission
⚠️ Won't work with non-Chromium browsers
```

### Option 2: Extension + AppleScript (Parallel)

```
macOS:   Both available (AppleScript for CLI/automation, Extension for UI)
Windows: Extension only
Linux:   Extension only

Benefits:
✅ AppleScript for backward compatibility
✅ Extension for user convenience
✅ Users choose their preference
✅ CLI automation still works

Trade-offs:
⚠️ Two implementations to maintain
⚠️ Potential inconsistency
⚠️ More code to test
```

### Option 3: AppleScript → Extension (Sunset Plan)

```
Phase 1: Release extension (parallel with AppleScript)
Phase 2: Mark AppleScript as "legacy"
Phase 3: Deprecate and remove AppleScript in future version

Rationale:
✅ Smooth transition for existing users
✅ New users get better experience
✅ Eventually converge on single solution
```

## Recommendation: Option 1 - Extension as Primary

**Why:**

1. **True cross-platform** - Same code on every OS
2. **Perfect UX** - Install once, use like any other extension
3. **No friction** - No special Chrome flags, no profiles, no AppleScript permissions
4. **Lower maintenance** - Single codebase vs 3 platform implementations
5. **More reliable** - Direct DOM access vs AppleScript fragility
6. **Future-proof** - Works with future Chrome versions, CDP issues don't affect us

**Migration Path:**

- Phase 1: Develop and test extension thoroughly
- Phase 2: Submit to Chrome Web Store
- Phase 3: Document AppleScript as deprecated
- Phase 4: Remove AppleScript in v2.0

## Changes to MCP Server

### New HTTP Endpoint

Add to `chrome_tab_mcp_server.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow requests from extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["chrome-extension://*"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

@app.post("/tools/process_chrome_tab")
async def http_process_chrome_tab(
    content: str,
    system_prompt: str = None,
    start: str = None,
    end: str = None
):
    """HTTP endpoint for browser extension."""

    # If system_prompt not provided, use default
    if not system_prompt:
        system_prompt = DEFAULT_SYSTEM_PROMPT

    # Filter content if keywords provided
    if start or end:
        content = filter_content(content, start, end)

    # Call Ollama
    response = await call_ollama(content, system_prompt)

    return {"analysis": response}
```

### Dual Interface

- **MCP Protocol** (for Claude Code)
- **HTTP REST** (for browser extension)

Both interfaces call the same underlying logic.

## Browser Extension Distribution

### Chrome Web Store Submission

1. Prepare extension package
2. Create developer account
3. Submit to Chrome Web Store
4. Handle review process (1-3 days typically)
5. Publish on Web Store
6. Users install with one click

### Private Distribution (if not on Web Store)

Users can load extension locally:
1. Download extension code
2. Go to `chrome://extensions/`
3. Enable "Developer Mode"
4. Click "Load unpacked"
5. Select extension directory

## Comparison: Final Trade-offs

| Aspect | AppleScript | CDP | Browser Extension |
|--------|-------------|-----|-------------------|
| **Cross-platform** | ❌ macOS only | ✅ All platforms | ✅ All platforms |
| **Setup friction** | Zero (built-in) | Medium-High (flags + profile) | Low (install once) |
| **Recurring friction** | Zero | High (launch flag each time) | Zero |
| **Maintenance** | 1 code path | 1 code path | 1 code path |
| **Reliability** | Good (but AppleScript fragile) | Medium (CDP limitations) | Excellent (native) |
| **UX** | CLI-focused | Requires config | GUI-focused |
| **Distribution** | Manual setup | Manual setup | Chrome Web Store |
| **Works without MCP running** | N/A | No (needs CDP) | No (needs MCP) |

## Conclusion

**Strongly recommend Browser Extension as primary implementation.**

- Single cross-platform codebase
- Perfect user experience after one-time install
- Direct DOM access (most reliable)
- Easy distribution via Chrome Web Store
- Can sunset AppleScript with clear migration path
- Future-proof (not dependent on AppleScript fragility or CDP issues)

---

**Status:** Design proposal
**Date:** 2025-11-13
**Next Step:** Decide on extension vs AppleScript consolidation strategy
