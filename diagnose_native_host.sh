#!/bin/bash
#
# Chrome Tab Reader - Native Host Diagnostic Tool
#
# This script helps diagnose why Chrome isn't starting the native messaging host.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Chrome Tab Reader - Native Host Diagnostics ===${NC}"
echo ""

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
NATIVE_HOST_SCRIPT="$SCRIPT_DIR/chrome_tab_native_host.py"

# Detect platform and set paths
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
    MANIFEST_DIR="$HOME/.config/google-chrome/NativeMessagingHosts"
    CHROME_LOG_DIR="$HOME/.config/google-chrome"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
    MANIFEST_DIR="$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
    CHROME_LOG_DIR="$HOME/Library/Application Support/Google/Chrome"
else
    echo -e "${RED}Unsupported platform: $OSTYPE${NC}"
    exit 1
fi

MANIFEST_FILE="$MANIFEST_DIR/com.chrome_tab_reader.host.json"
LOG_FILE="$HOME/.chrome-tab-reader/native_host.log"

echo -e "${BLUE}Platform:${NC} $PLATFORM"
echo -e "${BLUE}Expected manifest:${NC} $MANIFEST_FILE"
echo -e "${BLUE}Expected log file:${NC} $LOG_FILE"
echo ""

# Check 1: Manifest file exists
echo -e "${BLUE}[1] Checking manifest file...${NC}"
if [ -f "$MANIFEST_FILE" ]; then
    echo -e "${GREEN}✓${NC} Manifest file exists"
    echo "   Location: $MANIFEST_FILE"

    # Check if manifest is valid JSON
    if python3 -m json.tool "$MANIFEST_FILE" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Manifest is valid JSON"

        # Display manifest contents
        echo ""
        echo "   Manifest contents:"
        cat "$MANIFEST_FILE" | sed 's/^/   /'
        echo ""

        # Extract extension ID
        ALLOWED_ORIGIN=$(python3 -c "import json; print(json.load(open('$MANIFEST_FILE'))['allowed_origins'][0])" 2>/dev/null || echo "")
        if [ -n "$ALLOWED_ORIGIN" ]; then
            EXTENSION_ID=$(echo "$ALLOWED_ORIGIN" | sed -n 's|chrome-extension://\([^/]*\)/|\1|p')
            echo -e "${BLUE}   Extension ID:${NC} $EXTENSION_ID"
        fi
    else
        echo -e "${RED}✗${NC} Manifest is NOT valid JSON!"
        exit 1
    fi
else
    echo -e "${RED}✗${NC} Manifest file does NOT exist!"
    echo "   Expected location: $MANIFEST_FILE"
    echo ""
    echo "   Run: ./install_native_host.sh <extension-id>"
    exit 1
fi
echo ""

# Check 2: Native host script exists and is executable
echo -e "${BLUE}[2] Checking native host script...${NC}"
if [ -f "$NATIVE_HOST_SCRIPT" ]; then
    echo -e "${GREEN}✓${NC} Native host script exists"
    echo "   Location: $NATIVE_HOST_SCRIPT"

    if [ -x "$NATIVE_HOST_SCRIPT" ]; then
        echo -e "${GREEN}✓${NC} Script is executable"
    else
        echo -e "${RED}✗${NC} Script is NOT executable!"
        echo "   Fix with: chmod +x $NATIVE_HOST_SCRIPT"
        exit 1
    fi
else
    echo -e "${RED}✗${NC} Native host script does NOT exist!"
    echo "   Expected location: $NATIVE_HOST_SCRIPT"
    exit 1
fi
echo ""

# Check 3: Python availability
echo -e "${BLUE}[3] Checking Python...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo -e "${GREEN}✓${NC} Python found: $PYTHON_VERSION"
    echo "   Path: $(which python3)"
else
    echo -e "${RED}✗${NC} Python3 not found!"
    exit 1
fi
echo ""

# Check 4: Test native host manually
echo -e "${BLUE}[4] Testing native host manually...${NC}"
echo "   This will send a test message to the native host"
echo "   Expected: The host should start, create a log file, and respond"
echo ""

# Create a simple test message (health check)
TEST_MESSAGE='{"action":"health_check","request_id":999}'
MESSAGE_LENGTH=${#TEST_MESSAGE}

# Create binary message with length prefix (little-endian)
printf "   Sending test message: %s\n" "$TEST_MESSAGE"
echo ""

# Run the native host with a test message
TEMP_LOG=$(mktemp)
(
    # Send message: 4-byte length + JSON message
    python3 -c "
import sys
import struct
message = '$TEST_MESSAGE'
encoded = message.encode('utf-8')
length = len(encoded)
sys.stdout.buffer.write(struct.pack('=I', length))
sys.stdout.buffer.write(encoded)
sys.stdout.buffer.flush()
" | python3 "$NATIVE_HOST_SCRIPT" 2>"$TEMP_LOG"
) &
NATIVE_HOST_PID=$!

# Wait a moment for the host to start
sleep 2

# Check if log file was created
if [ -f "$LOG_FILE" ]; then
    echo -e "${GREEN}✓${NC} Native host created log file!"
    echo "   Location: $LOG_FILE"
    echo ""
    echo "   Recent log entries:"
    tail -n 20 "$LOG_FILE" | sed 's/^/   /'
else
    echo -e "${RED}✗${NC} Native host did NOT create log file!"
    echo ""
    echo "   This means the host failed to start or crashed immediately."
    echo "   Check stderr output below for clues:"
    echo ""
    cat "$TEMP_LOG" | sed 's/^/   /'
fi

echo ""
echo "   Stderr output from native host:"
cat "$TEMP_LOG" | sed 's/^/   /'

# Cleanup
kill $NATIVE_HOST_PID 2>/dev/null || true
rm -f "$TEMP_LOG"
echo ""

# Check 5: Chrome extension status
echo -e "${BLUE}[5] Checking Chrome extension...${NC}"
echo "   Manual steps required:"
echo ""
echo "   1. Open Chrome: chrome://extensions/"
echo "   2. Find 'Chrome Tab Reader' extension"
echo "   3. Verify the extension ID matches the manifest:"
if [ -n "$EXTENSION_ID" ]; then
    echo "      Expected ID: $EXTENSION_ID"
fi
echo "   4. Check for errors in the extension (click 'Errors' button)"
echo ""

# Check 6: Chrome native messaging logs
echo -e "${BLUE}[6] Chrome native messaging logs...${NC}"
echo "   Chrome logs native messaging errors to stderr"
echo ""
echo "   To see Chrome's native messaging logs:"
echo "   1. Close all Chrome windows"
echo "   2. Start Chrome from terminal:"
if [ "$PLATFORM" == "linux" ]; then
    echo "      google-chrome --enable-logging=stderr --v=1 2>&1 | tee chrome.log"
elif [ "$PLATFORM" == "macos" ]; then
    echo "      /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --enable-logging=stderr --v=1 2>&1 | tee chrome.log"
fi
echo "   3. Open the extension popup or reload the extension"
echo "   4. Look for native messaging errors in the output"
echo ""

# Check 7: Service worker console
echo -e "${BLUE}[7] Extension service worker console...${NC}"
echo "   The service worker logs connection attempts"
echo ""
echo "   To check service worker logs:"
echo "   1. Go to: chrome://extensions/"
echo "   2. Find 'Chrome Tab Reader'"
echo "   3. Click 'service worker' link (it will say 'Inspect views: service worker')"
echo "   4. Look for messages like:"
echo "      '[Chrome Tab Reader] Connecting to native messaging host...'"
echo "      '[Chrome Tab Reader] Connected to native messaging host'"
echo "      OR errors like:"
echo "      '[Chrome Tab Reader] Failed to connect to native host: ...'"
echo ""

# Summary
echo -e "${BLUE}=== Summary ===${NC}"
echo ""
echo "If the native host manual test above failed:"
echo "  - Check the stderr output for Python import errors"
echo "  - Verify the script's shebang line points to correct Python"
echo "  - Check file permissions on the script"
echo ""
echo "If the manual test succeeded but Chrome still doesn't start the host:"
echo "  - Verify the extension ID in the manifest matches your extension"
echo "  - Check Chrome's service worker console for connection errors"
echo "  - Try starting Chrome with verbose logging (see step 6 above)"
echo "  - Check if Chrome has permission to execute the script"
echo ""
echo "Common issues:"
echo "  1. Extension ID mismatch (reinstall: ./install_native_host.sh <correct-id>)"
echo "  2. Python path issues (check shebang: head -1 $NATIVE_HOST_SCRIPT)"
echo "  3. Missing Python dependencies (try: uv pip install -r requirements.txt)"
echo "  4. Chrome can't find/execute script (check path in manifest is absolute)"
echo ""
