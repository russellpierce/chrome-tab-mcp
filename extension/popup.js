/**
 * Chrome Tab Reader - Popup Script
 *
 * Manages the extension popup UI for content extraction
 */

document.addEventListener('DOMContentLoaded', initializePopup);

function initializePopup() {
    console.log('[Chrome Tab Reader] Initializing popup');

    // Get references to UI elements
    const tabTitleEl = document.getElementById('tabTitle');
    const extractBtn = document.getElementById('extractBtn');
    const clearBtn = document.getElementById('clearBtn');
    const statusEl = document.getElementById('status');
    const contentAreaEl = document.getElementById('contentArea');

    // Update tab title on load
    updateTabTitle();

    // Set up event listeners
    extractBtn.addEventListener('click', () => extractCurrentTab(statusEl, contentAreaEl, extractBtn));
    clearBtn.addEventListener('click', () => clearContent(contentAreaEl));

    /**
     * Update the displayed tab title
     */
    function updateTabTitle() {
        chrome.runtime.sendMessage({ action: 'get_current_tab' }, (response) => {
            if (response && response.url) {
                try {
                    const url = new URL(response.url);
                    const domain = url.hostname;
                    const title = response.title || url.pathname || 'Unknown Page';
                    tabTitleEl.textContent = `${title} (${domain})`;
                    tabTitleEl.title = response.url;
                } catch (e) {
                    tabTitleEl.textContent = response.title || 'Current Page';
                }
            } else {
                tabTitleEl.textContent = 'No tab info available';
            }
        });
    }

    /**
     * Extract content from current tab
     */
    function extractCurrentTab(statusEl, contentAreaEl, extractBtn) {
        console.log('[Chrome Tab Reader] Extract button clicked');

        // Disable button and show loading status
        extractBtn.disabled = true;
        showStatus(statusEl, 'loading', 'Extracting content...');
        contentAreaEl.innerHTML = '';
        contentAreaEl.classList.add('empty');

        // Send extraction request to service worker
        chrome.runtime.sendMessage(
            { action: 'extract_current_tab', strategy: 'three-phase' },
            (response) => {
                extractBtn.disabled = false;

                if (!response) {
                    showStatus(statusEl, 'error', 'No response from service worker');
                    return;
                }

                if (response.status === 'success') {
                    console.log('[Chrome Tab Reader] Extraction successful');
                    showStatus(statusEl, 'success', `Extracted ${response.content.length} characters in ${response.extraction_time_ms}ms`);
                    displayContent(contentAreaEl, response.content);
                } else {
                    console.error('[Chrome Tab Reader] Extraction error:', response.error);
                    showStatus(statusEl, 'error', `Error: ${response.error}`);
                }
            }
        );
    }

    /**
     * Display extracted content
     */
    function displayContent(contentAreaEl, content) {
        contentAreaEl.classList.remove('empty');
        contentAreaEl.textContent = content;
    }

    /**
     * Clear displayed content
     */
    function clearContent(contentAreaEl) {
        contentAreaEl.innerHTML = '<p>Click "Extract Content" to analyze the current page</p>';
        contentAreaEl.classList.add('empty');
        statusEl.textContent = '';
        statusEl.className = 'status';
    }

    /**
     * Show status message
     */
    function showStatus(statusEl, type, message) {
        statusEl.textContent = message;
        statusEl.className = `status ${type}`;
    }
}
