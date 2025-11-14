/**
 * Chrome Tab Reader - Service Worker
 *
 * Background service worker that:
 * - Handles tab navigation and extraction requests
 * - Manages communication between popup and content script
 * - Delegates to content script for actual extraction
 */

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
 * Extract content from a specific tab
 */
async function extractFromTab(tabId, strategy = "three-phase") {
    console.log(`[Chrome Tab Reader] Extracting from tab ${tabId} with strategy: ${strategy}`);

    try {
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
 * Handle messages from popup
 */
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
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
