# Testing Native Messaging Integration

> **Note:** This document is AI-authored with very limited human oversight.

This directory contains tests for the Native Messaging integration between the MCP server and Chrome extension.

## Test Levels

### 1. Unit Tests (`test_native_messaging.py`)
Tests individual components in isolation:
- Native Messaging protocol encoding/decoding
- Message serialization (4-byte length prefix + JSON)
- Socket communication primitives
- MCP server extraction function

**Run:**
```bash
pytest tests/test_native_messaging.py -v
```

**Requirements:**
- pytest
- No Chrome or extension needed

### 2. Integration Tests (`test_native_messaging.py` - marked `@pytest.mark.integration`)
Tests interaction between components:
- Unix socket server/client communication
- Request/response matching with IDs
- Timeout handling
- Error propagation

**Run:**
```bash
pytest tests/test_native_messaging.py -v -m integration
```

**Requirements:**
- pytest
- Native messaging host (can be mocked)

### 3. End-to-End Tests (`test_e2e_native_messaging.py`)
Tests complete flow with real Chrome:
- Extension loading in Chrome
- Native host connection
- Full extraction pipeline
- MCP → Native Host → Extension → Content

**Run:**
```bash
pytest tests/test_e2e_native_messaging.py -v -m e2e
```

**Requirements:**
- Chrome browser
- Extension loaded
- Native messaging host installed
- Playwright

### 4. Manual Tests (`manual_test_native_messaging.py`)
Interactive testing without pytest:
- Protocol verification
- Socket communication
- Extension connectivity
- Visual feedback

**Run:**
```bash
# Run all tests
python tests/manual_test_native_messaging.py all

# Run specific test
python tests/manual_test_native_messaging.py protocol
python tests/manual_test_native_messaging.py socket
python tests/manual_test_native_messaging.py extension
python tests/manual_test_native_messaging.py mcp
```

**Requirements:**
- Chrome with extension (for extension/mcp tests)
- Native host installed (for extension/mcp tests)

## Setup

### Install Test Dependencies

```bash
# Using uv (recommended - faster and more reliable)
uv pip install -r tests/requirements-test.txt

# Or using pip
pip install -r tests/requirements-test.txt

# Install Playwright browsers
playwright install chrome
```

### Install Extension and Native Host

1. **Load Extension:**
   ```bash
   # Open Chrome
   # Go to chrome://extensions/
   # Enable Developer mode
   # Click "Load unpacked"
   # Select the extension/ directory
   # Note the Extension ID
   ```

2. **Install Native Host:**
   ```bash
   ./install_native_host.sh <your-extension-id>
   ```

3. **Verify Setup:**
   ```bash
   # Check extension logs
   # Open Chrome DevTools console (F12)
   # Should see: [Chrome Tab Reader] Connected to native messaging host

   # Check native host logs
   tail -f ~/.chrome-tab-reader/native_host.log
   # Should see: Extension message loop started
   ```

## Running Tests

### Quick Test (Manual)
```bash
# Make sure Chrome is running with extension loaded and a page open
python tests/manual_test_native_messaging.py extension
```

Expected output:
```
=== Testing MCP → Extension Communication ===

Test 1: Check if native messaging socket exists
  ✓ Socket exists: /home/user/.chrome-tab-reader/mcp_bridge.sock

Test 2: Connect to native messaging bridge
  ✓ Connected to native host

Test 3: Send extraction request
  Request sent: {'action': 'extract_current_tab', 'strategy': 'three-phase'}

Test 4: Receive extraction response
  Response status: success
  Content preview: This domain is for use in illustrative examples...
  Title: Example Domain
  URL: https://example.com/
  Extraction time: 1234ms
  ✓ Extension communication works!
```

### Unit Tests
```bash
pytest tests/test_native_messaging.py -v
```

Expected output:
```
tests/test_native_messaging.py::TestNativeMessagingProtocol::test_message_encoding PASSED
tests/test_native_messaging.py::TestNativeMessagingProtocol::test_message_decoding PASSED
tests/test_native_messaging.py::TestNativeMessagingProtocol::test_empty_message_handling PASSED
tests/test_native_messaging.py::TestSocketCommunication::test_socket_request_response PASSED
tests/test_native_messaging.py::TestSocketCommunication::test_socket_timeout_handling PASSED
```

### Integration Tests
```bash
pytest tests/test_native_messaging.py -v -m integration
```

### E2E Tests (with Chrome)
```bash
# Ensure Chrome is not running
pytest tests/test_e2e_native_messaging.py -v -m e2e -s

# The -s flag shows print output (useful for debugging)
```

### All Tests
```bash
pytest tests/ -v --cov=. --cov-report=html
```

## Troubleshooting Tests

### "Socket not found" error
**Problem:** Native messaging socket doesn't exist

**Solution:**
1. Load extension in Chrome
2. Open extension popup (click icon)
3. Check native host log: `tail -f ~/.chrome-tab-reader/native_host.log`
4. Should see "Extension message loop started"

### "Connection refused" error
**Problem:** Native host is not responding

**Solution:**
1. Reload extension in Chrome
2. Check native host manifest is installed:
   ```bash
   cat ~/.config/google-chrome/NativeMessagingHosts/com.chrome_tab_reader.host.json
   ```
3. Verify path in manifest points to `chrome_tab_native_host.py`
4. Verify extension ID in manifest matches your extension

### "No response from extension" error
**Problem:** Extension is not processing requests

**Solution:**
1. Open Chrome DevTools console (F12) on any page
2. Check for extension errors
3. Look for: "[Chrome Tab Reader] Received native message: ..."
4. Ensure content script is loaded (check console)

### Playwright errors
**Problem:** Browser automation fails

**Solution:**
1. Install Playwright browsers:
   ```bash
   playwright install chrome
   ```
2. Update Playwright:
   ```bash
   pip install --upgrade playwright
   ```
3. Check Chrome version compatibility

### Tests hang
**Problem:** Test waits forever

**Solution:**
1. Check if Chrome has an active tab open
2. Navigate to any webpage (e.g., https://example.com)
3. Ensure extension has permissions for the page
4. Check timeout settings in tests

## Test Coverage

Current test coverage:

- ✅ Native Messaging protocol (encoding/decoding)
- ✅ Socket communication (client/server)
- ✅ Request/response matching
- ✅ Timeout handling
- ✅ Extension connection
- ✅ Content extraction
- ✅ Error propagation
- ✅ MCP server integration

## Writing New Tests

### Unit Test Example
```python
def test_my_feature():
    """Test description"""
    # Arrange
    input_data = {"test": "data"}

    # Act
    result = my_function(input_data)

    # Assert
    assert result["status"] == "success"
```

### Integration Test Example
```python
@pytest.mark.integration
def test_socket_integration():
    """Test socket communication"""
    # Start mock server
    # Connect client
    # Send request
    # Verify response
    pass
```

### E2E Test Example
```python
@pytest.mark.e2e
def test_full_flow(extension_path):
    """Test complete extraction flow"""
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="",
            headless=False,
            args=[
                f"--disable-extensions-except={extension_path}",
                f"--load-extension={extension_path}",
            ]
        )

        # Test actions

        browser.close()
```

## Continuous Integration

These tests can be run in CI with headless Chrome:

```yaml
# .github/workflows/test-native-messaging.yml
name: Test Native Messaging

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r tests/requirements-test.txt
      - run: playwright install chrome
      - run: pytest tests/test_native_messaging.py -v
      # E2E tests require special setup in CI
```

## Performance Benchmarks

Expected performance metrics:

- **Protocol encoding/decoding:** < 1ms
- **Socket connection:** < 100ms
- **Content extraction:** 1-5 seconds (depends on page complexity)
- **Full MCP → Extension → Response:** < 10 seconds

## Security Considerations

When testing:
- Native host logs may contain page content
- Socket files have user-only permissions
- Extension ID should not be hardcoded in tests
- Use temporary directories for test artifacts

## References

- [Chrome Native Messaging Docs](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging)
- [Playwright Python Docs](https://playwright.dev/python/)
- [pytest Documentation](https://docs.pytest.org/)
