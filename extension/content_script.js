/**
 * Chrome Tab Reader - Content Script
 *
 * Runs in page context with DOM access
 * Performs three-phase content extraction:
 *  1. Trigger lazy-loading by simulating scroll
 *  2. Wait for DOM stability (MutationObserver)
 *  3. Extract clean content with Readability.js
 */

console.log("[Chrome Tab Reader] Content script loaded");

/**
 * Phase 1: Trigger Lazy-Loading
 * Simulates user scrolling to trigger infinite scroll and lazy-loading patterns
 */
async function triggerLazyLoading(maxScrolls = 5, scrollDelay = 500) {
    console.log("[Chrome Tab Reader] Phase 1: Triggering lazy-loading...");
    let lastHeight = document.body.scrollHeight;
    let scrollCount = 0;

    for (let i = 0; i < maxScrolls; i++) {
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise(resolve => setTimeout(resolve, scrollDelay));

        let newHeight = document.body.scrollHeight;
        if (newHeight === lastHeight) {
            console.log(`[Chrome Tab Reader] Phase 1: No new content after scroll ${i + 1}, stopping`);
            break;
        }
        lastHeight = newHeight;
        scrollCount++;
    }

    // Return to top
    window.scrollTo(0, 0);
    console.log(`[Chrome Tab Reader] Phase 1: Completed ${scrollCount} scrolls`);
}

/**
 * Phase 2: Wait for DOM Stability
 * Uses MutationObserver to detect when dynamic content stops loading
 */
async function waitForDOMStability(timeoutMs = 180000, stabilityDelayMs = 2000) {
    console.log("[Chrome Tab Reader] Phase 2: Waiting for DOM stability...");

    return new Promise((resolve) => {
        let stableTimer;
        const observer = new MutationObserver((mutations) => {
            // Reset the stability timer on any mutation
            clearTimeout(stableTimer);

            // Wait this many milliseconds without changes before considering stable
            stableTimer = setTimeout(() => {
                console.log("[Chrome Tab Reader] Phase 2: DOM stable, resolving");
                observer.disconnect();
                resolve();
            }, stabilityDelayMs);
        });

        // Only track structural changes, not style/class changes
        observer.observe(document.documentElement, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['src', 'href', 'data-src']
        });

        // Hard timeout after specified milliseconds
        setTimeout(() => {
            console.log("[Chrome Tab Reader] Phase 2: Hard timeout reached, stopping observation");
            observer.disconnect();
            resolve();
        }, timeoutMs);
    });
}

/**
 * Phase 3: Extract Clean Content
 * Uses Readability.js to extract main article content
 * Falls back to document.body.innerText if Readability fails
 */
function extractCleanContent() {
    console.log("[Chrome Tab Reader] Phase 3: Extracting content with Readability...");

    try {
        // Check if Readability is available
        if (typeof Readability === 'undefined') {
            console.warn("[Chrome Tab Reader] Readability not available, using fallback");
            return document.body.innerText;
        }

        // Clone the document to avoid modifying the original
        const clonedDoc = document.cloneNode(true);
        const reader = new Readability(clonedDoc);
        const article = reader.parse();

        if (article && article.textContent) {
            // Sanitize with DOMPurify if available
            if (typeof DOMPurify !== 'undefined') {
                return DOMPurify.sanitize(article.textContent);
            }
            return article.textContent;
        }
    } catch (error) {
        console.warn("[Chrome Tab Reader] Readability extraction failed:", error);
    }

    // Fallback to innerText
    console.log("[Chrome Tab Reader] Falling back to document.body.innerText");
    return document.body.innerText;
}

/**
 * Full three-phase extraction pipeline
 */
async function extractPageContent(strategy = "three-phase") {
    const startTime = performance.now();
    console.log(`[Chrome Tab Reader] Starting extraction with strategy: ${strategy}`);

    try {
        if (strategy === "three-phase") {
            // Phase 1: Trigger lazy-loading (up to 5 seconds)
            await triggerLazyLoading(5, 500);

            // Phase 2: Wait for DOM stability (up to 3 minutes)
            await waitForDOMStability(180000, 2000);

            // Phase 3: Extract with Readability
            var content = extractCleanContent();
        } else if (strategy === "simple") {
            // Simple strategy: just get innerText
            content = document.body.innerText;
        } else {
            console.warn(`[Chrome Tab Reader] Unknown strategy: ${strategy}, using three-phase`);
            await triggerLazyLoading(5, 500);
            await waitForDOMStability(180000, 2000);
            content = extractCleanContent();
        }

        const endTime = performance.now();
        const extractionTimeMs = Math.round(endTime - startTime);

        return {
            status: "success",
            content: content,
            title: document.title,
            url: window.location.href,
            extraction_time_ms: extractionTimeMs
        };
    } catch (error) {
        console.error("[Chrome Tab Reader] Extraction error:", error);
        return {
            status: "error",
            error: error.message,
            title: document.title,
            url: window.location.href
        };
    }
}

/**
 * Extract content between two keywords (inclusive)
 * Case-insensitive partial matching
 */
function extractContentBetweenKeywords(content, startKeyword, endKeyword) {
    console.log(`[Chrome Tab Reader] Filtering content between "${startKeyword}" and "${endKeyword}"`);

    if (!startKeyword && !endKeyword) {
        return content;
    }

    const lowerContent = content.toLowerCase();
    let startIdx = 0;
    let endIdx = content.length;

    if (startKeyword) {
        const lowerStart = startKeyword.toLowerCase();
        startIdx = lowerContent.indexOf(lowerStart);
        if (startIdx === -1) {
            console.warn(`[Chrome Tab Reader] Start keyword "${startKeyword}" not found`);
            startIdx = 0;
        }
    }

    if (endKeyword) {
        const lowerEnd = endKeyword.toLowerCase();
        endIdx = lowerContent.indexOf(lowerEnd, startIdx);
        if (endIdx === -1) {
            console.warn(`[Chrome Tab Reader] End keyword "${endKeyword}" not found`);
            endIdx = content.length;
        } else {
            // Include the end keyword in the result
            endIdx += endKeyword.length;
        }
    }

    const filtered = content.substring(startIdx, endIdx);
    console.log(`[Chrome Tab Reader] Filtered content length: ${filtered.length} characters`);
    return filtered;
}

/**
 * Handle messages from service worker
 */
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log("[Chrome Tab Reader] Content script received message:", request.action);

    if (request.action === "extractContent") {
        // Run extraction and send response
        extractPageContent(request.strategy || "three-phase").then((result) => {
            // Apply keyword filtering if provided
            if (request.startKeyword || request.endKeyword) {
                result.content = extractContentBetweenKeywords(
                    result.content,
                    request.startKeyword,
                    request.endKeyword
                );
            }
            sendResponse(result);
        }).catch((error) => {
            sendResponse({
                status: "error",
                error: error.message
            });
        });

        // Return true to indicate we'll respond asynchronously
        return true;
    }

    if (request.action === "getPageInfo") {
        sendResponse({
            title: document.title,
            url: window.location.href
        });
        return false;
    }
});

console.log("[Chrome Tab Reader] Content script ready");
