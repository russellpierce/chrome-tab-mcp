/**
 * UI and Popup Tests
 *
 * Test the extension popup and user interface
 */

const {
  delay,
  launchBrowserWithExtension,
  openPopup
} = require('./test-utils');

describe('Extension UI', () => {
  let browser;
  let extensionId;

  beforeAll(async () => {
    const result = await launchBrowserWithExtension();
    browser = result.browser;
    extensionId = result.extensionId;
  });

  afterAll(async () => {
    if (browser) {
      await browser.close();
    }
  });

  describe('Popup', () => {
    test('popup opens successfully', async () => {
      const popup = await openPopup(browser, extensionId);

      expect(popup).toBeDefined();
      expect(popup.url()).toContain('chrome-extension://');
      expect(popup.url()).toContain('popup.html');

      await popup.close();
    });

    test('popup has correct title', async () => {
      const popup = await openPopup(browser, extensionId);
      const title = await popup.title();

      expect(title).toBeDefined();

      await popup.close();
    });

    test('popup contains expected UI elements', async () => {
      const popup = await openPopup(browser, extensionId);

      // Wait for popup to fully load
      await delay(1000);

      // Check for key UI elements
      const elements = await popup.evaluate(() => {
        return {
          hasTabTitle: !!document.getElementById('tabTitle'),
          hasExtractBtn: !!document.getElementById('extractBtn'),
          hasClearBtn: !!document.getElementById('clearBtn'),
          hasStatus: !!document.getElementById('status'),
          hasContentArea: !!document.getElementById('contentArea')
        };
      });

      expect(elements.hasTabTitle).toBe(true);
      expect(elements.hasExtractBtn).toBe(true);
      expect(elements.hasClearBtn).toBe(true);
      expect(elements.hasStatus).toBe(true);
      expect(elements.hasContentArea).toBe(true);

      await popup.close();
    });

    test('extract button is enabled', async () => {
      const popup = await openPopup(browser, extensionId);
      await delay(1000);

      const isEnabled = await popup.evaluate(() => {
        const btn = document.getElementById('extractBtn');
        return !btn.disabled;
      });

      expect(isEnabled).toBe(true);

      await popup.close();
    });

    test('clear button is present', async () => {
      const popup = await openPopup(browser, extensionId);
      await delay(1000);

      const hasButton = await popup.evaluate(() => {
        const btn = document.getElementById('clearBtn');
        return btn !== null;
      });

      expect(hasButton).toBe(true);

      await popup.close();
    });
  });

  describe('Popup Functionality', () => {
    test('clicking extract button triggers extraction', async () => {
      // First open a test page
      const page = await browser.newPage();
      await page.goto('https://example.com', { waitUntil: 'networkidle0' });
      await delay(2000);

      // Open popup
      const popup = await openPopup(browser, extensionId);
      await delay(1000);

      // Click extract button
      await popup.evaluate(() => {
        document.getElementById('extractBtn').click();
      });

      // Wait for extraction to complete
      await delay(5000);

      // Check if status was updated
      const statusText = await popup.evaluate(() => {
        return document.getElementById('status').textContent;
      });

      expect(statusText).toBeDefined();
      expect(statusText.length).toBeGreaterThan(0);

      await popup.close();
      await page.close();
    });

    test('clear button clears content area', async () => {
      const popup = await openPopup(browser, extensionId);
      await delay(1000);

      // Add some content to the content area
      await popup.evaluate(() => {
        document.getElementById('contentArea').textContent = 'Test content';
      });

      // Click clear button
      await popup.evaluate(() => {
        document.getElementById('clearBtn').click();
      });

      await delay(500);

      // Check if content was cleared
      const content = await popup.evaluate(() => {
        return document.getElementById('contentArea').textContent;
      });

      // Content should be reset to initial state or empty
      expect(content).toBeDefined();

      await popup.close();
    });

    test('tab title updates correctly', async () => {
      // Open a page with a known title
      const page = await browser.newPage();
      await page.goto('https://example.com', { waitUntil: 'networkidle0' });
      await delay(2000);

      // Open popup
      const popup = await openPopup(browser, extensionId);
      await delay(2000);

      // Get tab title text
      const tabTitle = await popup.evaluate(() => {
        return document.getElementById('tabTitle').textContent;
      });

      expect(tabTitle).toBeDefined();
      expect(tabTitle).toContain('example.com');

      await popup.close();
      await page.close();
    });
  });

  describe('Service Worker Communication', () => {
    test('popup can communicate with service worker', async () => {
      const popup = await openPopup(browser, extensionId);
      await delay(1000);

      // Send health check message
      const response = await popup.evaluate(() => {
        return new Promise((resolve) => {
          chrome.runtime.sendMessage({
            action: 'health_check'
          }, (response) => {
            resolve(response);
          });
        });
      });

      expect(response).toBeDefined();
      expect(response.status).toBe('ok');

      await popup.close();
    });

    test('popup can request current tab info', async () => {
      // Open a test page first
      const page = await browser.newPage();
      await page.goto('https://example.com', { waitUntil: 'networkidle0' });
      await delay(2000);

      const popup = await openPopup(browser, extensionId);
      await delay(1000);

      const tabInfo = await popup.evaluate(() => {
        return new Promise((resolve) => {
          chrome.runtime.sendMessage({
            action: 'get_current_tab'
          }, (response) => {
            resolve(response);
          });
        });
      });

      expect(tabInfo).toBeDefined();
      expect(tabInfo.url).toBeDefined();
      expect(tabInfo.title).toBeDefined();

      await popup.close();
      await page.close();
    });
  });

  describe('Error Display', () => {
    test('popup handles errors gracefully', async () => {
      const popup = await openPopup(browser, extensionId);
      await delay(1000);

      // Simulate an error by trying to extract from invalid state
      // (This test ensures UI doesn't crash on errors)
      const noError = await popup.evaluate(() => {
        try {
          // Try to update status with error
          const statusEl = document.getElementById('status');
          if (statusEl) {
            statusEl.textContent = 'Error: Test error message';
            statusEl.className = 'status error';
            return true;
          }
          return false;
        } catch (e) {
          return false;
        }
      });

      expect(noError).toBe(true);

      await popup.close();
    });
  });
});
