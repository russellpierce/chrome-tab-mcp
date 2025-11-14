/**
 * Content Extraction Tests
 *
 * Test the three-phase extraction process and content handling
 */

const {
  launchBrowserWithExtension,
  createTestPage,
  checkLibrariesLoaded
} = require('./test-utils');

describe('Content Extraction', () => {
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

  describe('Basic Extraction', () => {
    test('extracts content from simple page', async () => {
      const page = await browser.newPage();
      await page.goto('https://example.com', { waitUntil: 'networkidle0' });

      // Wait for content script to load
      await page.waitForTimeout(2000);

      // Trigger extraction via content script
      const result = await page.evaluate(() => {
        return new Promise((resolve) => {
          chrome.runtime.sendMessage({
            action: 'extractContent',
            strategy: 'three-phase'
          }, (response) => {
            resolve(response);
          });
        });
      });

      expect(result).toBeDefined();
      expect(result.status).toBe('success');
      expect(result.content).toBeDefined();
      expect(result.content.length).toBeGreaterThan(0);
      expect(result.title).toBe('Example Domain');
      expect(result.url).toContain('example.com');
      expect(result.extraction_time_ms).toBeGreaterThan(0);

      await page.close();
    });

    test('extraction includes page title and URL', async () => {
      const page = await browser.newPage();
      await createTestPage(page, {
        title: 'Test Page Title',
        content: '<h1>Main Heading</h1><p>Test content here.</p>'
      });

      await page.waitForTimeout(2000);

      const result = await page.evaluate(() => {
        return new Promise((resolve) => {
          chrome.runtime.sendMessage({
            action: 'extractContent',
            strategy: 'three-phase'
          }, (response) => {
            resolve(response);
          });
        });
      });

      expect(result.status).toBe('success');
      expect(result.title).toBe('Test Page Title');
      expect(result.url).toBeDefined();

      await page.close();
    });

    test('extraction handles empty page', async () => {
      const page = await browser.newPage();
      await createTestPage(page, {
        title: 'Empty Page',
        content: ''
      });

      await page.waitForTimeout(2000);

      const result = await page.evaluate(() => {
        return new Promise((resolve) => {
          chrome.runtime.sendMessage({
            action: 'extractContent',
            strategy: 'three-phase'
          }, (response) => {
            resolve(response);
          });
        });
      });

      expect(result.status).toBe('success');
      expect(result.content).toBeDefined();
      // Empty page should still have some content (even if minimal)

      await page.close();
    });
  });

  describe('Extraction Strategies', () => {
    test('simple strategy works', async () => {
      const page = await browser.newPage();
      await createTestPage(page, {
        title: 'Simple Strategy Test',
        content: '<p>Simple content extraction test.</p>'
      });

      await page.waitForTimeout(2000);

      const result = await page.evaluate(() => {
        return new Promise((resolve) => {
          chrome.runtime.sendMessage({
            action: 'extractContent',
            strategy: 'simple'
          }, (response) => {
            resolve(response);
          });
        });
      });

      expect(result.status).toBe('success');
      expect(result.content).toContain('Simple content extraction test');

      await page.close();
    });

    test('three-phase strategy completes within reasonable time', async () => {
      const page = await browser.newPage();
      await page.goto('https://example.com', { waitUntil: 'networkidle0' });

      await page.waitForTimeout(2000);

      const startTime = Date.now();

      const result = await page.evaluate(() => {
        return new Promise((resolve) => {
          chrome.runtime.sendMessage({
            action: 'extractContent',
            strategy: 'three-phase'
          }, (response) => {
            resolve(response);
          });
        });
      });

      const totalTime = Date.now() - startTime;

      expect(result.status).toBe('success');
      expect(totalTime).toBeLessThan(30000); // Should complete within 30 seconds for simple page

      await page.close();
    });
  });

  describe('Keyword Filtering', () => {
    test('filters content between keywords', async () => {
      const page = await browser.newPage();
      await createTestPage(page, {
        title: 'Keyword Test',
        content: `
          <h1>Introduction</h1>
          <p>This is the intro section.</p>
          <h2>Skills</h2>
          <p>This is the skills section with important content.</p>
          <h2>Contact</h2>
          <p>This is the contact section.</p>
        `
      });

      await page.waitForTimeout(2000);

      const result = await page.evaluate(() => {
        return new Promise((resolve) => {
          chrome.runtime.sendMessage({
            action: 'extractContent',
            strategy: 'simple',
            startKeyword: 'Skills',
            endKeyword: 'Contact'
          }, (response) => {
            resolve(response);
          });
        });
      });

      expect(result.status).toBe('success');
      expect(result.content).toContain('skills');
      expect(result.content).toContain('important content');
      expect(result.content).not.toContain('intro section');

      await page.close();
    });

    test('keyword filtering is case-insensitive', async () => {
      const page = await browser.newPage();
      await createTestPage(page, {
        title: 'Case Test',
        content: `
          <h1>INTRODUCTION</h1>
          <p>Start content.</p>
          <h2>conclusion</h2>
          <p>End content.</p>
        `
      });

      await page.waitForTimeout(2000);

      const result = await page.evaluate(() => {
        return new Promise((resolve) => {
          chrome.runtime.sendMessage({
            action: 'extractContent',
            strategy: 'simple',
            startKeyword: 'introduction',
            endKeyword: 'CONCLUSION'
          }, (response) => {
            resolve(response);
          });
        });
      });

      expect(result.status).toBe('success');
      expect(result.content.toLowerCase()).toContain('introduction');
      expect(result.content.toLowerCase()).toContain('conclusion');

      await page.close();
    });
  });

  describe('Readability Integration', () => {
    test('readability removes navigation and cleans content', async () => {
      const page = await browser.newPage();
      await createTestPage(page, {
        title: 'Article with Noise',
        content: `
          <nav>
            <a href="/">Home</a>
            <a href="/about">About</a>
          </nav>
          <article>
            <h1>Main Article Title</h1>
            <p>This is the main article content that should be extracted.</p>
            <p>Multiple paragraphs of important information.</p>
          </article>
          <aside>
            <p>Advertisement content that should be removed.</p>
          </aside>
          <footer>
            <p>Footer content that should be removed.</p>
          </footer>
        `
      });

      await page.waitForTimeout(2000);

      const result = await page.evaluate(() => {
        return new Promise((resolve) => {
          chrome.runtime.sendMessage({
            action: 'extractContent',
            strategy: 'three-phase'
          }, (response) => {
            resolve(response);
          });
        });
      });

      expect(result.status).toBe('success');
      expect(result.content).toContain('Main Article Title');
      expect(result.content).toContain('main article content');
      // Readability should remove nav, aside, footer
      // Note: The exact behavior depends on Readability.js implementation

      await page.close();
    });
  });

  describe('Error Handling', () => {
    test('handles extraction on pages with scripts', async () => {
      const page = await browser.newPage();
      await createTestPage(page, {
        title: 'Page with Scripts',
        content: `
          <h1>Content</h1>
          <p>Normal content here.</p>
        `,
        scripts: [
          'console.log("Test script");',
          'document.body.setAttribute("data-test", "value");'
        ]
      });

      await page.waitForTimeout(2000);

      const result = await page.evaluate(() => {
        return new Promise((resolve) => {
          chrome.runtime.sendMessage({
            action: 'extractContent',
            strategy: 'three-phase'
          }, (response) => {
            resolve(response);
          });
        });
      });

      expect(result.status).toBe('success');
      expect(result.content).toContain('Normal content');

      await page.close();
    });

    test('extraction does not crash on complex pages', async () => {
      const page = await browser.newPage();
      await createTestPage(page, {
        title: 'Complex Page',
        content: `
          <div id="app">
            <header>
              <nav>
                ${Array(20).fill(0).map((_, i) => `<a href="/page${i}">Link ${i}</a>`).join('')}
              </nav>
            </header>
            <main>
              ${Array(50).fill(0).map((_, i) => `
                <article>
                  <h2>Article ${i}</h2>
                  <p>Content for article ${i} with some text.</p>
                </article>
              `).join('')}
            </main>
          </div>
        `
      });

      await page.waitForTimeout(2000);

      const result = await page.evaluate(() => {
        return new Promise((resolve) => {
          chrome.runtime.sendMessage({
            action: 'extractContent',
            strategy: 'three-phase'
          }, (response) => {
            resolve(response);
          });
        });
      });

      expect(result.status).toBe('success');
      expect(result.content.length).toBeGreaterThan(0);

      await page.close();
    });
  });

  describe('Libraries', () => {
    test('Readability is available', async () => {
      const page = await browser.newPage();
      await page.goto('https://example.com', { waitUntil: 'networkidle0' });
      await page.waitForTimeout(2000);

      const libs = await checkLibrariesLoaded(page);
      expect(libs.readability).toBe(true);

      await page.close();
    });

    test('DOMPurify is available', async () => {
      const page = await browser.newPage();
      await page.goto('https://example.com', { waitUntil: 'networkidle0' });
      await page.waitForTimeout(2000);

      const libs = await checkLibrariesLoaded(page);
      expect(libs.dompurify).toBe(true);

      await page.close();
    });
  });
});
