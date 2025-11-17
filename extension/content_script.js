/**
 * Chrome Tab Reader - Content Script
 *
 * Runs in page context with DOM access
 * Performs three-phase content extraction:
 *  1. Trigger lazy-loading by simulating scroll
 *  2. Wait for DOM stability (MutationObserver)
 *  3. Extract clean content with Readability.js
 */

// Intercept console.log to send to popup
(function() {
    const originalLog = console.log;
    const originalWarn = console.warn;
    const originalError = console.error;

    function sendLogToPopup(level, args) {
        const message = Array.from(args).map(arg => {
            if (typeof arg === 'object') {
                try {
                    return JSON.stringify(arg);
                } catch (e) {
                    return String(arg);
                }
            }
            return String(arg);
        }).join(' ');

        // Send to service worker which will relay to popup
        chrome.runtime.sendMessage({
            type: 'console_log',
            level: level,
            message: message,
            source: 'content'
        }).catch(() => {
            // Popup might not be open, ignore errors
        });
    }

    console.log = function(...args) {
        originalLog.apply(console, args);
        if (args[0] && args[0].includes('[Chrome Tab Reader]')) {
            sendLogToPopup('info', args);
        }
    };

    console.warn = function(...args) {
        originalWarn.apply(console, args);
        if (args[0] && args[0].includes('[Chrome Tab Reader]')) {
            sendLogToPopup('warn', args);
        }
    };

    console.error = function(...args) {
        originalError.apply(console, args);
        if (args[0] && args[0].includes('[Chrome Tab Reader]')) {
            sendLogToPopup('error', args);
        }
    };
})();

console.log("[Chrome Tab Reader] Content script loaded");

/**
 * Try incremental scrolling to simulate real user behavior
 */
async function tryIncrementalScroll(targetPosition, delay) {
    const steps = 5;
    const currentPosition = window.pageYOffset || document.documentElement.scrollTop;

    for (let step = 1; step <= steps; step++) {
        const position = currentPosition + ((targetPosition - currentPosition) * step / steps);
        window.scrollTo(0, position);
        window.dispatchEvent(new Event('scroll', { bubbles: true }));
        await new Promise(resolve => setTimeout(resolve, delay / steps));
    }
}

/**
 * Find the primary scrollable container on the page
 */
function findScrollableContainer() {
    // Try to find the main scrollable element
    // Check common patterns: workspace containers, main content areas, feed containers
    const candidates = [
        document.querySelector('main#workspace'),
        document.querySelector('main'),
        document.querySelector('[role="main"]'),
        document.querySelector('.scaffold-layout__main'),
        document.querySelector('[class*="feed"]'),
        document.querySelector('#main'),
        document.documentElement,
        document.body,
    ].filter(el => el);

    // Find the one with the most scrollable height
    let best = document.documentElement;
    let maxScrollableHeight = 0;

    for (const el of candidates) {
        const scrollableHeight = el.scrollHeight - el.clientHeight;
        if (scrollableHeight > maxScrollableHeight) {
            maxScrollableHeight = scrollableHeight;
            best = el;
        }
    }

    return best;
}

/**
 * Get total content metrics for detecting new content
 */
function getContentMetrics(container) {
    return {
        scrollHeight: container.scrollHeight,
        elementCount: container.querySelectorAll('*').length,
        bodyHeight: document.body.scrollHeight
    };
}

/**
 * Check if content metrics indicate new content loaded
 */
function hasNewContent(oldMetrics, newMetrics) {
    return newMetrics.scrollHeight > oldMetrics.scrollHeight ||
           newMetrics.elementCount > oldMetrics.elementCount ||
           newMetrics.bodyHeight > oldMetrics.bodyHeight;
}

/**
 * Try scrolling a specific container element
 */
async function tryContainerScroll(container, targetScroll) {
    try {
        const oldScrollTop = container.scrollTop;

        // Try multiple scroll techniques on the container
        container.scrollTop = targetScroll;
        if (container.scrollTo) {
            container.scrollTo(0, targetScroll);
            container.scrollTo({ top: targetScroll, behavior: 'smooth' });
        }

        // Dispatch scroll event
        container.dispatchEvent(new Event('scroll', { bubbles: true, cancelable: true }));

        return container.scrollTop !== oldScrollTop;
    } catch (e) {
        console.warn("[Chrome Tab Reader] Error scrolling container:", e);
        return false;
    }
}

/**
 * Phase 1: Trigger Lazy-Loading
 * Simulates user scrolling to trigger infinite scroll and lazy-loading patterns
 * Tries methods sequentially and stops when new content is detected
 * Handles both window scrolling and custom container scrolling
 */
async function triggerLazyLoading(maxScrolls = 5, scrollDelay = 500) {
    console.log("[Chrome Tab Reader] Phase 1: Triggering lazy-loading...");

    // Find the primary scrollable container
    const scrollContainer = findScrollableContainer();
    const isWindowScroll = (scrollContainer === document.documentElement || scrollContainer === document.body);

    console.log(`[Chrome Tab Reader] Using scroll container: ${scrollContainer.tagName}${scrollContainer.id ? '#' + scrollContainer.id : ''}${scrollContainer.className ? '.' + scrollContainer.className.split(' ')[0] : ''}`);
    console.log(`[Chrome Tab Reader] Scroll mode: ${isWindowScroll ? 'window' : 'container'}`);

    let scrollCount = 0;

    for (let i = 0; i < maxScrolls; i++) {
        // Get metrics before scrolling
        const startMetrics = getContentMetrics(scrollContainer);
        const targetPosition = scrollContainer.scrollHeight;
        let methodUsed = null;

        // Method 5: Incremental scrolling (most human-like)
        if (!methodUsed) {
            console.log("[Chrome Tab Reader] Trying incremental scroll...");
            if (isWindowScroll) {
                await tryIncrementalScroll(targetPosition, scrollDelay);
            } else {
                // Incremental scroll for container
                const steps = 5;
                const currentPos = scrollContainer.scrollTop;
                for (let step = 1; step <= steps; step++) {
                    const pos = currentPos + ((targetPosition - currentPos) * step / steps);
                    scrollContainer.scrollTop = pos;
                    scrollContainer.dispatchEvent(new Event('scroll', { bubbles: true }));
                    await new Promise(resolve => setTimeout(resolve, scrollDelay / steps));
                }
            }
            await new Promise(resolve => setTimeout(resolve, 200));

            const newMetrics = getContentMetrics(scrollContainer);
            if (hasNewContent(startMetrics, newMetrics)) {
                methodUsed = "incremental scroll";
            }
        }

        // Method 4: Dispatch scroll events
        if (!methodUsed) {
            console.log("[Chrome Tab Reader] Trying scroll event dispatch...");
            if (isWindowScroll) {
                window.scrollTo(0, targetPosition);
                window.dispatchEvent(new Event('scroll', { bubbles: true }));
                document.dispatchEvent(new Event('scroll', { bubbles: true }));
            } else {
                scrollContainer.scrollTop = targetPosition;
                scrollContainer.dispatchEvent(new Event('scroll', { bubbles: true }));
            }
            await new Promise(resolve => setTimeout(resolve, 200));

            const newMetrics = getContentMetrics(scrollContainer);
            if (hasNewContent(startMetrics, newMetrics)) {
                methodUsed = "scroll events";
            }
        }

        // Method 3: Custom container scroll with multiple techniques
        if (!methodUsed) {
            console.log("[Chrome Tab Reader] Trying container scroll techniques...");
            await tryContainerScroll(scrollContainer, targetPosition);
            await new Promise(resolve => setTimeout(resolve, 200));

            const newMetrics = getContentMetrics(scrollContainer);
            if (hasNewContent(startMetrics, newMetrics)) {
                methodUsed = "container scroll";
            }
        }

        // Method 2: Direct property assignment
        if (!methodUsed) {
            console.log("[Chrome Tab Reader] Trying direct property assignment...");
            scrollContainer.scrollTop = targetPosition;
            if (isWindowScroll) {
                document.documentElement.scrollTop = targetPosition;
                document.body.scrollTop = targetPosition;
            }
            await new Promise(resolve => setTimeout(resolve, 200));

            const newMetrics = getContentMetrics(scrollContainer);
            if (hasNewContent(startMetrics, newMetrics)) {
                methodUsed = "direct assignment";
            }
        }

        // Method 1: scrollTo with smooth behavior
        if (!methodUsed) {
            console.log("[Chrome Tab Reader] Trying smooth scrollTo...");
            if (isWindowScroll) {
                window.scrollTo({ top: targetPosition, behavior: 'smooth' });
            } else if (scrollContainer.scrollTo) {
                scrollContainer.scrollTo({ top: targetPosition, behavior: 'smooth' });
            }
            await new Promise(resolve => setTimeout(resolve, scrollDelay));

            const newMetrics = getContentMetrics(scrollContainer);
            if (hasNewContent(startMetrics, newMetrics)) {
                methodUsed = "smooth scrollTo";
            }
        }

        // Check if we loaded new content
        const finalMetrics = getContentMetrics(scrollContainer);
        if (hasNewContent(startMetrics, finalMetrics)) {
            scrollCount++;
            console.log(`[Chrome Tab Reader] Phase 1: New content detected using ${methodUsed}`);
            console.log(`  Metrics: scrollHeight ${startMetrics.scrollHeight} → ${finalMetrics.scrollHeight}, elements ${startMetrics.elementCount} → ${finalMetrics.elementCount}`);
            // Continue to next scroll iteration
        } else {
            console.log(`[Chrome Tab Reader] Phase 1: No new content after scroll ${i + 1}, stopping`);
            break;
        }
    }

    // Return to top
    if (isWindowScroll) {
        window.scrollTo({ top: 0, behavior: 'instant' });
    } else {
        scrollContainer.scrollTop = 0;
    }
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

            // Phase 2: Wait for DOM stability (up to 30 seconds)
            await waitForDOMStability(30000, 2000);

            // Phase 3: Extract with Readability
            var content = extractCleanContent();
        } else if (strategy === "simple") {
            // Simple strategy: just get innerText
            content = document.body.innerText;
        } else {
            console.warn(`[Chrome Tab Reader] Unknown strategy: ${strategy}, using three-phase`);
            await triggerLazyLoading(5, 500);
            await waitForDOMStability(30000, 2000);
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

/**
 * Expose extraction API to window for testing
 * This allows Puppeteer tests to call the extension directly
 */
window.__chromeTabReader__ = {
    extractContent: async (options = {}) => {
        try {
            const result = await extractPageContent(options.strategy || "three-phase");

            // Apply keyword filtering if provided
            if (options.startKeyword || options.endKeyword) {
                result.content = extractContentBetweenKeywords(
                    result.content,
                    options.startKeyword,
                    options.endKeyword
                );
            }

            return result;
        } catch (error) {
            return {
                status: "error",
                error: error.message
            };
        }
    },
    getPageInfo: () => ({
        title: document.title,
        url: window.location.href
    }),
    checkLibraries: () => ({
        readability: typeof Readability !== 'undefined',
        dompurify: typeof DOMPurify !== 'undefined'
    })
};

console.log("[Chrome Tab Reader] Test API exposed on window.__chromeTabReader__");

console.log("[Chrome Tab Reader] Content script ready");
