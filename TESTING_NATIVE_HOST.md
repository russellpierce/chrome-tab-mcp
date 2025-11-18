# Native Messaging Host Testing Guide

This guide explains how to test the native messaging host locally to ensure it's working correctly.

## Quick Verification

Run the quick TCP server verification:

```bash
python3 verify_tcp_server.py
```

This verifies:
- ✓ Native host starts without crashing
- ✓ TCP server binds to port 8765
- ✓ Port is accessible from localhost

**Expected output:**
```
✓ TCP server is listening on 127.0.0.1:8765
SUCCESS! The native host is working correctly
```

## Full Protocol Test

Run the full native messaging protocol simulation:

```bash
python3 test_native_messaging_simulation.py
```

This tests:
- ✓ Native host startup with stdin/stdout pipes
- ✓ TCP server accepts connections
- ✓ Message forwarding between extension and MCP server
- ✓ Process stability over time

## Manual Testing with Chrome

### 1. Check if Native Host is Running

When Chrome launches the native host, check the logs:

```bash
# Watch logs in real-time
tail -f ~/.chrome-tab-reader/native_host.log

# Or view the log file
cat ~/.chrome-tab-reader/native_host.log
```

**What to look for:**
```
[INFO] === Native Messaging Host Starting ===
[INFO] ✓ TCP server listening on 127.0.0.1:8765
[INFO] ✓ Extension message loop started
```

### 2. Verify TCP Server is Listening

While Chrome is running with the extension loaded:

```bash
# Linux (requires net-tools)
netstat -tuln | grep 8765

# Linux/macOS (requires lsof)
lsof -i :8765

# Linux (requires iproute2)
ss -tuln | grep 8765
```

**Expected output:**
```
tcp    0    0 127.0.0.1:8765    0.0.0.0:*    LISTEN
```

### 3. Test MCP Server Connection

Try connecting the MCP server while Chrome is running:

```bash
# Set required environment variables
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="llama2"

# Start MCP server (it should connect to the native host)
uv run chrome_tab_mcp_server.py --ollama-url $OLLAMA_BASE_URL --model $OLLAMA_MODEL
```

**In the native host log, you should see:**
```
[INFO] ✓ MCP client connected from ('127.0.0.1', XXXXX)
[INFO] Received from MCP: extract_current_tab
```

## Common Issues

### Empty Log File

**Problem:** Log file exists but is empty
**Cause:** Native host crashed during startup before logging initialized
**Solution:** Check stderr output (captured by Chrome):
- Open `chrome://extensions/`
- Click "Errors" button on the extension
- Look for native messaging errors

### TCP Port Already in Use

**Problem:** `Address already in use` error
**Cause:** Another instance of the native host is already running
**Expected:** The second instance will gracefully exit - this is normal!
**Solution:** This is actually correct behavior. Chrome may launch multiple instances, but only the first one binds to the TCP port.

### Extension Connects and Disconnects Immediately

**Problem:** Extension repeatedly connects/disconnects
**Cause:** Chrome service workers suspend after inactivity
**Expected:** This is normal Chrome behavior
**Solution:**
- Click the extension icon to wake it up
- Open the extension popup to keep it active

## Debugging Tips

### Enable Debug Logging

The native host already logs extensively to both file and stderr. Check both:

```bash
# File logs
tail -f ~/.chrome-tab-reader/native_host.log

# Chrome also captures stderr - check chrome://extensions/ → Errors
```

### Manually Run Native Host

You can manually run the native host to test it:

```bash
python3 chrome_tab_native_host.py
```

**Note:** It will exit immediately because stdin is closed. This is normal - Chrome keeps stdin open when it launches the native host.

### Test TCP Connection

Manually test the TCP connection:

```bash
# Using netcat
echo '{"action":"health_check"}' | nc 127.0.0.1 8765

# Using telnet
telnet 127.0.0.1 8765
# Then type: {"action":"health_check"}
```

## Test Scripts

| Script | Purpose | Duration |
|--------|---------|----------|
| `verify_tcp_server.py` | Quick TCP server check | 5 seconds |
| `test_native_messaging_simulation.py` | Full protocol test | 10 seconds |
| `test_native_host.sh` | Bash-based verification | 8 seconds |

## Expected Behavior

### Normal Startup Sequence

1. Native host starts
2. TCP server binds to 127.0.0.1:8765
3. Extension message loop starts, waits for messages
4. When MCP server connects, TCP thread handles it
5. Messages flow: MCP → Native Host → Extension → Native Host → MCP

### Normal Shutdown

- When Chrome closes the extension, stdin/stdout close
- Native host detects disconnection
- Extension message loop exits
- Process terminates cleanly

### Multiple Instances

- Chrome may launch multiple native host instances
- First instance binds to TCP port 8765
- Subsequent instances detect "address already in use" and skip TCP server
- All instances can still forward messages via native messaging
- This is normal and expected behavior

## Architecture Diagram

```
MCP Server (chrome_tab_mcp_server.py)
    ↓ TCP connection to localhost:8765
Native Host (chrome_tab_native_host.py)
    ├─ TCP Server Thread (port 8765)
    └─ Extension Message Loop (stdin/stdout)
         ↓ Native Messaging Protocol
Chrome Extension (service_worker.js)
    ↓ Content Script Injection
Web Page Content
```

## Success Criteria

The native host is working correctly if:

- ✓ Log file shows successful startup
- ✓ TCP server binds to port 8765
- ✓ Process doesn't crash within 5 seconds
- ✓ Extension can connect via native messaging
- ✓ MCP server can connect via TCP

## Further Reading

- [Chrome Native Messaging Documentation](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging)
- [Native Messaging Setup Guide](NATIVE_MESSAGING_SETUP.md)
- [MCP Server README](README_MCP.md)
