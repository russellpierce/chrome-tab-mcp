#!/bin/bash
#
# Chrome Tab Reader - Native Messaging Host Installer
#
# This script installs the native messaging host manifest so Chrome can
# communicate with the browser extension via Native Messaging.
#
# Usage: ./install_native_host.sh [extension-id]
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
NATIVE_HOST_SCRIPT="$SCRIPT_DIR/chrome_tab_native_host.py"
MANIFEST_TEMPLATE="$SCRIPT_DIR/com.chrome_tab_reader.host.json"

# Check if extension ID provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Extension ID required${NC}"
    echo ""
    echo "Usage: $0 <extension-id>"
    echo ""
    echo "To find your extension ID:"
    echo "1. Open Chrome and go to chrome://extensions/"
    echo "2. Enable 'Developer mode' in the top right"
    echo "3. Find 'Chrome Tab Reader' and copy the ID"
    echo ""
    exit 1
fi

EXTENSION_ID="$1"

echo -e "${GREEN}Chrome Tab Reader - Native Messaging Host Installer${NC}"
echo ""

# Detect platform
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
    MANIFEST_DIR="$HOME/.config/google-chrome/NativeMessagingHosts"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
    MANIFEST_DIR="$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    PLATFORM="windows"
    MANIFEST_DIR="$APPDATA/Google/Chrome/NativeMessagingHosts"
else
    echo -e "${RED}Unsupported platform: $OSTYPE${NC}"
    exit 1
fi

echo "Detected platform: $PLATFORM"
echo "Manifest directory: $MANIFEST_DIR"
echo ""

# Check Python installation and version
echo "Checking Python installation..."
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}Error: Python not found${NC}"
    echo ""
    echo "Python 3.8 or higher is required."
    echo "Please install Python from https://www.python.org/downloads/"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oP '\d+\.\d+')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo -e "${RED}Error: Python 3.8 or higher required${NC}"
    echo "Found: Python $PYTHON_VERSION"
    echo ""
    echo "Please upgrade Python from https://www.python.org/downloads/"
    exit 1
fi

echo -e "${GREEN}✓${NC} Found Python $PYTHON_VERSION"
echo ""

# Check if native host script exists
if [ ! -f "$NATIVE_HOST_SCRIPT" ]; then
    echo -e "${RED}Error: Native host script not found at $NATIVE_HOST_SCRIPT${NC}"
    exit 1
fi

# Make native host script executable
chmod +x "$NATIVE_HOST_SCRIPT"
echo -e "${GREEN}✓${NC} Made native host script executable"

# Create manifest directory if it doesn't exist
mkdir -p "$MANIFEST_DIR"
echo -e "${GREEN}✓${NC} Created manifest directory"

# Create manifest file with correct paths
MANIFEST_FILE="$MANIFEST_DIR/com.chrome_tab_reader.host.json"
cat > "$MANIFEST_FILE" << EOF
{
  "name": "com.chrome_tab_reader.host",
  "description": "Chrome Tab Reader Native Messaging Host",
  "path": "$NATIVE_HOST_SCRIPT",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://$EXTENSION_ID/"
  ]
}
EOF

echo -e "${GREEN}✓${NC} Created native messaging host manifest"
echo "   Location: $MANIFEST_FILE"
echo ""

echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Reload the Chrome extension (chrome://extensions/)"
echo "2. Open the extension popup - it should connect to the native host"
echo "3. Check the native host log for connection status:"
echo "   tail -f ~/.chrome-tab-reader/native_host.log"
echo ""
echo "To test the setup, try using the MCP server to extract a Chrome tab."
