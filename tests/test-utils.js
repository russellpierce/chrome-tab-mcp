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

  // Use new headless mode in CI (supports extensions)
  // In local dev, use headful mode for debugging
  const isCI = process.env.CI === 'true' || process.env.GITHUB_ACTIONS === 'true';
  const headlessMode = isCI ? 'new' : false;

  const launchOptions = {
    headless: headlessMode,
    executablePath,
    args: [
      `--disable-extensions-except=${extensionPath}`,
      `--load-extension=${extensionPath}`,
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      ...(options.args || [])
    ],
    dumpio: false,
    ...options
  };

  const browser = await puppeteer.launch(launchOptions);

  // Get extension ID
  const targets = await browser.targets();
  const extensionTarget = targets.find(
    target => target.type() === 'service_worker' && target.url().includes('chrome-extension://')
  );

  let extensionId = null;
  if (extensionTarget) {
    const extensionUrl = extensionTarget.url();
    extensionId = extensionUrl.split('/')[2]; // Extract extension ID from URL
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
  const popupUrl = `chrome-extension://${extensionId}/popup.html`;
  const page = await browser.newPage();
  await page.goto(popupUrl, { waitUntil: 'networkidle0' });
  return page;
}

/**
 * Extract content using the extension
 */
async function extractContent(page, extensionId) {
  // Inject a script that sends a message to the content script
  const result = await page.evaluate((extId) => {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage(extId, {
        action: 'extractContent',
        strategy: 'three-phase'
      }, (response) => {
        resolve(response);
      });
    });
  }, extensionId);

  return result;
}

/**
 * Check if libraries are loaded in the page
 */
async function checkLibrariesLoaded(page) {
  return await page.evaluate(() => {
    return {
      readability: typeof Readability !== 'undefined',
      dompurify: typeof DOMPurify !== 'undefined'
    };
  });
}

module.exports = {
  delay,
  getExtensionPath,
  verifyExtensionFiles,
  launchBrowserWithExtension,
  createTestPage,
  waitForExtension,
  getServiceWorker,
  openPopup,
  extractContent,
  checkLibrariesLoaded
};
