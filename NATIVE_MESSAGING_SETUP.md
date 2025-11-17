# Native Messaging Setup Guide

This guide explains how to set up Native Messaging to connect the MCP server directly to the Chrome extension.

## Architecture

```
Claude Code (via MCP protocol)
    ↓
MCP Server (chrome_tab_mcp_server.py)
    ↓ (TCP localhost:8765)
Native Messaging Host (chrome_tab_native_host.py)
    ↓ (Chrome Native Messaging protocol - stdin/stdout)
Chrome Extension
    ↓ (content extraction)
Web Page Content
```

## Benefits

- **Cross-platform**: Works on Windows, macOS, and Linux
- **Direct communication**: No HTTP server needed
- **Secure**: Chrome manages the connection
- **Superior extraction**: Uses extension's three-phase extraction (lazy-loading, DOM stability, Readability.js)

## Prerequisites

1. Chrome browser with the Chrome Tab Reader extension installed
2. Python 3.8 or later
3. The extension's ID from chrome://extensions/

## Installation Steps

### 1. Install the Chrome Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" in the top right
3. Click "Load unpacked" and select the `extension/` directory
4. Note the Extension ID (you'll need this for step 2)

### 2. Install the Native Messaging Host

Run the installation script with your extension ID:

```bash
./install_native_host.sh <your-extension-id>
```

**Example:**
```bash
./install_native_host.sh abcdefghijklmnopqrstuvwxyz123456
```

This script will:
- Make the native host script executable
- Create the platform-specific manifest directory
- Install the native messaging host manifest with correct paths

### 3. Verify Installation

#### Check Extension Connection

1. Reload the extension in Chrome (`chrome://extensions/` → click reload icon)
2. Open the extension popup (click the extension icon)
3. Open Chrome DevTools Console (F12)
4. Look for: `[Chrome Tab Reader] Connected to native messaging host`

#### Check Native Host Logs

The native host logs all activity:

```bash
tail -f ~/.chrome-tab-reader/native_host.log
```

You should see messages like:
```
[2025-11-17 ...] INFO: === Native Messaging Host Starting ===
[2025-11-17 ...] INFO: Extension message loop started
```

#### Test the Connection

Try extracting content from a web page using the MCP server:

```python
# In your Claude Code session
process_chrome_tab()
```

## Platform-Specific Details

### Linux

- Manifest directory: `~/.config/google-chrome/NativeMessagingHosts/`
- TCP: `127.0.0.1:8765`
- Log file: `~/.chrome-tab-reader/native_host.log`

### macOS

- Manifest directory: `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/`
- TCP: `127.0.0.1:8765`
- Log file: `~/.chrome-tab-reader/native_host.log`

### Windows

- Manifest directory: `%APPDATA%\Google\Chrome\NativeMessagingHosts\`
- TCP: `127.0.0.1:8765`
- Log file: `%USERPROFILE%\.chrome-tab-reader\native_host.log`

## Troubleshooting

### Extension Can't Connect to Native Host

**Symptom:** Extension console shows connection errors

**Solutions:**
1. Verify the manifest is installed:
   ```bash
   # Linux/Mac
   cat ~/.config/google-chrome/NativeMessagingHosts/com.chrome_tab_reader.host.json

   # Check that "path" points to chrome_tab_native_host.py
   # Check that "allowed_origins" contains your extension ID
   ```

2. Verify the native host script is executable:
   ```bash
   ls -l chrome_tab_native_host.py
   # Should show: -rwxr-xr-x
   ```

3. Test the native host manually:
   ```bash
   # This should start the host (it won't output anything)
   ./chrome_tab_native_host.py
   ```

4. Reload the extension and retry

### MCP Server Can't Connect to Native Host

**Symptom:** `Native messaging bridge is not running` error

**Solutions:**
1. Ensure Chrome is running with the extension loaded
2. The native host only starts when the extension connects
3. Open the extension popup to trigger the connection
4. Check that the TCP server is listening:
   ```bash
   # Linux/Mac
   netstat -an | grep 8765
   # Or
   lsof -i :8765

   # Windows
   netstat -an | findstr 8765
   ```

### Permission Denied Errors

**Symptom:** Permission errors when running scripts

**Solutions:**
1. Make scripts executable:
   ```bash
   chmod +x chrome_tab_native_host.py
   chmod +x install_native_host.sh
   ```

2. Check file ownership:
   ```bash
   ls -la chrome_tab_native_host.py
   # Should be owned by your user
   ```

### Extension ID Changed

**Symptom:** Native host connection fails after reinstalling extension

**Solution:**
1. Get the new extension ID from chrome://extensions/
2. Re-run the installation script with the new ID:
   ```bash
   ./install_native_host.sh <new-extension-id>
   ```

## How It Works

### Native Messaging Protocol

Chrome Native Messaging uses a simple binary protocol over stdin/stdout:

1. **Message Format:**
   - 4 bytes: Message length (little-endian unsigned int)
   - N bytes: JSON message content

2. **Bidirectional Communication:**
   - Extension sends messages to native host via `chrome.runtime.connectNative()`
   - Native host reads from stdin, writes to stdout
   - Messages are JSON-encoded

### Bridge Architecture

The native host acts as a bridge:

1. **Extension → Native Host:** Chrome Native Messaging (stdin/stdout)
2. **Native Host → MCP Server:** TCP localhost:8765 (JSON over newline-delimited protocol)
3. **MCP Server:** Sends requests to native host, receives responses

### Message Flow Example

```
1. MCP server connects to TCP localhost:8765
2. MCP server sends: {"action": "extract_current_tab", "strategy": "three-phase"}
3. Native host forwards to extension via stdout
4. Extension extracts content using three-phase strategy
5. Extension sends response via stdin
6. Native host receives response
7. Native host forwards to MCP server via TCP
8. MCP server processes content with Ollama
```

## Comparison with AppleScript Approach

| Feature | Native Messaging | AppleScript (old) |
|---------|------------------|-------------------|
| Platform support | ✅ Windows, macOS, Linux | ❌ macOS only |
| Extraction quality | ✅ Three-phase (advanced) | ⚠️  Basic text extraction |
| Setup complexity | Medium (one-time) | Low |
| Dependencies | Chrome extension | AppleScript |
| Performance | Fast | Fast |
| Reliability | High | Medium (UI dependent) |

## Advanced Configuration

### Custom TCP Port

You can change the TCP port by editing both files:

1. **Native host** (`chrome_tab_native_host.py`):
   ```python
   TCP_HOST = "127.0.0.1"
   TCP_PORT = 9000  # Your custom port
   ```

2. **MCP server** (`chrome_tab_mcp_server.py`):
   ```python
   BRIDGE_HOST = "127.0.0.1"
   BRIDGE_PORT = 9000  # Your custom port
   ```

**Note:** Make sure the port is not already in use and is allowed through your firewall.

### Multiple Extension Instances

To run multiple extension instances (e.g., Chrome Canary), create separate manifests:

```bash
./install_native_host.sh <chrome-canary-extension-id>
```

The manifest file should be unique per browser but can use the same native host script.

## Uninstallation

To remove the native messaging host:

```bash
# Remove manifest
rm ~/.config/google-chrome/NativeMessagingHosts/com.chrome_tab_reader.host.json

# Remove logs (optional)
rm -rf ~/.chrome-tab-reader/
```

## References

- [Chrome Native Messaging Documentation](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging)
- [Native Messaging Protocol Specification](https://developer.chrome.com/docs/apps/nativeMessaging/)
