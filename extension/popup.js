/**
 * Chrome Tab Reader - Popup Script
 *
 * Manages the extension popup UI for content extraction
 */

document.addEventListener('DOMContentLoaded', initializePopup);

function initializePopup() {
    console.log('[Chrome Tab Reader] Initializing popup');

    // Get references to UI elements
    const accessTokenEl = document.getElementById('accessToken');
    const copyTokenBtn = document.getElementById('copyTokenBtn');
    const regenerateTokenBtn = document.getElementById('regenerateTokenBtn');
    const tabTitleEl = document.getElementById('tabTitle');
    const extractBtn = document.getElementById('extractBtn');
    const clearBtn = document.getElementById('clearBtn');
    const statusEl = document.getElementById('status');
    const contentAreaEl = document.getElementById('contentArea');
    const consoleOutputEl = document.getElementById('consoleOutput');
    const consoleHeaderEl = document.getElementById('consoleHeader');
    const consoleToggleEl = document.getElementById('consoleToggle');
    const consoleClearBtn = document.getElementById('consoleClearBtn');

    // Load and display access token
    loadAccessToken();

    // Update tab title on load
    updateTabTitle();

    // Set up console
    initializeConsole();

    // Set up event listeners
    copyTokenBtn.addEventListener('click', () => copyAccessToken());
    regenerateTokenBtn.addEventListener('click', () => regenerateAccessToken());
    extractBtn.addEventListener('click', () => extractCurrentTab(statusEl, contentAreaEl, extractBtn));
    clearBtn.addEventListener('click', () => clearContent(contentAreaEl));
    consoleHeaderEl.addEventListener('click', (e) => {
        // Don't toggle if clicking the clear button
        if (e.target !== consoleClearBtn) {
            toggleConsole();
        }
    });
    consoleClearBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        clearConsole();
    });

    /**
     * Load and display access token
     */
    function loadAccessToken() {
        chrome.runtime.sendMessage({ action: 'get_access_token' }, (token) => {
            if (token && !token.error) {
                accessTokenEl.textContent = token;
            } else {
                accessTokenEl.textContent = 'Error loading token';
            }
        });
    }

    /**
     * Copy access token to clipboard
     */
    function copyAccessToken() {
        const token = accessTokenEl.textContent;
        navigator.clipboard.writeText(token).then(() => {
            showStatus(statusEl, 'success', 'Token copied to clipboard');
            setTimeout(() => {
                statusEl.className = 'status';
            }, 2000);
        }).catch(err => {
            showStatus(statusEl, 'error', 'Failed to copy token');
        });
    }

    /**
     * Regenerate access token
     */
    function regenerateAccessToken() {
        if (!confirm('Regenerate access token? You will need to update it in your MCP server and scripts.')) {
            return;
        }

        chrome.runtime.sendMessage({ action: 'regenerate_access_token' }, (token) => {
            if (token && !token.error) {
                accessTokenEl.textContent = token;
                showStatus(statusEl, 'success', 'Token regenerated successfully');
            } else {
                showStatus(statusEl, 'error', 'Failed to regenerate token');
            }
        });
    }

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

    /**
     * Initialize console display
     */
    function initializeConsole() {
        // Listen for log messages from background and content scripts
        chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
            if (message.type === 'console_log') {
                addConsoleLog(message.level || 'info', message.message, message.source);
            }
        });

        // Add initial message
        addConsoleLog('info', 'Popup initialized', 'popup');
    }

    /**
     * Toggle console visibility
     */
    function toggleConsole() {
        const isOpen = consoleOutputEl.classList.toggle('open');
        consoleToggleEl.textContent = isOpen ? '▲' : '▼';
    }

    /**
     * Clear console output
     */
    function clearConsole() {
        consoleOutputEl.innerHTML = '';
        addConsoleLog('info', 'Console cleared', 'popup');
    }

    /**
     * Add a log message to the console display
     */
    function addConsoleLog(level, message, source) {
        const logEntry = document.createElement('div');
        logEntry.className = `console-log ${level}`;

        const timestamp = new Date().toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            fractionalSecondDigits: 3
        });

        const sourcePrefix = source ? `[${source}] ` : '';
        logEntry.textContent = `${timestamp} ${sourcePrefix}${message}`;

        consoleOutputEl.appendChild(logEntry);

        // Auto-scroll to bottom
        consoleOutputEl.scrollTop = consoleOutputEl.scrollHeight;

        // Keep max 100 log entries to prevent memory issues
        while (consoleOutputEl.children.length > 100) {
            consoleOutputEl.removeChild(consoleOutputEl.firstChild);
        }

        // Auto-open console on error or warn
        if ((level === 'error' || level === 'warn') && !consoleOutputEl.classList.contains('open')) {
            toggleConsole();
        }
    }

    // Expose functions for use in the popup scope
    window.addConsoleLog = addConsoleLog;
}
