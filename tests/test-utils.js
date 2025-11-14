const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

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
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/snap/bin/chromium',
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

  // Launch Chrome with extension loaded (headful mode for local testing)
  const launchOptions = {
    headless: false, // Extensions work best in headful mode
    executablePath,
    args: [
      `--disable-extensions-except=${extensionPath}`,
      `--load-extension=${extensionPath}`,
      ...(options.args || [])
    ],
    dumpio: false,
    ...options
  };

  const browser = await puppeteer.launch(launchOptions);

  // Wait briefly for extension to load
  await delay(1000);

  // Get extension ID from service worker
  let extensionId = null;
  const targets = await browser.targets();
  const extensionTarget = targets.find(
    target => target.type() === 'service_worker' && target.url().includes('chrome-extension://')
  );

  if (extensionTarget) {
    const extensionUrl = extensionTarget.url();
    extensionId = extensionUrl.split('/')[2];
    console.log(`Extension loaded with ID: ${extensionId}`);
  } else {
    console.warn('Warning: Extension service worker not found. Tests may fail.');
  }

  return { browser, extensionId };
}

/**
 * Create a test page with specific content
 */
async function createTestPage(page, options = {}) {
  const {
    title = 'Test Page',
    content = '<h1>Test Content</h1><p>This is a test page.</p>',
    scripts = []
  } = options;

  const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>${title}</title>
</head>
<body>
  ${content}
  ${scripts.map(script => `<script>${script}</script>`).join('\n')}
</body>
</html>
  `;

  await page.setContent(html, { waitUntil: 'networkidle0' });
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
 * In headful mode this should be quick
 */
async function waitForContentScript(page, timeoutMs = 5000) {
  const startTime = Date.now();

  while (Date.now() - startTime < timeoutMs) {
    const isReady = await page.evaluate(() => {
      return typeof window.__chromeTabReader__ !== 'undefined';
    });

    if (isReady) {
      return true;
    }

    await delay(100);
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
    if (!window.__chromeTabReader__) {
      return {
        readability: false,
        dompurify: false
      };
    }

    return window.__chromeTabReader__.checkLibraries();
  });
}

module.exports = {
  delay,
  getExtensionPath,
  verifyExtensionFiles,
  launchBrowserWithExtension,
  createTestPage,
  waitForExtension,
  waitForContentScript,
  getServiceWorker,
  openPopup,
  extractContent,
  checkLibrariesLoaded
};
