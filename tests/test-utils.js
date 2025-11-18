const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

// Load environment variables from .env file
require('dotenv').config();

/**
 * Test utilities for Chrome extension testing
 */

/**
 * Delay helper function to replace deprecated page.waitForTimeout()
 * @param {number} ms - Milliseconds to wait
 * @returns {Promise}
 */
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Get the path to the extension directory
 */
function getExtensionPath() {
  return path.resolve(__dirname, '../extension');
}

/**
 * Verify extension files exist
 */
function verifyExtensionFiles() {
  const extensionPath = getExtensionPath();
  const requiredFiles = [
    'manifest.json',
    'content_script.js',
    'service_worker.js',
    'popup.html',
    'popup.js',
    'lib/readability.min.js',
    'lib/dompurify.min.js'
  ];

  const results = {
    extensionPath,
    allExist: true,
    missing: [],
    existing: []
  };

  for (const file of requiredFiles) {
    const filePath = path.join(extensionPath, file);
    if (fs.existsSync(filePath)) {
      results.existing.push(file);
    } else {
      results.missing.push(file);
      results.allExist = false;
    }
  }

  return results;
}

/**
 * Launch Chrome with extension loaded
 * @param {Object} options - Launch options
 * @returns {Promise<{browser: Browser, extensionId: string}>}
 */
async function launchBrowserWithExtension(options = {}) {
  const extensionPath = getExtensionPath();

  // Find Chrome executable path
  const chromePaths = [
    // Windows paths
    process.env.LOCALAPPDATA ? path.join(process.env.LOCALAPPDATA, 'Google\\Chrome\\Application\\chrome.exe') : null,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    // macOS paths
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    // Linux paths
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/snap/bin/chromium',
    // User override
    process.env.CHROME_PATH
  ].filter(Boolean);

  let executablePath = null;
  for (const chromePath of chromePaths) {
    if (fs.existsSync(chromePath)) {
      executablePath = chromePath;
      break;
    }
  }

  if (!executablePath) {
    throw new Error(
      'Chrome/Chromium not found. Please install Chrome or set CHROME_PATH environment variable.\n' +
      'Searched paths:\n' + chromePaths.join('\n')
    );
  }

  console.log(`Using Chrome at: ${executablePath}`);

  // Use the modern Puppeteer extension API
  const launchOptions = {
    headless: false, // Extensions require headful mode
    executablePath,
    pipe: true, // Required for enableExtensions
    enableExtensions: [extensionPath],
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--no-default-browser-check',
      '--no-first-run',
      ...(options.args || [])
    ],
    dumpio: false,
    ...options
  };

  const browser = await puppeteer.launch(launchOptions);

  // Wait for extension to load using the service worker file
  let extensionId = null;
  try {
    console.log('Waiting for extension service worker to load...');
    const serviceWorkerTarget = await browser.waitForTarget(
      target => target.type() === 'service_worker' && target.url().endsWith('service_worker.js'),
      { timeout: 15000 }
    );
    
    const extensionUrl = serviceWorkerTarget.url();
    extensionId = extensionUrl.split('/')[2];
    console.log(`Extension loaded with ID: ${extensionId}`);
  } catch (error) {
    console.warn('Warning: Extension service worker not found within timeout. Checking for any chrome-extension targets...');
    
    // Fallback: look for any chrome-extension target
    const targets = await browser.targets();
    const extensionTarget = targets.find(
      target => target.url().includes('chrome-extension://')
    );
    
    if (extensionTarget) {
      const extensionUrl = extensionTarget.url();
      extensionId = extensionUrl.split('/')[2];
      console.log(`Extension found with ID: ${extensionId} (type: ${extensionTarget.type()})`);
    } else {
      console.warn('Warning: No extension targets found. Tests may fail.');
    }
  }

  return { browser, extensionId };
}

/**
 * Load a static test page from GitHub Pages
 */
async function loadTestPage(page, testPageName = 'test-simple.html') {
  // Use GitHub Pages to serve rendered HTML (not raw text)
  const baseUrl = 'https://russellpierce.github.io/chrome-tab-mcp/tests/test-pages';
  const webUrl = `${baseUrl}/${testPageName}`;
  
  console.log(`[Test] Loading test page: ${webUrl}`);
  
  try {
    await page.goto(webUrl, { waitUntil: 'networkidle0', timeout: 10000 });
  } catch (error) {
    console.log(`[Test] Failed to load from GitHub Pages, trying fallback...`);
    // Fallback to example.com if GitHub Pages isn't set up yet
    await page.goto('https://example.com', { waitUntil: 'networkidle0' });
  }
  
  // Give time for content script to inject (works on HTTP/HTTPS)
  await delay(5000);

  console.log(`[Test] Test page loaded: ${testPageName}`);
}

/**
 * Create a test page with specific content (legacy function - now uses static pages)
 */
async function createTestPage(page, options = {}) {
  const {
    type = 'simple', // simple, complex, keywords, readability
    title = 'Test Page',
    content = '<h1>Test Content</h1><p>This is a test page.</p>',
    scripts = []
  } = options;

  // Map content types to static test pages
  const testPageMap = {
    'simple': 'test-simple.html',
    'complex': 'test-complex.html', 
    'keywords': 'test-keywords.html',
    'readability': 'test-readability.html'
  };
  
  const testPageName = testPageMap[type] || 'test-simple.html';
  await loadTestPage(page, testPageName);
}

/**
 * Wait for extension to be ready
 */
async function waitForExtension(browser, extensionId, timeoutMs = 10000) {
  const startTime = Date.now();

  while (Date.now() - startTime < timeoutMs) {
    const targets = await browser.targets();
    const extensionTarget = targets.find(
      target => target.type() === 'service_worker' && target.url().includes(extensionId)
    );

    if (extensionTarget) {
      return true;
    }

    await new Promise(resolve => setTimeout(resolve, 100));
  }

  return false;
}

/**
 * Get the service worker for the extension
 */
async function getServiceWorker(browser, extensionId) {
  const targets = await browser.targets();
  const serviceWorkerTarget = targets.find(
    target => target.type() === 'service_worker' && target.url().includes(extensionId)
  );

  if (!serviceWorkerTarget) {
    throw new Error('Service worker not found');
  }

  return await serviceWorkerTarget.worker();
}

/**
 * Open extension popup
 */
async function openPopup(browser, extensionId) {
  if (!extensionId) {
    throw new Error('Extension ID is null or undefined. Extension may not have loaded properly. Check if extension files exist and service worker is running.');
  }

  const popupUrl = `chrome-extension://${extensionId}/popup.html`;
  const page = await browser.newPage();

  try {
    await page.goto(popupUrl, { waitUntil: 'networkidle0', timeout: 10000 });
  } catch (error) {
    throw new Error(`Failed to load popup at ${popupUrl}: ${error.message}`);
  }

  return page;
}

/**
 * Wait for content script to be ready
 * Increased timeout to handle slower injection on some pages
 */
async function waitForContentScript(page, timeoutMs = 45000) {
  const startTime = Date.now();

  while (Date.now() - startTime < timeoutMs) {
    try {
      const isReady = await page.evaluate(() => {
        // Check if the content script global is available
        if (typeof window.__chromeTabReader__ !== 'undefined') {
          return true;
        }

        // Check if content script console logs suggest it's loading
        return document.readyState === 'complete' &&
               (window.Readability !== undefined || window.DOMPurify !== undefined);
      });

      if (isReady) {
        console.log('[Test] Content script is ready');
        return true;
      }
    } catch (error) {
      // Ignore evaluation errors and continue waiting
    }

    await delay(200);
  }

  throw new Error('Content script did not load within timeout. Make sure Chrome has the extension loaded.');
}

/**
 * Extract content using the extension
 * Calls the extension's exposed test API
 */
async function extractContent(page, options = {}) {
  // Wait for content script to be ready
  await waitForContentScript(page);

  const {
    strategy = 'three-phase',
    startKeyword = null,
    endKeyword = null
  } = options;

  // Call the extension's test API
  const result = await page.evaluate(async (opts) => {
    if (!window.__chromeTabReader__) {
      throw new Error('Chrome Tab Reader extension not loaded');
    }

    return await window.__chromeTabReader__.extractContent(opts);
  }, { strategy, startKeyword, endKeyword });

  return result;
}

/**
 * Check if libraries are loaded in the page
 */
async function checkLibrariesLoaded(page) {
  // Wait for content script to be ready
  await waitForContentScript(page);

  return await page.evaluate(() => {
    // First check if the content script API is available
    if (window.__chromeTabReader__ && window.__chromeTabReader__.checkLibraries) {
      return window.__chromeTabReader__.checkLibraries();
    }

    // Fallback: check if libraries are directly available in global scope
    return {
      readability: typeof window.Readability !== 'undefined',
      dompurify: typeof window.DOMPurify !== 'undefined'
    };
  });
}

/**
 * Test extension against a real website
 */
async function testAgainstRealSite(browser, url = 'https://github.com/russellpierce/chrome-tab-mcp') {
  const page = await browser.newPage();
  
  try {
    console.log(`Navigating to: ${url}`);
    await page.goto(url, { waitUntil: 'networkidle0', timeout: 30000 });
    
    // Wait longer for content script to load on real sites
    console.log('Waiting for content script to initialize...');
    await waitForContentScript(page, 15000); // Increased timeout
    
    // Test content extraction with simple strategy first
    console.log('Testing content extraction...');
    const result = await extractContent(page, { strategy: 'simple' });
    
    console.log('Successfully extracted content from real site');
    console.log(`Title: ${result.title}`);
    console.log(`Content length: ${result.content.length} characters`);
    
    return result;
  } finally {
    await page.close();
  }
}

module.exports = {
  delay,
  getExtensionPath,
  verifyExtensionFiles,
  launchBrowserWithExtension,
  loadTestPage,
  createTestPage,
  waitForExtension,
  waitForContentScript,
  getServiceWorker,
  openPopup,
  extractContent,
  checkLibrariesLoaded,
  testAgainstRealSite
};
