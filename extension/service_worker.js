/**
 * Chrome Tab Reader - Service Worker
 *
 * Background service worker that:
 * - Handles tab navigation and extraction requests
 * - Manages communication between popup and content script
 * - Delegates to content script for actual extraction
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

        // Send to all extension contexts (popup)
        chrome.runtime.sendMessage({
            type: 'console_log',
            level: level,
            message: message,
            source: 'service-worker'
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

console.log("[Chrome Tab Reader] Service Worker loaded");

/**
 * Generate a cryptographically random access token
 */
function generateAccessToken() {
    const array = new Uint8Array(32); // 256 bits
    crypto.getRandomValues(array);
    // Convert to base64-url safe string
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
}

/**
 * Get or create access token
 */
async function getAccessToken() {
    const result = await chrome.storage.local.get(['accessToken']);
    if (result.accessToken) {
        return result.accessToken;
    }

    // Generate new token
    const token = generateAccessToken();
    await chrome.storage.local.set({ accessToken: token });
    console.log("[Chrome Tab Reader] Generated new access token");
    return token;
}

/**
 * Regenerate access token
 */
async function regenerateAccessToken() {
    const token = generateAccessToken();
    await chrome.storage.local.set({ accessToken: token });
    console.log("[Chrome Tab Reader] Regenerated access token");
    return token;
}

// Initialize token on install
chrome.runtime.onInstalled.addListener(async () => {
    await getAccessToken();
    console.log("[Chrome Tab Reader] Extension installed/updated");
});

/**
 * Check if a URL can have content scripts injected
 */
function canInjectContentScript(url) {
    if (!url) return false;

    const restrictedProtocols = ['chrome:', 'chrome-extension:', 'about:', 'edge:', 'browser:'];
    const restrictedPages = ['chrome://newtab/', 'chrome://extensions/', 'about:blank'];

    // Check if URL starts with restricted protocol
    for (const protocol of restrictedProtocols) {
        if (url.startsWith(protocol)) {
            return false;
        }
    }

    // Check if URL is a restricted page
    for (const page of restrictedPages) {
        if (url.startsWith(page)) {
            return false;
        }
    }

    return true;
}

/**
 * Ensure content script is injected in the tab
 */
async function ensureContentScriptInjected(tabId) {
    try {
        // Try to ping the content script
        const response = await chrome.tabs.sendMessage(tabId, { action: "getPageInfo" });
        console.log("[Chrome Tab Reader] Content script already loaded");
        return true;
    } catch (error) {
        // Content script not loaded, try to inject it
        console.log("[Chrome Tab Reader] Content script not detected, attempting injection");

        try {
            // Inject the libraries first
            await chrome.scripting.executeScript({
                target: { tabId: tabId },
                files: ['lib/readability.min.js', 'lib/dompurify.min.js', 'content_script.js']
            });

            console.log("[Chrome Tab Reader] Content script injected successfully");

            // Wait a moment for the script to initialize
            await new Promise(resolve => setTimeout(resolve, 100));

            return true;
        } catch (injectError) {
            console.error("[Chrome Tab Reader] Failed to inject content script:", injectError);
            return false;
        }
    }
}

/**
 * Extract content from a specific tab
 */
async function extractFromTab(tabId, strategy = "three-phase") {
    console.log(`[Chrome Tab Reader] Extracting from tab ${tabId} with strategy: ${strategy}`);

    try {
        // Get tab info to check URL
        const tab = await chrome.tabs.get(tabId);

        // Check if we can inject content scripts on this page
        if (!canInjectContentScript(tab.url)) {
            console.warn(`[Chrome Tab Reader] Cannot extract from restricted page: ${tab.url}`);
            return {
                status: "error",
                error: `Cannot extract content from this type of page (${new URL(tab.url).protocol}). Please navigate to a regular webpage.`
            };
        }

        // Ensure content script is injected
        const injected = await ensureContentScriptInjected(tabId);
        if (!injected) {
            return {
                status: "error",
                error: "Failed to inject content script. Please try refreshing the page."
            };
        }

        // Send extraction request to content script
        const response = await chrome.tabs.sendMessage(tabId, {
            action: "extractContent",
            strategy: strategy
        });
        console.log("[Chrome Tab Reader] Extraction response:", response);
        return response;
    } catch (error) {
        console.error("[Chrome Tab Reader] Error sending message to tab:", error);
        return {
            status: "error",
            error: `Failed to extract content: ${error.message}`
        };
    }
}

/**
 * Extract content from current tab
 */
async function extractCurrentTab(strategy = "three-phase") {
    console.log("[Chrome Tab Reader] Extracting from current tab");

    try {
        // Get the active tab in the current window
        const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tabs.length === 0) {
            return {
                status: "error",
                error: "No active tab found"
            };
        }

        const tab = tabs[0];
        console.log(`[Chrome Tab Reader] Found active tab: ${tab.id} - ${tab.title}`);

        return await extractFromTab(tab.id, strategy);
    } catch (error) {
        console.error("[Chrome Tab Reader] Error getting active tab:", error);
        return {
            status: "error",
            error: `Failed to get active tab: ${error.message}`
        };
    }
}

/**
 * Navigate to URL and extract content
 */
async function navigateAndExtract(url, strategy = "three-phase", waitForMs = 0) {
    console.log(`[Chrome Tab Reader] Navigating to ${url} and extracting`);

    try {
        // Get the current active tab
        const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tabs.length === 0) {
            return {
                status: "error",
                error: "No active tab found"
            };
        }

        const tab = tabs[0];
        const startTime = performance.now();

        // Navigate to the URL
        await chrome.tabs.update(tab.id, { url: url });

        // Wait for page to load
        await new Promise((resolve) => {
            let checkCount = 0;
            const maxChecks = waitForMs / 100; // Check every 100ms

            const checkCompletion = async () => {
                try {
                    const updatedTab = await chrome.tabs.get(tab.id);
                    if (updatedTab.status === "complete" && checkCount > 5) {
                        // Give page a bit more time to settle
                        setTimeout(() => resolve(), 500);
                    } else {
                        checkCount++;
                        if (checkCount < maxChecks) {
                            setTimeout(checkCompletion, 100);
                        } else {
                            resolve(); // Timeout, proceed anyway
                        }
                    }
                } catch (error) {
                    console.warn("[Chrome Tab Reader] Error checking tab status:", error);
                    resolve();
                }
            };

            checkCompletion();
        });

        // Wait additional time if specified
        if (waitForMs > 0) {
            await new Promise(resolve => setTimeout(resolve, waitForMs));
        }

        const navigationTimeMs = performance.now() - startTime;

        // Extract content from the new page
        const extractionResult = await extractFromTab(tab.id, strategy);

        // Add navigation timing to result
        if (extractionResult.status === "success") {
            extractionResult.navigation_time_ms = Math.round(navigationTimeMs);
        }

        return extractionResult;
    } catch (error) {
        console.error("[Chrome Tab Reader] Error during navigation and extraction:", error);
        return {
            status: "error",
            error: `Failed to navigate and extract: ${error.message}`
        };
    }
}

/**
 * Get info about the current tab
 */
async function getCurrentTabInfo() {
    console.log("[Chrome Tab Reader] Getting current tab info");

    try {
        const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tabs.length === 0) {
            return {
                status: "error",
                error: "No active tab found"
            };
        }

        const tab = tabs[0];
        return {
            tab_id: tab.id,
            url: tab.url,
            title: tab.title,
            is_loading: tab.status === "loading"
        };
    } catch (error) {
        console.error("[Chrome Tab Reader] Error getting tab info:", error);
        return {
            status: "error",
            error: `Failed to get tab info: ${error.message}`
        };
    }
}

/**
 * Health check
 */
function getHealthStatus() {
    return {
        status: "ok",
        extension_version: "1.0.0"
    };
}

/**
 * Handle messages from popup and content scripts
 */
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    // Handle console log messages from content scripts - relay to popup
    if (request.type === 'console_log') {
        // Don't log this message to avoid infinite loop
        // Just relay it to the popup
        chrome.runtime.sendMessage(request).catch(() => {
            // Popup might not be open, ignore
        });
        return false;
    }

    console.log("[Chrome Tab Reader] Service worker received message:", request.action);

    if (request.action === "extract_current_tab") {
        extractCurrentTab(request.strategy || "three-phase").then(sendResponse).catch((error) => {
            sendResponse({
                status: "error",
                error: error.message
            });
        });
        return true; // Respond asynchronously
    }

    if (request.action === "navigate_and_extract") {
        navigateAndExtract(request.url, request.strategy || "three-phase", request.wait_for_ms || 0)
            .then(sendResponse)
            .catch((error) => {
                sendResponse({
                    status: "error",
                    error: error.message
                });
            });
        return true;
    }

    if (request.action === "get_current_tab") {
        getCurrentTabInfo().then(sendResponse).catch((error) => {
            sendResponse({
                status: "error",
                error: error.message
            });
        });
        return true;
    }

    if (request.action === "health_check") {
        sendResponse(getHealthStatus());
        return false;
    }

    if (request.action === "get_access_token") {
        getAccessToken().then(sendResponse).catch((error) => {
            sendResponse({ error: error.message });
        });
        return true;
    }

    if (request.action === "regenerate_access_token") {
        regenerateAccessToken().then(sendResponse).catch((error) => {
            sendResponse({ error: error.message });
        });
        return true;
    }
});

/**
 * Handle extension icon click - open popup
 */
chrome.action.onClicked.addListener((tab) => {
    console.log("[Chrome Tab Reader] Action icon clicked");
    // Popup will open automatically, this is just for logging
});

console.log("[Chrome Tab Reader] Service Worker ready");
