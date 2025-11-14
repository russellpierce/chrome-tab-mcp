# Browser Extension Testing & Verification Plan

## Communication Architecture Clarification

### Current Design: Pull-Based (One-Way)

```
User clicks extension popup
        ↓
Extension popup sends HTTP request
        ↓
MCP Server receives & processes
        ↓
MCP Server sends HTTP response
        ↓
Extension displays results
```

**Important:** The MCP server **cannot reach out to trigger the extension**. The flow is always initiated by the user clicking the extension popup. The extension pulls content, the server responds.

### Why This Design?

- ✅ Simple, stateless HTTP communication
- ✅ No persistent connections needed
- ✅ Works across different network setups
- ✅ Aligns with browser extension security model
- ✅ No need for service worker to listen for incoming connections

### If Two-Way Communication Needed (Future Enhancement)

If a future use case requires the MCP server to trigger the extension (e.g., from Claude Code to pull specific content), we would need:

```javascript
// Option 1: WebSocket (Bidirectional)
// Extension maintains WebSocket connection to MCP server
// MCP server can send messages to connected extensions
const ws = new WebSocket('ws://127.0.0.1:3000/extension');
ws.onmessage = (event) => {
    // Server sent us a command
    const { action, params } = JSON.parse(event.data);
    if (action === 'extract') {
        extractPageContent().then(content => {
            ws.send(JSON.stringify({ result: content }));
        });
    }
};
```

**Decision:** Not implementing in v1. Can add in v2 if needed.

---

## Test & Verification Plan

### Phase 1: Unit Testing (Individual Components)

#### 1.1 Content Script - Phase 1: Lazy-Loading

**Test:** `lazy-loading.test.js`

```javascript
describe("triggerLazyLoading()", () => {
    test("should detect new content when scrollHeight increases", async () => {
        // Mock page with increasing height
        // Call triggerLazyLoading()
        // Verify scrollTo was called multiple times
        // Verify function exits when height stops changing
    });

    test("should stop after 5 scroll attempts even if content keeps loading", async () => {
        // Mock page with infinite content loading
        // Call triggerLazyLoading()
        // Verify max 5 scroll attempts
    });

    test("should return to top after scrolling", async () => {
        // Call triggerLazyLoading()
        // Verify final scrollTo(0, 0) call
    });
});
```

**Manual Testing:**
- ✅ Test on infinite scroll page (Twitter, Reddit)
- ✅ Test on pagination page (Google Search results)
- ✅ Test on static page (should exit immediately)
- ✅ Verify scroll behavior doesn't interfere with user

#### 1.2 Content Script - Phase 2: DOM Stability

**Test:** `dom-stability.test.js`

```javascript
describe("waitForDOMStability()", () => {
    test("should resolve when DOM hasn't changed for 2 seconds", async () => {
        const observer = new MutationObserver(...);
        // Trigger mutations, wait 2s
        // Verify it resolves before 3-minute timeout
    });

    test("should reset timer on new mutations", async () => {
        // Trigger mutation at 1.5s mark
        // Verify timer resets
        // Continue mutations every 1.5s
        // Verify doesn't resolve until mutations stop
    });

    test("should hard-timeout after 3 minutes", async () => {
        // Mock continuous mutations for 3+ minutes
        // Verify it resolves at exactly 3 minutes
    });

    test("should ignore style/class attribute changes", async () => {
        // Trigger style attribute mutation
        // Verify it doesn't reset stability timer
    });

    test("should observe src/href/data-src changes", async () => {
        // Trigger src attribute mutation
        // Verify it resets stability timer
    });
});
```

**Manual Testing:**
- ✅ Test on page with animations (CSS animations continue)
- ✅ Test on page with lazy-loaded images (data-src updates)
- ✅ Test on page with form autofill updates
- ✅ Test on page with live feeds (continuous mutations)
- ✅ Verify 3-minute timeout works with browser DevTools

#### 1.3 Content Script - Phase 3: Readability Extraction

**Test:** `readability.test.js`

```javascript
describe("extractCleanContent()", () => {
    test("should use Readability.js when available", async () => {
        // Mock page with nav, sidebar, main content
        // Call extractCleanContent()
        // Verify Readability was called
        // Verify nav/sidebar content removed
    });

    test("should fallback to innerText if Readability fails", async () => {
        // Mock Readability to throw error
        // Call extractCleanContent()
        // Verify returns document.body.innerText
    });

    test("should sanitize with DOMPurify", async () => {
        // Mock article content with malicious script tags
        // Call extractCleanContent()
        // Verify DOMPurify.sanitize was called
        // Verify no <script> tags in output
    });

    test("should handle null article gracefully", async () => {
        // Mock Readability.parse() returning null
        // Call extractCleanContent()
        // Verify fallback to innerText
    });
});
```

**Manual Testing:**
- ✅ Test on news article (NY Times, Medium, Hacker News)
- ✅ Test on product page (Amazon, Shopify)
- ✅ Test on documentation (MDN, DevDocs)
- ✅ Test on Reddit thread
- ✅ Test on single-page app (React/Vue loaded content)
- ✅ Verify nav/footer/sidebar removed
- ✅ Compare output: Readability vs innerText

#### 1.4 Content Script - Complete Flow

**Test:** `content-script.test.js`

```javascript
describe("extractPageContent()", () => {
    test("should call all three phases in order", async () => {
        const triggerLazySpy = jest.spyOn(global, 'triggerLazyLoading');
        const waitStableSpy = jest.spyOn(global, 'waitForDOMStability');
        const extractSpy = jest.spyOn(global, 'extractCleanContent');

        await extractPageContent();

        expect(triggerLazySpy).toHaveBeenCalledBefore(waitStableSpy);
        expect(waitStableSpy).toHaveBeenCalledBefore(extractSpy);
    });

    test("should fallback to innerText on error", async () => {
        // Mock all phases to throw
        // Call extractPageContent()
        // Verify returns document.body.innerText
    });

    test("should handle keyword filtering", (done) => {
        chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
            if (request.action === "extractFiltered") {
                expect(extractContentBetweenKeywords).toHaveBeenCalled();
                done();
            }
        });

        chrome.runtime.sendMessage({
            action: "extractFiltered",
            startKeyword: "Start",
            endKeyword: "End"
        });
    });
});
```

---

### Phase 2: Integration Testing (Extension ↔ MCP Server)

#### 2.1 HTTP Endpoint Testing

**Setup:**
```bash
# Start MCP server
python chrome_tab_mcp_server.py --ollama-url http://localhost:11434 --model llama2

# Test endpoint exists
curl http://127.0.0.1:3000/tools/process_chrome_tab
```

**Test:** `http-endpoint.test.js`

```javascript
describe("POST /tools/process_chrome_tab", () => {
    test("should accept content, system_prompt, start, end", async () => {
        const response = await fetch('http://127.0.0.1:3000/tools/process_chrome_tab', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                content: "Sample page content",
                system_prompt: "Analyze this",
                start: null,
                end: null
            })
        });

        expect(response.ok).toBe(true);
        const data = await response.json();
        expect(data).toHaveProperty('analysis');
    });

    test("should handle filtering parameters", async () => {
        const response = await fetch('http://127.0.0.1:3000/tools/process_chrome_tab', {
            method: 'POST',
            body: JSON.stringify({
                content: "Start Middle End",
                start: "Start",
                end: "End",
                system_prompt: "Extract"
            })
        });

        const data = await response.json();
        expect(data.analysis).toContain("Middle");
        expect(data.analysis).not.toContain("Start");
    });

    test("should handle large content payloads", async () => {
        // Create 10MB of content
        const largeContent = "x".repeat(10 * 1024 * 1024);

        const response = await fetch('http://127.0.0.1:3000/tools/process_chrome_tab', {
            method: 'POST',
            body: JSON.stringify({
                content: largeContent,
                system_prompt: "Summarize"
            })
        });

        expect(response.ok).toBe(true);
    });

    test("should timeout after 9 minutes", async () => {
        // This is more of a load test
        // Verify fetch timeout is set to 540000ms
    });
});
```

**Manual Testing:**
- ✅ Start MCP server with Ollama
- ✅ Use curl to test endpoint
- ✅ Verify response format
- ✅ Test with various content sizes (100 bytes, 1KB, 100KB, 1MB)
- ✅ Test timeout behavior (kill Ollama mid-process)

#### 2.2 Service Worker Testing

**Test:** `service-worker.test.js`

```javascript
describe("Service Worker", () => {
    test("should send correct HTTP request to MCP server", async () => {
        const fetchSpy = jest.spyOn(global, 'fetch');

        chrome.runtime.sendMessage({
            action: "analyze",
            content: "Test content",
            systemPrompt: "Analyze",
            startKeyword: null,
            endKeyword: null
        });

        await new Promise(resolve => setTimeout(resolve, 100));
        expect(fetchSpy).toHaveBeenCalledWith(
            'http://127.0.0.1:3000/tools/process_chrome_tab',
            expect.objectContaining({
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
        );
    });

    test("should handle MCP server connection error", async () => {
        // Mock fetch to throw connection error
        // Send analyze message
        // Verify error response sent to popup
    });

    test("should handle timeout from MCP server", async () => {
        // Mock fetch to timeout after 9 minutes
        // Verify user-friendly timeout message
    });
});
```

---

### Phase 3: End-to-End Testing (Extension ↔ MCP Server ↔ Ollama)

#### 3.1 Full Flow Test

**Setup:**
- Chrome running
- MCP server running with Ollama
- Browser extension loaded (unpacked)

**Test Cases:**

**TC-3.1.1: Simple News Article Analysis**
```
1. Navigate to: https://example.com/news-article
2. Click extension popup
3. Leave default system prompt
4. Click "Analyze"
5. Verify:
   - "Triggering lazy-loading..." message appears
   - "Waiting for page to stabilize..." message appears
   - "Extracting content..." message appears
   - Results appear after Ollama processing (2-5 minutes)
   - Results contain article summary
```

**TC-3.1.2: Content Filtering Test**
```
1. Navigate to: https://example.com/long-page
2. Click extension popup
3. Set "From keyword: SECTION 1"
4. Set "To keyword: SECTION 2"
5. Click "Analyze"
6. Verify:
   - Content extracted only from SECTION 1 to SECTION 2
   - Analysis focuses on filtered content
   - Nav/footer not included
```

**TC-3.1.3: Infinite Scroll Page**
```
1. Navigate to: https://twitter.com (or similar infinite scroll)
2. Click extension popup
3. Click "Analyze"
4. Verify:
   - Page scrolls to bottom (observable)
   - New tweets load (observable)
   - Waits for stabilization (2-3 seconds)
   - Content includes recently scrolled tweets
```

**TC-3.1.4: Single-Page App**
```
1. Navigate to: https://react.example.com (React/Vue app)
2. Wait for app to fully load
3. Click extension popup
4. Click "Analyze"
5. Verify:
   - Waits for DOM to stabilize (may take longer for SPA)
   - Extracted content matches what's visible on screen
   - No missing dynamically-loaded components
```

**TC-3.1.5: PDF/Special Pages (Error Handling)**
```
1. Navigate to: PDF file or about:blank
2. Click extension popup
3. Click "Analyze"
4. Verify:
   - Appropriate error message appears
   - Fallback to innerText (or empty content)
   - No crash
```

**TC-3.1.6: Custom System Prompt**
```
1. Navigate to any page
2. Click extension popup
3. Set custom prompt: "Extract the top 3 key points"
4. Click "Analyze"
5. Verify:
   - Ollama receives custom prompt
   - Results follow custom format (3 bullet points)
```

---

### Phase 4: Cross-Browser Testing

**Browsers to Test:**
- ✅ Chrome (latest)
- ✅ Chromium (latest)
- ✅ Edge (latest)
- ✅ Brave (latest)
- ⚠️ Firefox (Manifest v3 compatibility notes)

**Platform Testing:**
- ✅ macOS (primary)
- ✅ Windows 10/11
- ✅ Linux (Ubuntu 22.04+)

**Test:** On each browser/platform combination:
- Extension installs without errors
- Popup displays correctly
- Content script loads
- HTTP requests reach MCP server
- Extraction works (lazy-loading, DOM stability, readability)

---

### Phase 5: Performance Testing

#### 5.1 Extraction Time

**Test:** `performance.test.js`

```javascript
describe("Extraction Performance", () => {
    test("Phase 1 (lazy-loading) should complete in <5 seconds", async () => {
        const start = performance.now();
        await triggerLazyLoading();
        const elapsed = performance.now() - start;
        expect(elapsed).toBeLessThan(5000);
    });

    test("Phase 2 (DOM stability) should complete in <3 minutes", async () => {
        const start = performance.now();
        await waitForDOMStability();
        const elapsed = performance.now() - start;
        expect(elapsed).toBeLessThan(180000);
    });

    test("Phase 3 (readability) should complete in <1 second", async () => {
        const start = performance.now();
        extractCleanContent();
        const elapsed = performance.now() - start;
        expect(elapsed).toBeLessThan(1000);
    });

    test("Total extraction time for typical page <6 seconds", async () => {
        // Typical: 2-3s lazy load + 0.5s DOM stability + 0.1s readability
        // Slow: 5s lazy load + 3min DOM stability (waits full time)
    });
});
```

#### 5.2 Bundle Size

**Test:**
```bash
# Check minified sizes
wc -c lib/readability.min.js    # Should be ~40KB
wc -c lib/dompurify.min.js      # Should be ~10KB
wc -c content_script.js          # Should be <5KB
wc -c service_worker.js          # Should be <3KB
```

**Target:** Extension total size <100KB (excluding icons)

#### 5.3 Memory Usage

**Test:**
- Open extension DevTools
- Run content extraction multiple times
- Verify memory stays <50MB
- Verify no memory leaks (run garbage collection between extractions)

---

### Phase 6: Error Handling & Edge Cases

#### 6.1 MCP Server Errors

| Scenario | Expected Behavior |
|----------|-------------------|
| MCP server offline | Show error: "Cannot connect to MCP server at http://127.0.0.1:3000" |
| Ollama offline | Show error: "Ollama server not responding. Check configuration." |
| Invalid Ollama response | Show error: "Invalid response from AI server" |
| Content too large | Show error: "Content too large for analysis" |
| Timeout after 9 minutes | Show error: "Analysis timed out. Please try again." |

**Test Cases:**
```javascript
describe("Error Handling", () => {
    test("should show user-friendly error when MCP server unreachable", async () => {
        // Mock fetch rejection
        // Verify error message is displayed in popup
    });

    test("should show specific error for Ollama failures", async () => {
        // Mock MCP server to return Ollama error
        // Verify error message explains Ollama issue
    });

    test("should handle truncated content gracefully", async () => {
        // Content extraction succeeds but is empty
        // Verify user gets helpful message
    });
});
```

#### 6.2 Edge Cases

| Edge Case | Expected Behavior |
|-----------|-------------------|
| Page with no text content | Fall back to innerText; may return empty or minimal content |
| Page with iframes | Extract outer page only (iframes not accessible) |
| Page that updates during extraction | MutationObserver waits for stabilization |
| User closes popup during extraction | Cancel ongoing requests |
| User navigates to new page mid-extraction | Cancel extraction for old page |
| Multiple popup instances | Only one can extract at a time |

---

### Phase 7: Security Testing

#### 7.1 Content Sanitization

**Test:** `security.test.js`

```javascript
describe("Content Security", () => {
    test("should sanitize malicious content with DOMPurify", async () => {
        const maliciousContent = '<script>alert("xss")</script><p>Content</p>';
        const extracted = extractCleanContent();
        expect(extracted).not.toContain('<script>');
    });

    test("should not execute embedded scripts", async () => {
        // Load page with <script> tag
        // Verify script doesn't execute
    });

    test("should not expose sensitive data in errors", async () => {
        // Verify error messages don't leak file paths or Ollama URLs
    });
});
```

#### 7.2 Network Security

- ✅ Only connect to http://127.0.0.1:3000 (localhost)
- ✅ Verify HTTPS not required (localhost only)
- ✅ Verify no API keys or credentials in requests
- ✅ Verify content not logged/stored

---

### Phase 8: Documentation & Deliverables

**Create:**
- ✅ Test report template
- ✅ Bug tracking spreadsheet
- ✅ Known issues & workarounds doc
- ✅ Manual test checklist

**Example Manual Test Checklist:**
```
[ ] Extension installs on Chrome
[ ] Extension installs on Edge
[ ] Extension installs on Brave
[ ] Popup UI displays correctly
[ ] Default system prompt is sensible
[ ] "Use default" link works
[ ] Analyze button triggers extraction
[ ] Progress messages display
[ ] Results display in scrollable area
[ ] Copy to clipboard works
[ ] Settings button opens options page
[ ] Lazy-loading triggers on infinite scroll
[ ] DOM stability waits appropriately
[ ] Readability removes nav/footer
[ ] Filtering works with keywords
[ ] Error messages are helpful
[ ] MCP server disconnection handled gracefully
[ ] Large content handled without crash
```

---

## Test Execution Timeline

### Week 1: Unit Tests
- Content script phases
- HTTP endpoint
- Service worker

### Week 2: Integration Tests
- Extension ↔ MCP Server communication
- Error handling paths
- All content types (articles, news, docs, SPA, etc.)

### Week 3: End-to-End Tests
- Full flow on multiple pages
- Keyword filtering
- Cross-browser verification

### Week 4: Performance & Polish
- Performance optimization
- Security review
- Documentation polish

---

## Success Criteria

- ✅ All unit tests pass
- ✅ All integration tests pass
- ✅ Extension works on Chrome, Edge, Brave
- ✅ Content extraction accurate on 10+ different website types
- ✅ Lazy-loading detects new content
- ✅ DOM stability waits appropriately (not forever, not too quick)
- ✅ Readability removes nav/sidebar noise
- ✅ All error cases handled gracefully
- ✅ Total extraction time <10 seconds (not including Ollama)
- ✅ Extension size <100KB
- ✅ Memory usage stable <50MB
- ✅ Security review passes (no XSS, no credential leaks)

---

**Status:** Test plan created
**Next Step:** Implement unit tests, then integration tests
