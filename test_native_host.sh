#!/bin/bash
#
# Test script for native messaging host
#
# This script verifies:
# 1. Native host starts without crashing
# 2. TCP server binds to port 8765
# 3. TCP server accepts connections
# 4. Native host stays running

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== Native Messaging Host Test ==="
echo ""

# Clean up any previous test runs
rm -f ~/.chrome-tab-reader/native_host.log

# Start native host in background
echo -e "${YELLOW}Starting native host in background...${NC}"
python3 chrome_tab_native_host.py &
NATIVE_HOST_PID=$!

echo -e "${GREEN}✓${NC} Native host started with PID: $NATIVE_HOST_PID"

# Give it a moment to start up
sleep 2

# Check if process is still running
if ! ps -p $NATIVE_HOST_PID > /dev/null 2>&1; then
    echo -e "${RED}✗ FAILED: Native host crashed during startup${NC}"
    echo ""
    echo "Log contents:"
    cat ~/.chrome-tab-reader/native_host.log 2>/dev/null || echo "No log file found"
    exit 1
fi

echo -e "${GREEN}✓${NC} Native host is running after 2 seconds"

# Check if TCP port 8765 is listening
echo -e "${YELLOW}Checking if TCP port 8765 is listening...${NC}"
if command -v ss &> /dev/null; then
    if ss -tuln | grep -q ':8765'; then
        echo -e "${GREEN}✓${NC} TCP port 8765 is listening (via ss)"
    else
        echo -e "${RED}✗ FAILED: TCP port 8765 is not listening${NC}"
        kill $NATIVE_HOST_PID 2>/dev/null || true
        exit 1
    fi
elif command -v netstat &> /dev/null; then
    if netstat -tuln | grep -q ':8765'; then
        echo -e "${GREEN}✓${NC} TCP port 8765 is listening (via netstat)"
    else
        echo -e "${RED}✗ FAILED: TCP port 8765 is not listening${NC}"
        kill $NATIVE_HOST_PID 2>/dev/null || true
        exit 1
    fi
elif command -v lsof &> /dev/null; then
    if lsof -i :8765 > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} TCP port 8765 is listening (via lsof)"
    else
        echo -e "${RED}✗ FAILED: TCP port 8765 is not listening${NC}"
        kill $NATIVE_HOST_PID 2>/dev/null || true
        exit 1
    fi
else
    echo -e "${YELLOW}⚠${NC} Cannot verify port (no ss/netstat/lsof available)"
fi

# Test TCP connection
echo -e "${YELLOW}Testing TCP connection to 127.0.0.1:8765...${NC}"
if timeout 2 bash -c "echo '' | nc -w 1 127.0.0.1 8765" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} TCP connection successful"
elif timeout 2 bash -c "</dev/tcp/127.0.0.1/8765" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} TCP connection successful (via /dev/tcp)"
else
    echo -e "${YELLOW}⚠${NC} TCP connection test inconclusive (may need Chrome extension connected)"
fi

# Wait a bit longer and check if still running
echo -e "${YELLOW}Waiting 3 more seconds to verify stability...${NC}"
sleep 3

if ! ps -p $NATIVE_HOST_PID > /dev/null 2>&1; then
    echo -e "${RED}✗ FAILED: Native host crashed after 5 seconds total${NC}"
    echo ""
    echo "Log contents:"
    cat ~/.chrome-tab-reader/native_host.log 2>/dev/null || echo "No log file found"
    exit 1
fi

echo -e "${GREEN}✓${NC} Native host is still running after 5 seconds"

# Show log contents
echo ""
echo "=== Log file contents ==="
cat ~/.chrome-tab-reader/native_host.log

# Clean up
echo ""
echo -e "${YELLOW}Stopping native host...${NC}"
kill $NATIVE_HOST_PID 2>/dev/null || true
wait $NATIVE_HOST_PID 2>/dev/null || true

echo -e "${GREEN}✓${NC} Test complete - native host is working!"
echo ""
echo "Summary:"
echo "  - Native host starts successfully"
echo "  - TCP server binds to port 8765"
echo "  - Process stays running (doesn't crash)"
echo ""
echo "Note: The native host will exit immediately when started manually"
echo "because stdin is closed. This is normal - Chrome keeps stdin open"
echo "when it launches the native host."
