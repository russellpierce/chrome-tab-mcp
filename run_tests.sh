#!/bin/bash
#
# Test Runner for Chrome Tab Reader
#
# Usage:
#   ./run_tests.sh              # Run all tests
#   ./run_tests.sh unit         # Run unit tests only
#   ./run_tests.sh integration  # Run integration tests
#   ./run_tests.sh e2e          # Run end-to-end tests
#   ./run_tests.sh manual       # Run manual interactive test
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Print header
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Chrome Tab Reader - Test Suite${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Determine test type
TEST_TYPE="${1:-all}"

# Ensure dependencies are installed (skip for clean/help commands)
if [[ "$TEST_TYPE" != "clean" && "$TEST_TYPE" != "help" && "$TEST_TYPE" != "--help" && "$TEST_TYPE" != "-h" ]]; then
    echo -e "${YELLOW}Checking dependencies...${NC}"
    if ! uv sync --extra test --quiet 2>&1 | grep -q "error"; then
        echo -e "${GREEN}✓ Dependencies synced${NC}"
        echo ""
    else
        echo -e "${RED}✗ Failed to sync dependencies${NC}"
        echo "Run: uv sync --extra test"
        exit 1
    fi
fi

case "$TEST_TYPE" in
    unit)
        echo -e "${GREEN}Running unit tests...${NC}"
        echo ""
        echo -e "${BLUE}→ Native Messaging Protocol Tests${NC}"
        uv run pytest tests/test_native_messaging.py -v -m "not integration and not e2e"
        echo ""
        echo -e "${BLUE}→ HTTP Server Tests${NC}"
        uv run pytest tests/test_http_server.py -v
        echo ""
        echo -e "${BLUE}→ FastAPI Schema Validation${NC}"
        uv run python test_fastapi_server.py
        ;;

    integration)
        echo -e "${GREEN}Running integration tests...${NC}"
        echo -e "${YELLOW}Note: These tests require the native host to be running${NC}"
        uv run pytest tests/test_native_messaging.py -v -m integration
        ;;

    e2e)
        echo -e "${GREEN}Running end-to-end tests...${NC}"
        echo -e "${YELLOW}Note: These tests require Chrome with extension loaded${NC}"
        echo ""
        echo "Prerequisites:"
        echo "  1. Extension loaded in Chrome (chrome://extensions/)"
        echo "  2. Native messaging host installed"
        echo "  3. Playwright installed (uv pip install playwright && uv run playwright install chrome)"
        echo ""
        read -p "Continue? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            uv run pytest tests/test_e2e_native_messaging.py -v -m e2e -s
        else
            echo "Cancelled"
            exit 0
        fi
        ;;

    manual)
        echo -e "${GREEN}Running manual interactive tests...${NC}"
        echo -e "${YELLOW}This will test the actual connection to Chrome${NC}"
        echo ""
        uv run python tests/manual_test_native_messaging.py all
        ;;

    coverage)
        echo -e "${GREEN}Running tests with coverage...${NC}"
        uv run pytest tests/ -v --cov=. --cov-report=html --cov-report=term
        echo ""
        echo -e "${GREEN}Coverage report generated: htmlcov/index.html${NC}"
        ;;

    all)
        echo -e "${GREEN}Running all tests...${NC}"
        echo ""

        echo -e "${BLUE}1. FastAPI Schema Validation${NC}"
        uv run python test_fastapi_server.py || true
        echo ""

        echo -e "${BLUE}2. Unit Tests - Native Messaging${NC}"
        uv run pytest tests/test_native_messaging.py -v -m "not integration and not e2e" || true
        echo ""

        echo -e "${BLUE}3. Unit Tests - HTTP Server${NC}"
        uv run pytest tests/test_http_server.py -v || true
        echo ""

        echo -e "${BLUE}4. Manual Test (Quick Check)${NC}"
        uv run python tests/manual_test_native_messaging.py protocol || true
        echo ""

        echo -e "${YELLOW}Skipping integration and E2E tests (run with: ./run_tests.sh e2e)${NC}"
        ;;

    clean)
        echo -e "${GREEN}Cleaning test artifacts...${NC}"
        rm -rf .pytest_cache
        rm -rf htmlcov
        rm -rf .coverage
        rm -rf tests/__pycache__
        rm -rf tests/.pytest_cache
        rm -f /tmp/test_chrome_tab_mcp.sock
        echo -e "${GREEN}✓ Cleaned${NC}"
        ;;

    help|--help|-h)
        echo "Usage: $0 [test_type]"
        echo ""
        echo "Test types:"
        echo "  unit         - Run unit tests (FastAPI schema, HTTP server, native messaging)"
        echo "  integration  - Run integration tests (requires native host)"
        echo "  e2e          - Run end-to-end tests (requires Chrome + extension)"
        echo "  manual       - Run manual interactive test"
        echo "  coverage     - Run tests with coverage report"
        echo "  all          - Run all tests (default)"
        echo "  clean        - Clean test artifacts"
        echo "  help         - Show this help"
        echo ""
        echo "Examples:"
        echo "  $0              # Run all tests"
        echo "  $0 unit         # Quick unit tests (no Chrome needed)"
        echo "  $0 manual       # Test actual Chrome connection"
        echo "  $0 e2e          # Full end-to-end test"
        echo ""
        echo "Note: All tests use 'uv run' to ensure consistent Python environment"
        ;;

    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo "Run '$0 help' for usage"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
