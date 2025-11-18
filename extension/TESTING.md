# Browser Extension Testing Plan

> **Note:** This document is AI-authored with human oversight.

## Quick Reference

**Full test plan:** See `/tests/BROWSER_EXTENSION_TESTING.md`

This document provides a condensed testing checklist for extension development.

---

## Pre-Testing Setup

### Requirements

- Chrome, Edge, or Brave browser
- Extension loaded (unpacked) in developer mode
- MCP server running: `python chrome_tab_mcp_server.py --ollama-url http://localhost:11434 --model llama2`
- Ollama running with at least one model: `ollama list`

### Loading Extension for Testing

1. Go to `chrome://extensions/`
2. Enable "Developer Mode" (top right)
3. Click "Load unpacked"
4. Select the `extension/` directory
5. Verify extension appears and is enabled

### Accessing Extension DevTools

- Right-click extension icon → "Inspect popup" (for popup debugging)
- Right-click extension icon → "Manage Extensions" → Inspect views (for service worker)
- Open extension popup, then DevTools Console to see logs

---

## Test Categories

### Phase 1: Basic Functionality Tests

#### T1.1: Extension Loads Without Errors

```
[ ] Extension appears in chrome://extensions
[ ] Extension icon appears in toolbar
[ ] No errors in extension logs (Console)
[ ] Popup opens without crash
[ ] Service worker is running (no errors)
```

#### T1.2: Popup UI Works

```
[ ] System prompt textarea is visible
[ ] "From keyword" input is visible
[ ] "To keyword" input is visible
[ ] "Analyze" button is visible
[ ] "Settings" button is visible
[ ] "Use default" link works
[ ] Results area shows when analysis complete
[ ] Copy button appears in results
```

#### T1.3: Basic Extraction

**Test on:** https://example.com (simple, static page)

```
[ ] Click "Analyze"
[ ] See "Triggering lazy-loading..." message
[ ] See "Waiting for page to stabilize..." message
[ ] See "Extracting content..." message
[ ] Extraction completes in <10 seconds
[ ] Results appear in popup
[ ] Results are readable text
```

---

### Phase 2: Extraction Quality Tests

#### T2.1: Lazy-Loading Detection

**Test on:** https://twitter.com or similar infinite scroll page

```
[ ] Page scrolls to bottom (observable)
[ ] New tweets/content appears (observable)
[ ] DOM stability detection waits 2-3 seconds
[ ] Final extraction includes recently loaded content
[ ] Scroll returns to top after extraction
```

#### T2.2: Readability.js Noise Removal

**Test on:** Any news article or blog post

```
[ ] Navigation menu not included in results
[ ] Footer not included
[ ] Sidebar not included
[ ] Ad content not included
[ ] Main article content is included
[ ] Text formatting is preserved (paragraphs, lists)
```

**Comparison Test:**

```bash
# Run in browser console on article page:
console.log(document.body.innerText);    // Raw text
```

Verify Readability output is cleaner than innerText.

#### T2.3: DOM Stability Handling

**Test on:** Page with animations or auto-updating content

```
[ ] Waits for content to stabilize
[ ] Doesn't wait forever (respects 3-minute timeout)
[ ] On static page: exits in <1 second
[ ] On animated page: waits 2-3 seconds for stabilization
[ ] Hard timeout at 3 minutes prevents infinite wait
```

#### T2.4: Single-Page App Support

**Test on:** React/Vue application (e.g., https://react.dev)

```
[ ] Detects initial render is complete
[ ] Waits for dynamic content to populate
[ ] No missing components in extraction
[ ] Final analysis reflects what's visible on screen
```

---

### Phase 3: Filtering Tests

#### T3.1: Keyword Filtering

**Setup:** Navigate to a page with clear section headers

**Test:**

```
[ ] Set "From keyword: [first section]"
[ ] Set "To keyword: [second section]"
[ ] Click "Analyze"
[ ] Results only contain content between keywords
[ ] Results exclude content before first keyword
[ ] Results exclude content after second keyword
```

#### T3.2: Case-Insensitive Matching

```
[ ] From keyword: "INTRODUCTION" matches "introduction"
[ ] To keyword: "conclusion" matches "CONCLUSION"
[ ] Filtering is case-insensitive
```

#### T3.3: Partial Keyword Matching

```
[ ] Keyword "Skills" matches "My Skills"
[ ] Keyword "Contact" matches "Contact Information"
[ ] Partial matches work correctly
```

---

### Phase 4: MCP Server Communication

#### T4.1: Endpoint Connectivity

**Manual test:**

```bash
# Verify endpoint exists and responds
curl -X POST http://127.0.0.1:3000/tools/process_chrome_tab \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Test content",
    "system_prompt": "Analyze this"
  }'
```

Expected: JSON response with `analysis` field

#### T4.2: Large Content Handling

**Test:** Extract from long article or multiple pages

```
[ ] Send >100KB content to MCP server
[ ] No connection errors
[ ] Server processes successfully
[ ] Results returned correctly
```

#### T4.3: Error Scenarios

**Test 1: MCP Server Offline**

```
[ ] Stop MCP server
[ ] Click "Analyze"
[ ] See error: "Cannot connect to MCP server at http://127.0.0.1:3000"
[ ] Error message is user-friendly
[ ] Extension doesn't crash
```

**Test 2: Ollama Offline**

```
[ ] Stop Ollama
[ ] Start MCP server (server starts fine)
[ ] Click "Analyze"
[ ] Wait for Ollama timeout
[ ] See helpful error message about Ollama
```

**Test 3: Timeout**

```
[ ] Set very long timeout (9+ minutes)
[ ] Verify timeout error after 9 minutes
[ ] Message indicates what timed out
```

---

### Phase 5: Cross-Browser Testing

#### T5.1: Chrome

```
[ ] Install extension
[ ] Extract content successfully
[ ] All tests pass
```

#### T5.2: Edge

```
[ ] Install extension (should work same as Chrome)
[ ] Extract content successfully
```

#### T5.3: Brave

```
[ ] Install extension
[ ] Extract content successfully
```

#### T5.4: Platform Testing

On each browser, test on:
- ✅ macOS
- ✅ Windows
- ✅ Linux

---

### Phase 6: Performance Testing

#### T6.1: Extraction Timing

**Measure:** Time each phase

```javascript
// In popup.js, add timing:
const phaseStart = performance.now();
// ... run extraction
const phaseEnd = performance.now();
console.log(`Phase took ${phaseEnd - phaseStart}ms`);
```

**Targets:**
```
Phase 1 (lazy-loading): < 5 seconds
Phase 2 (DOM stability): < 3 minutes (typically 0.5-2 sec)
Phase 3 (readability): < 1 second
Total: < 10 seconds (not counting Ollama)
```

#### T6.2: Memory Usage

```
[ ] Open DevTools
[ ] Record memory before extraction
[ ] Run extraction
[ ] Record memory after extraction
[ ] Memory increase < 50MB
[ ] No memory leaks (run GC between extractions)
```

#### T6.3: Bundle Size

```bash
# Check file sizes
wc -c extension/lib/readability.min.js   # Should be ~40KB
wc -c extension/lib/dompurify.min.js     # Should be ~10KB
wc -c extension/content_script.js         # Should be <5KB
wc -c extension/service_worker.js         # Should be <3KB
```

---

### Phase 7: Edge Cases

#### T7.1: Empty Pages

**Test on:** `about:blank` or empty page

```
[ ] No crash
[ ] Extraction returns empty or minimal content
[ ] User gets helpful message
```

#### T7.2: PDF Files

**Test on:** PDF document

```
[ ] No crash
[ ] Extraction fails gracefully
[ ] Error message explains PDF not supported
```

#### T7.3: Page Navigation During Extraction

```
[ ] Start extraction
[ ] Quickly navigate to new page
[ ] Old extraction cancelled
[ ] No stale results displayed
[ ] No errors in console
```

#### T7.4: Rapid Successive Extractions

```
[ ] Click "Analyze" multiple times quickly
[ ] Only latest extraction completes
[ ] No race conditions
[ ] Results are correct
```

#### T7.5: Pop-up Close During Extraction

```
[ ] Start extraction
[ ] Close popup mid-process
[ ] No crashes
[ ] No orphaned requests to MCP server
```

---

### Phase 8: Security Testing

#### T8.1: XSS Prevention

**Test on:** Page with embedded scripts

```html
<script>alert('XSS')</script>
<p>Normal content</p>
```

```
[ ] No alert() appears
[ ] Script doesn't execute
[ ] Only "Normal content" in results
[ ] DOMPurify sanitization working
```

#### T8.2: Content Isolation

```
[ ] Extracted content is text only (no HTML)
[ ] No inline styles
[ ] No embedded objects
```

#### T8.3: Credential Leakage

```
[ ] No passwords in error messages
[ ] No API keys in logs
[ ] No server URLs in user-facing messages
```

---

## Manual Test Checklist

### Quick Smoke Test (5 minutes)

Before deployment, run this quick test:

```
[ ] Extension loads without errors
[ ] Popup opens
[ ] Click "Analyze" on example.com
[ ] Results appear
[ ] No console errors
[ ] MCP server receives request
[ ] Ollama processes successfully
```

### Full Test Suite (30 minutes)

For release testing:

```
[ ] T1.1: Extension loads
[ ] T1.2: Popup UI works
[ ] T1.3: Basic extraction
[ ] T2.1: Lazy-loading (Twitter)
[ ] T2.2: Readability (news article)
[ ] T2.4: SPA extraction
[ ] T3.1: Keyword filtering
[ ] T4.1: Endpoint connectivity
[ ] T4.3: Error scenarios
[ ] T5.1: Chrome test
[ ] T6.1: Extraction timing
[ ] T7.1: Empty page handling
[ ] T8.1: XSS prevention
```

### Test Websites by Category

Use these to verify extraction quality across types:

**News/Articles:**
- https://news.ycombinator.com
- https://medium.com/@[user]/[article]
- https://www.nytimes.com/

**Documentation:**
- https://developer.mozilla.org/en-US/
- https://docs.python.org/

**Social Media:**
- https://twitter.com
- https://reddit.com/r/[subreddit]

**Product Pages:**
- https://www.amazon.com/s?k=[product]
- https://www.github.com

**SPAs:**
- https://react.dev
- https://vuejs.org

**Technical:**
- https://github.com/[project]/[repo]
- https://stackoverflow.com/questions/

---

## Debugging Tips

### Enable Verbose Logging

In `content_script.js`, all logs prefixed with `[Chrome Tab Reader]` will show in DevTools console.

### View Network Requests

1. Open DevTools
2. Network tab
3. Run extraction
4. Look for POST request to `http://127.0.0.1:3000/tools/process_chrome_tab`
5. Check request/response headers and body

### Inspect Service Worker

1. Go to `chrome://extensions`
2. Find Chrome Tab Reader extension
3. Click "Service worker" under Inspect views
4. View console logs

### Check Extension Storage

```javascript
// In service worker console:
chrome.storage.local.get(null, (items) => console.log(items));
```

### Monitor Memory

DevTools → Memory tab:
1. Take heap snapshot
2. Run extraction
3. Force garbage collection (trash icon)
4. Take another snapshot
5. Compare growth

---

## Success Criteria

All of the following must pass before release:

- ✅ All T1-T5 tests pass on Chrome, Edge, Brave
- ✅ Extraction works on 10+ different website types
- ✅ Lazy-loading detection works on infinite scroll
- ✅ Readability removes nav/footer/sidebar
- ✅ All error cases handled gracefully
- ✅ Extraction time < 10 seconds
- ✅ Bundle size < 100KB
- ✅ Memory usage stable < 50MB
- ✅ No XSS vulnerabilities
- ✅ No credential leakage

---

## Known Issues & Workarounds

### Issue: "Cannot connect to MCP server"

**Cause:** MCP server not running

**Fix:** Start MCP server:
```bash
python chrome_tab_mcp_server.py --ollama-url http://localhost:11434 --model llama2
```

### Issue: Extraction takes 3+ minutes

**Cause:** DOM stability timeout reached

**Expected:** This is normal. Extraction waits up to 3 minutes for dynamic content. If page keeps changing, it uses hard timeout.

**Workaround:** Navigate to more stable pages, or reduce timeout in code if needed.

### Issue: Readability.js not defined

**Cause:** Library not loading properly

**Check:**
1. Verify `lib/readability.min.js` exists
2. Check manifest.json includes it in content_scripts
3. Clear cache: go to `chrome://extensions`, click reload

---

## Test Report Template

When running tests, save results:

```markdown
# Test Run Report

**Date:** 2025-11-13
**Browser:** Chrome 131
**Platform:** macOS Sonoma
**Tester:** [Name]

## Summary
- Tests Passed: X/Y
- Tests Failed: 0
- Blockers: None

## Results

### T1: Basic Functionality
- [ ] T1.1 PASS/FAIL
- [ ] T1.2 PASS/FAIL
- [ ] T1.3 PASS/FAIL

[... more test results ...]

## Issues Found
[List any bugs or issues discovered]

## Notes
[Any relevant observations]
```

---

**Status:** Comprehensive Testing Plan
**Version:** 1.0
**Last Updated:** November 13, 2025
**Next Step:** Implement tests and track results
