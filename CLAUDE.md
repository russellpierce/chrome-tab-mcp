# CLAUDE.md - AI Assistant Development Guide

> **Note:** This document is AI-authored with very limited human oversight.

This guide helps AI assistants (like Claude Code) understand the Chrome Tab Reader codebase structure, development workflows, and conventions. It serves as a comprehensive reference for working effectively with this repository.

## Table of Contents

- [Repository Overview](#repository-overview)
- [Architecture Overview](#architecture-overview)
- [Directory Structure](#directory-structure)
- [Development Setup](#development-setup)
  - [Cloud/Web Environment Limitations](#cloudweb-environment-limitations)
- [Code Conventions](#code-conventions)
- [Testing Strategy](#testing-strategy)
- [Git Workflow](#git-workflow)
- [Common Tasks](#common-tasks)
- [Important Gotchas](#important-gotchas)
- [Dependencies](#dependencies)

---

## Repository Overview

**Project Name:** Chrome Tab Reader
**Purpose:** Extract and analyze content from Chrome tabs using AI assistance.  In particular distill contents from a tab before reporting back to a more expensive model.
**Primary Language:** JavaScript (extension), Python (servers)
**License:** [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)

### What This Project Does

Chrome Tab Reader provides three ways to access and process Chrome tab content:

1. **Chrome Extension** - Browser extension with UI for manual content extraction
2. **HTTP Server** - FastAPI REST API with token-based authentication
3. **MCP Server** - Model Context Protocol server for Claude Code integration with local Ollama

### Key Features

- Three-phase content extraction (lazy-loading trigger, DOM stability wait, Readability.js)
- Intelligent content cleaning (removes navigation, ads, footers)
- Token-based access control for security
- Cross-platform support (Windows, macOS, Linux)
- Native Messaging bridge for extension-MCP communication

---

## Architecture Overview

### Component Interaction

```
User/Claude Code
    ↓
┌───────────────────────────────────────────────────────────┐
│ Access Methods (choose one):                              │
│                                                            │
│ 1. Browser Extension UI (popup.html/popup.js)            │
│                                                            │
│ 2. HTTP API Server (chrome_tab_http_server.py)           │
│    - Port 8888                                            │
│    - Requires Bearer token authentication                 │
│    - RESTful API with OpenAPI/Swagger docs                │
│                                                            │
│ 3. MCP Server (chrome_tab_mcp_server.py)                 │
│    - Uses Native Messaging bridge                         │
│    - Integrates with local Ollama                         │
│    - Bi-directional communication via TCP (port 8765)     │
└───────────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────────┐
│ Chrome Extension Core                                      │
│                                                            │
│ Service Worker (service_worker.js)                        │
│ - HTTP server on localhost:8888                           │
│ - Native Messaging host communication                      │
│ - Token generation and management                          │
│ - Request routing                                          │
│                                                            │
│ Content Script (content_script.js)                        │
│ - Three-phase extraction pipeline                         │
│ - DOM manipulation and observation                         │
│ - Readability.js + DOMPurify integration                  │
└───────────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────────┐
│ Web Page Content (extracted and sanitized)                │
└───────────────────────────────────────────────────────────┘
```

### Three-Phase Content Extraction

**Phase 1: Trigger Lazy-Loading (2-5s)**
- Simulates scrolling to trigger lazy-loaded content
- Handles infinite scroll, "Load More" buttons, lazy images
- Scrolls to bottom up to 5 times, checking for new content

**Phase 2: Wait for DOM Stability (up to 30 sec)**
- Uses MutationObserver to detect when DOM stops changing
- Resolves when no changes for 2 consecutive seconds
- Hard timeout at 30 seconds
- Handles SPAs (React/Vue), live feeds, dynamic forms

**Phase 3: Extract with Readability.js**
- Mozilla's proven content extraction algorithm
- Removes navigation, ads, sidebars, comments
- Sanitizes with DOMPurify
- Fallback to `document.body.innerText` on failure

---

## Directory Structure

```
chrome-tab-mcp/
├── extension/                    # Chrome extension (Manifest v3)
│   ├── manifest.json            # Extension configuration
│   ├── service_worker.js        # Background service (HTTP server, messaging)
│   ├── content_script.js        # DOM extraction logic (three-phase)
│   ├── popup.html               # Extension popup UI
│   ├── popup.js                 # Popup interaction logic
│   ├── lib/                     # Third-party libraries
│   │   ├── readability.min.js   # Mozilla Readability (~40KB)
│   │   └── dompurify.min.js     # DOMPurify sanitizer (~10KB)
│   ├── ARCHITECTURE.md          # Detailed architecture documentation
│   ├── SETUP.md                 # Extension setup guide
│   ├── TESTING.md               # Extension testing procedures
│   └── README.md                # Extension overview
│
├── tests/                        # Automated test suites
│   ├── installation.test.js     # Extension installation tests (Jest)
│   ├── extraction.test.js       # Content extraction tests (Jest)
│   ├── ui.test.js               # UI interaction tests (Jest)
│   ├── test-utils.js            # Shared test utilities
│   ├── test_http_server.py      # HTTP API tests (pytest)
│   ├── test_native_messaging.py # Native messaging tests (pytest)
│   ├── test_e2e_native_messaging.py  # E2E tests (pytest)
│   └── test-pages/              # Test HTML pages
│
├── .github/                      # GitHub configuration
│   └── workflows/
│       └── test-extension.yml   # CI/CD workflow (file structure tests)
│
├── chrome_tab_mcp_server.py     # MCP server (FastMCP, Ollama integration)
├── chrome_tab_http_server.py    # HTTP API server (FastAPI)
├── chrome_tab_native_host.py    # Native messaging bridge
├── install_native_host.sh       # Linux/macOS native host installer
├── install_native_host.ps1      # Windows native host installer
├── setup_token.sh               # Token configuration helper
│
├── package.json                 # Node.js dependencies & test scripts
├── pyproject.toml               # Python project metadata (PEP 723)
├── requirements.txt             # Python dependencies
├── pytest.ini                   # Pytest configuration
│
├── README.md                    # Main project documentation
├── NATIVE_MESSAGING_SETUP.md    # Native messaging setup guide
├── ACCESS_CONTROL_SETUP.md      # Token authentication guide
├── CLAUDE.md                    # This file (AI assistant guide)
│
├── .env.example                 # Environment variables template
├── tokens.json.example          # Token configuration template
├── chrome_tab_mcp_config.json   # MCP server config (Claude Code)
├── .gitignore                   # Git ignore patterns
└── LICENSE                      # ISC/MIT license
```

### Key Files to Know

**Extension Core:**
- `extension/service_worker.js` - Background service, HTTP server, messaging hub
- `extension/content_script.js` - DOM extraction, three-phase pipeline
- `extension/manifest.json` - Extension permissions and configuration

**Python Servers:**
- `chrome_tab_http_server.py` - HTTP API (FastAPI, port 8888, token auth)
- `chrome_tab_mcp_server.py` - MCP server (FastMCP, Ollama, native messaging)
- `chrome_tab_native_host.py` - Native messaging bridge (TCP server on 8765)

**Testing:**
- `tests/*.test.js` - JavaScript tests (Jest + Puppeteer)
- `tests/test_*.py` - Python tests (pytest, marked by test type)

**Configuration:**
- `package.json` - Node scripts: `test`, `test:install`, `test:extraction`, `test:ui`
- `pyproject.toml` - Python deps, pytest config, test markers

---

## Development Setup

### Prerequisites

- **Node.js:** v20+ (LTS recommended)
- **npm:** v10+ (comes with Node.js)
- **Python:** 3.10+ (3.8+ for servers)
- **Chrome/Chromium:** Latest stable
- **REQUIRED:** `uv` for Python dependency management

### Initial Setup

1. **Clone and navigate to repository:**
   ```bash
   git checkout <your-branch>  # Usually claude/* branches
   ```

2. **Install Node.js dependencies:**
   ```bash
   npm install
   ```

3. **Install Python dependencies:**
   ```bash
   # Option A: Using uv (recommended, handles PEP 723 metadata automatically)
   uv run chrome_tab_http_server.py --help

   # Option B: Using uv to install from requirements.txt
   uv pip install -r requirements.txt
   ```

4. **Load extension in Chrome:**
   - Navigate to `chrome://extensions/`
   - Enable "Developer mode" (top right)
   - Click "Load unpacked"
   - Select the `extension/` directory
   - Note the Extension ID (needed for native messaging)

5. **Optional - Set up Native Messaging:**
   ```bash
   # Linux/macOS
   ./install_native_host.sh <extension-id>

   # Windows PowerShell
   .\install_native_host.ps1 <extension-id>
   ```

6. **Optional - Configure HTTP API tokens:**
   ```bash
   ./setup_token.sh
   # Or manually create tokens.json (see ACCESS_CONTROL_SETUP.md)
   ```

### Verification

The repository includes a comprehensive test runner script:

```bash
# Quick verification (no Chrome needed - works in web environments)
./run_tests.sh ci

# Full test suite (requires Chrome locally)
./run_tests.sh all

# Specific test categories
./run_tests.sh unit         # Python unit tests
./run_tests.sh extension    # npm extension tests (requires Chrome)
./run_tests.sh e2e          # End-to-end tests (requires Chrome)

# See all options
./run_tests.sh help
```

**For web environments (Claude Code web, GitHub Actions):**
```bash
# CI-safe tests (no Chrome required)
./run_tests.sh ci

# Or manually run Python unit tests
uv run pytest tests/test_http_server.py -v
uv run pytest tests/test_native_messaging.py -v -m "not integration and not e2e"
```

**For local environments with Chrome:**
```bash
# Run all tests (Python + npm extension tests)
./run_tests.sh all

# Or run separately
npm test                    # Extension tests (Jest + Puppeteer)
./run_tests.sh unit         # Python unit tests
```

### Cloud/Web Environment Limitations

**PowerShell Testing:**

The repository includes PowerShell test scripts (`run_tests.ps1`) for Windows environments. However, PowerShell cannot be installed in cloud/web environments (like Claude Code web interface) due to:

1. **Network restrictions** - External downloads from GitHub releases are blocked
2. **Package manager limitations** - `apt` repositories require privileged access and have network restrictions
3. **Security policies** - Installation of system-level tools is restricted

**Workarounds:**
- **Syntax validation**: PowerShell scripts can still be edited and syntax-checked using standard text tools
- **Local testing**: Test PowerShell scripts in local environments with PowerShell installed
- **Cross-platform testing**: Use `run_tests.sh` (Bash) for CI-safe testing in cloud environments
- **Dual scripts**: The project maintains both Bash (`run_tests.sh`) and PowerShell (`run_tests.ps1`) versions for cross-platform compatibility

**PowerShell Installation (Local Environments Only):**
```bash
# Ubuntu/Debian
wget https://github.com/PowerShell/PowerShell/releases/download/v7.4.6/powershell-7.4.6-linux-x64.tar.gz
mkdir -p ~/.local/bin/powershell
tar -xzf powershell-7.4.6-linux-x64.tar.gz -C ~/.local/bin/powershell
ln -s ~/.local/bin/powershell/pwsh ~/.local/bin/pwsh

# Windows
# Already installed or via winget: winget install Microsoft.PowerShell

# macOS
brew install --cask powershell
```

**Environment Detection:**
```bash
# Check if running in restricted environment
if ! curl -s -o /dev/null -w "%{http_code}" https://github.com 2>&1 | grep -q "200"; then
    echo "Running in restricted cloud/web environment"
    echo "Use ./run_tests.sh ci for testing"
fi
```

---

## Code Conventions

### JavaScript (Extension)

**File Organization:**
- Use clear, descriptive function names
- Group related functions together
- Add JSDoc comments for complex functions
- Use `async/await` for asynchronous operations

**Naming Conventions:**
- Functions: `camelCase` (e.g., `extractContent`, `waitForDOMStability`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `BRIDGE_PORT`, `MAX_RETRIES`)
- Event handlers: prefix with `handle` (e.g., `handleExtractClick`)

**Error Handling:**
- Always wrap critical operations in try-catch
- Provide user-friendly error messages
- Log detailed errors to console for debugging
- Graceful degradation (fallback to simpler methods)

**Example:**
```javascript
async function extractContent(strategy = 'three-phase') {
    try {
        if (strategy === 'three-phase') {
            await triggerLazyLoading();
            await waitForDOMStability();
        }
        return extractWithReadability();
    } catch (error) {
        console.error('[Chrome Tab Reader] Extraction failed:', error);
        return document.body.innerText;  // Fallback
    }
}
```

### Python (Servers)

**File Organization:**
- Use PEP 723 inline script metadata for dependencies
- Group imports: stdlib, third-party, local
- Add docstrings to modules, classes, and functions
- Use type hints for function parameters and returns

**Naming Conventions:**
- Functions/variables: `snake_case` (e.g., `process_chrome_tab`, `bridge_port`)
- Classes: `PascalCase` (e.g., `ExtractRequest`, `TokenValidator`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `BRIDGE_HOST`, `DEFAULT_SYSTEM_PROMPT`)

**Error Handling:**
- **NEVER catch bare exceptions** - Always catch specific exception types (e.g., `OSError`, `ValueError`, `ConnectionError`)
- Only catch exceptions you can actually handle - let others propagate
- Log errors with appropriate levels (INFO, WARNING, ERROR)
- **When logging at ERROR level:** Use `logger.exception()` for unexpected errors (captures stack trace) vs `logger.error()` for expected errors (no stack trace needed)
- For expected exceptions where you don't need a stack trace, use `logger.error()` or `logger.warning()`
- Use FastAPI's HTTPException for API errors
- Return structured error responses with details

**Exception Handling Examples:**
```python
# GOOD: Specific exceptions, logger.exception() for unexpected errors
try:
    sock.close()
except (OSError, socket.error):
    # Expected error when closing socket - no stack trace needed
    pass

try:
    result = some_operation()
except ValueError as e:
    logger.error(f"Invalid value: {e}")  # Expected error, no stack trace
    raise
except Exception as e:
    logger.exception(f"Unexpected error")  # Unexpected - capture stack trace
    raise

# BAD: Bare exception
try:
    sock.close()
except:  # ❌ Don't do this - too broad
    pass

# BAD: Using logger.error() for unexpected exceptions
try:
    result = some_operation()
except Exception as e:
    logger.error(f"Error: {e}")  # ❌ Missing stack trace
    raise
```

**Example:**
```python
def get_chrome_extension_directories() -> list[Path]:
    """Get platform-specific Chrome extension directories.

    Returns:
        List of possible extension installation directories.

    Raises:
        ValueError: If platform is not supported.
    """
    system = platform.system()
    if system == "Darwin":  # macOS
        return [Path.home() / "Library/Application Support/Google/Chrome/Default/Extensions"]
    elif system == "Windows":
        return [Path.home() / "AppData/Local/Google/Chrome/User Data/Default/Extensions"]
    elif system == "Linux":
        return [Path.home() / ".config/google-chrome/Default/Extensions"]
    else:
        raise ValueError(f"Unsupported platform: {system}")
```

### Documentation

**All documentation is AI-authored with very limited human oversight** - always include this note:
```markdown
> **Note:** This document is AI-authored with very limited human oversight.
```

**Markdown Conventions:**
- Use clear headings (H1 for title, H2 for sections, H3 for subsections)
- Include code examples with syntax highlighting
- Use tables for comparisons and structured data
- Add "Table of Contents" for documents > 200 lines

---

## Testing Strategy

### Test Categories

**JavaScript Tests (Jest + Puppeteer):**
1. **Installation Tests** (`installation.test.js`)
   - File structure validation
   - Extension loading in Chrome
   - Service worker activation

2. **Extraction Tests** (`extraction.test.js`)
   - Three-phase extraction pipeline
   - Content cleaning and sanitization
   - Fallback mechanisms

3. **UI Tests** (`ui.test.js`)
   - Popup rendering
   - Button interactions
   - Token display

**Python Tests (pytest):**
- Marked with categories: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`
- **Unit Tests:** No Chrome needed, use mocks (run in CI)
- **Integration Tests:** Require Chrome + native host (local only)
- **E2E Tests:** Full stack with Playwright (local only)

### Running Tests

**Using the test runner (recommended):**
```bash
./run_tests.sh              # Run all tests (default)
./run_tests.sh ci           # CI-safe tests (no Chrome - for web environments)
./run_tests.sh unit         # Python unit tests only
./run_tests.sh extension    # npm extension tests (requires Chrome)
./run_tests.sh e2e          # End-to-end tests (requires Chrome + Playwright)
./run_tests.sh manual       # Interactive manual tests
./run_tests.sh coverage     # Tests with coverage report
./run_tests.sh help         # Show all options
```

**Manual test commands:**
```bash
# JavaScript/Extension Tests (requires Chrome locally)
npm test                    # All extension tests
npm run test:install        # Installation only
npm run test:extraction     # Extraction only
npm run test:ui             # UI only
npm run test:watch          # Watch mode
npm run test:coverage       # With coverage report

# Python Tests (use uv run for proper environment)
uv run pytest tests/                           # All tests
uv run pytest tests/test_http_server.py        # HTTP server only
uv run pytest -m unit                          # Unit tests only (CI-safe)
uv run pytest -m integration                   # Integration tests (local only)
uv run pytest -m e2e                           # E2E tests (local only)
uv run pytest --cov                            # With coverage
```

### CI/CD

**GitHub Actions:** `.github/workflows/test-extension.yml`
- Triggers on push to `main`, `master`, `develop`, `claude/*` branches
- Runs file structure tests only (via npm test with pattern filter)
- Node.js 20 environment
- Skips Puppeteer download to save time

**For more comprehensive CI testing:**
The `./run_tests.sh ci` command runs all CI-safe tests including:
- Python unit tests (HTTP server, native messaging protocol)
- No Chrome required - works in web environments and GitHub Actions
- Uses `uv run` for proper Python environment management

---

## Git Workflow

### Branch Naming

- **Feature branches:** `claude/<description>-<session-id>`
  - Example: `claude/add-streaming-support-019KRtfd4MU4ms3ZHWrkgfQG`
- **Main branches:** `main`, `master`, `develop`

### Commit Guidelines

**Always follow these rules when committing:**

1. **Run tests before committing:**
   ```bash
   # In web environments (Claude Code web) - run CI-safe tests
   ./run_tests.sh ci

   # In local environments with Chrome - run all tests
   ./run_tests.sh all
   ```

2. **Commit message format:**
   - Be concise (1-2 sentences)
   - Focus on "why" not "what"
   - Examples:
     - "Add automatic Chrome extension ID detection to MCP server"
     - "Fix GitHub CI tests by updating workflow configuration"
     - "Convert wrapper to true one-liner to avoid line ending issues"

3. **Use HEREDOC for commit messages:**
   ```bash
   git commit -m "$(cat <<'EOF'
   Add streaming support for large content extraction

   Implements WebSocket endpoint for chunked content delivery
   to prevent timeout issues with large pages.
   EOF
   )"
   ```

4. **Never commit secrets:**
   - `.env` files (gitignored)
   - `tokens.json` files (gitignored)
   - API keys or credentials

### Push Strategy

**Always push to the correct branch:**
```bash
git push -u origin claude/<your-branch-name>
```

**Retry on network errors:**
- Retry up to 4 times with exponential backoff (2s, 4s, 8s, 16s)

### Creating Pull Requests

**Note:** The GitHub CLI (`gh`) is not available in all environments (e.g., web-based Claude Code), but is available in local Claude installations.

**When `gh` is available:**
```bash
# Ensure you're on the correct branch
git status

# Push changes
git push -u origin claude/<branch-name>

# Create PR with summary and test plan
gh pr create --title "Add feature X" --body "$(cat <<'EOF'
## Summary
- Added feature X to improve Y
- Updated tests to cover new functionality

## Test plan
- [ ] Run `npm test` and verify all tests pass
- [ ] Manual test: Load extension and extract content
- [ ] Verify HTTP API still works with token auth
EOF
)"
```

**When `gh` is not available:**
```bash
# Push changes
git push -u origin claude/<branch-name>

# Then inform the user that the branch is pushed and provide:
# 1. The branch name
# 2. A summary of changes made
# 3. Suggested PR title and description
# The user can create the PR manually via GitHub web interface
```

---

## Common Tasks

### Task: Fix a Bug in Content Extraction

1. **Identify the issue:**
   - Check browser console for errors (F12)
   - Review `extension/content_script.js` (extraction logic)
   - Check which phase is failing (lazy-loading, DOM stability, Readability)

2. **Make changes:**
   ```bash
   # Edit the content script
   # extension/content_script.js
   ```

3. **Test locally:**
   ```bash
   # Reload extension in chrome://extensions/
   # Test on problematic webpage
   npm run test:extraction
   ```

4. **Commit and push:**
   ```bash
   git add extension/content_script.js
   git commit -m "Fix extraction timeout for heavy SPAs"
   git push -u origin claude/<branch-name>
   ```

### Task: Add a New HTTP API Endpoint

1. **Update FastAPI server:**
   ```python
   # chrome_tab_http_server.py

   @app.post("/api/new_endpoint", dependencies=[Depends(verify_token)])
   async def new_endpoint(request: NewRequest):
       """New endpoint description."""
       # Implementation
       return {"status": "success", "data": result}
   ```

2. **Add Pydantic model:**
   ```python
   class NewRequest(BaseModel):
       param: str = Field(..., description="Parameter description")
   ```

3. **Add tests:**
   ```python
   # tests/test_http_server.py

   @pytest.mark.unit
   def test_new_endpoint(mock_bridge, test_client):
       response = test_client.post(
           "/api/new_endpoint",
           headers={"Authorization": "Bearer test-token"},
           json={"param": "value"}
       )
       assert response.status_code == 200
   ```

4. **Test and verify:**
   ```bash
   pytest tests/test_http_server.py::test_new_endpoint
   # Start server and check Swagger UI at http://localhost:8888/docs
   ```

### Task: Update Extension Manifest Permissions

1. **Edit manifest:**
   ```json
   // extension/manifest.json
   {
     "permissions": [
       "activeTab",
       "scripting",
       "storage",
       "nativeMessaging",
       "newPermission"  // Add new permission
     ]
   }
   ```

2. **Update documentation:**
   - `extension/SETUP.md` - Document why permission is needed
   - `extension/ARCHITECTURE.md` - Explain how it's used

3. **Test installation:**
   ```bash
   # Reload extension in chrome://extensions/
   # Check for permission warnings
   npm run test:install
   ```

### Task: Add New Test Coverage

1. **Identify gap in coverage:**
   ```bash
   npm run test:coverage  # JavaScript
   pytest --cov tests/    # Python
   ```

2. **Add test case:**
   ```javascript
   // tests/extraction.test.js

   test('should handle empty pages gracefully', async () => {
       const page = await browser.newPage();
       await page.goto('about:blank');
       const result = await page.evaluate(() => {
           return extractContent('three-phase');
       });
       expect(result).toBeDefined();
       expect(result.length).toBe(0);
   });
   ```

3. **Run and verify:**
   ```bash
   npm test
   ```

---

## Important Gotchas

### 1. Extension Reloading

**Issue:** Changes to extension files don't take effect until reload.

**Solution:** Always reload extension in `chrome://extensions/` after changes:
- Click reload icon on extension card
- Or use keyboard shortcut in extension (Ctrl+R)

### 2. Native Messaging Bridge Port Conflicts

**Issue:** Port 8765 already in use by another process.

**Solution:**
- Check for running instances: `lsof -i :8765` (Linux/macOS) or `netstat -ano | findstr 8765` (Windows)
- Kill conflicting process or change `BRIDGE_PORT` in both `chrome_tab_native_host.py` and `chrome_tab_mcp_server.py`

### 3. Token Authentication Failures

**Issue:** HTTP API returns 401 Unauthorized.

**Causes:**
- Token not in `tokens.json` file
- Wrong file location (check platform-specific paths)
- Server not restarted after token update
- Missing `Authorization: Bearer` header

**Solution:**
```bash
# Verify token file location
# Linux: ~/.config/chrome-tab-reader/tokens.json
# macOS: ~/Library/Application Support/chrome-tab-reader/tokens.json
# Windows: %APPDATA%\chrome-tab-reader\tokens.json

# Verify token format
cat ~/.config/chrome-tab-reader/tokens.json
# Should be: {"tokens": ["your-token-here"]}

# Restart server
uvicorn chrome_tab_http_server:app --reload
```

### 4. Three-Phase Extraction Timeouts

**Issue:** Extraction hangs for minutes on complex pages.

**Causes:**
- DOM never stabilizes (constant updates, live feeds)
- Lazy-loading never completes
- Readability.js crashes on malformed HTML

**Solution:**
- Phase 2 has hard timeout (30 seconds) - will exit eventually
- Fallback to `immediate` strategy for problematic sites
- Fallback to `document.body.innerText` if Readability fails

### 5. Testing Requires Chrome Installation

**Issue:** Tests fail with "Chrome not found" error.

**Solution:**
- Install Chrome/Chromium
- Set `CHROME_PATH` environment variable if non-standard location
- CI skips browser tests (only runs file structure validation)

### 6. Python PEP 723 Dependencies

**Issue:** Dependencies not installed correctly.

**Solution:**
- Use `uv run` (preferred): `uv run chrome_tab_http_server.py`
- Or install from `requirements.txt`: `uv pip install -r requirements.txt`
- PEP 723 metadata is in script comments (/// script ///), not pyproject.toml

### 7. Cross-Platform Path Differences

**Issue:** Hardcoded paths break on different OS.

**Solution:**
- Use `Path` from `pathlib` (Python)
- Use `platformdirs` for user config directories
- Check `platform.system()` for OS-specific logic

**Example:**
```python
import platform
from pathlib import Path

def get_config_dir() -> Path:
    system = platform.system()
    if system == "Darwin":  # macOS
        return Path.home() / "Library/Application Support/chrome-tab-reader"
    elif system == "Windows":
        return Path(os.getenv("APPDATA")) / "chrome-tab-reader"
    else:  # Linux
        config_home = os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")
        return Path(config_home) / "chrome-tab-reader"
```

### 8. Manifest V3 Restrictions

**Issue:** Manifest V3 has strict CSP and service worker limitations.

**Restrictions:**
- No remote code execution (all libraries must be local)
- Service workers can't use DOM APIs
- Content scripts can't use `chrome.runtime` APIs

**Solution:**
- Bundle all libraries in `extension/lib/`
- Use message passing between service worker and content scripts
- Check extension/ARCHITECTURE.md for detailed message flow

### 9. PowerShell Line Endings (CRITICAL)

**Issue:** PowerShell scripts fail with cryptic parser errors like "Try statement is missing its Catch or Finally block" or "Unexpected token '{' in expression or statement".

**Root Cause:**
PowerShell on Windows **requires CRLF (`\r\n`) line endings**. If PowerShell files have Unix LF (`\n`) line endings, the parser completely fails to parse the script structure, resulting in misleading error messages.

**How to Detect:**
```bash
# Check line endings
file run_tests.ps1

# Good output (Windows):
# run_tests.ps1: a pwsh script, Unicode text, UTF-8 text executable, with CRLF line terminators

# Bad output (Unix):
# run_tests.ps1: a pwsh script, Unicode text, UTF-8 text executable
# (notice missing "with CRLF line terminators")
```

**Solution:**

The repository uses **automated line ending enforcement**:

1. **`.gitattributes` (automatic)**: Ensures PowerShell files always checkout with CRLF
   ```gitattributes
   *.ps1 text eol=crlf
   *.psm1 text eol=crlf
   *.psd1 text eol=crlf
   ```

2. **Git hooks (optional but recommended)**: Pre-commit validation
   ```bash
   # Enable Git hooks
   git config core.hooksPath .githooks

   # The pre-commit hook will automatically check line endings
   # See .githooks/README.md for details
   ```

3. **Manual fix (if needed):**
   ```bash
   # Convert to CRLF
   sed -i 's/$/\r/' file.ps1

   # Or use dos2unix tools
   unix2dos file.ps1

   # Or let Git re-normalize
   git rm --cached file.ps1
   git add file.ps1
   ```

**Prevention:**
- Always enable Git hooks: `git config core.hooksPath .githooks`
- The `.gitattributes` file automatically handles line endings on checkout
- Never edit PowerShell files on Linux/macOS without ensuring CRLF preservation
- Use editors that respect `.gitattributes` (VS Code, Vim with proper config)

**Why This Is Critical:**
PowerShell parser errors from line ending issues are extremely hard to debug because:
- Error messages point to wrong lines (usually `} else {` blocks)
- Parser reports structural errors even though syntax is correct
- The issue only manifests on Windows, making it platform-specific
- Can block all PowerShell script execution in the repository

---

## Dependencies

### Node.js (package.json)

**Production:**
- `@mozilla/readability` (^0.6.0) - Content extraction
- `dompurify` (^3.3.0) - HTML sanitization

**Development:**
- `jest` (^30.2.0) - Test framework
- `puppeteer` (^24.30.0) - Browser automation for tests
- `@types/chrome` (^0.1.28) - TypeScript definitions
- `dotenv` (^16.0.0) - Environment variable loading

### Python (pyproject.toml / requirements.txt)

**MCP Server:**
- `fastmcp` (>=0.1.0) - FastMCP framework
- `requests` (>=2.31.0) - HTTP client
- `python-dotenv` - Environment variables

**HTTP Server:**
- `fastapi` (>=0.104.0) - Web framework
- `uvicorn[standard]` (>=0.24.0) - ASGI server
- `platformdirs` (>=4.0.0) - Platform-specific directories

**Testing:**
- `pytest` (>=7.4.0) - Test framework
- `pytest-cov` (>=4.1.0) - Coverage plugin
- `httpx` (>=0.25.0) - FastAPI test client
- `playwright` (>=1.40.0) - Browser automation

### JavaScript Libraries (extension/lib/)

**Bundled in extension:**
- `readability.min.js` - Mozilla Readability (~40KB)
- `dompurify.min.js` - DOMPurify sanitizer (~10KB)

**Why bundled?** Manifest V3 CSP prevents loading external scripts.

---

## Additional Resources

### Documentation Files

- **README.md** - Main project documentation, quick start guide
- **extension/ARCHITECTURE.md** - Detailed architecture and message flow
- **extension/SETUP.md** - Extension installation and configuration
- **extension/TESTING.md** - Extension testing procedures
- **NATIVE_MESSAGING_SETUP.md** - Native messaging bridge setup
- **ACCESS_CONTROL_SETUP.md** - Token authentication guide
- **tests/README.md** - Test suite documentation
- **tests/TESTING_QUICK_START.md** - Quick testing guide

### External Resources

- [Chrome Extension Manifest V3 Docs](https://developer.chrome.com/docs/extensions/mv3/)
- [Mozilla Readability.js](https://github.com/mozilla/readability)
- [DOMPurify](https://github.com/cure53/DOMPurify)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)

---

## Contributing

When making changes to this repository:

1. **Always run tests** before committing
2. **Update documentation** if behavior changes
3. **Follow code conventions** outlined in this guide
4. **Add tests** for new functionality
5. **Use descriptive commit messages** (focus on "why")
6. **Push to `claude/*` branches** for AI-assisted development
7. **Create PRs with test plans** using `gh pr create`

---

**Last Updated:** 2025-11-18
**Document Version:** 1.2
**Maintainer:** Russell Pierce (with AI assistance)
