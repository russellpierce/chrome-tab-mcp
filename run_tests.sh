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
    ci)
        echo -e "${GREEN}Running CI-safe tests (no Chrome required)...${NC}"
        echo -e "${YELLOW}These tests can run in GitHub Actions, Claude Code, or locally${NC}"
        echo ""
        echo -e "${BLUE}→ FastAPI Schema Validation${NC}"
        uv run python test_fastapi_server.py
        echo ""
        echo -e "${BLUE}→ Unit Tests (HTTP Server)${NC}"
        uv run pytest tests/test_http_server.py -v
        echo ""
        echo -e "${BLUE}→ Unit Tests (Native Messaging)${NC}"
        uv run pytest tests/test_native_messaging.py -v -m "not integration and not e2e"
        ;;

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

        # Check if Playwright browsers are installed
        echo -e "${BLUE}Checking Playwright browser installation...${NC}"
        if ! uv run python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.chromium.launch(); p.stop()" 2>/dev/null; then
            echo -e "${YELLOW}⚠ Playwright browsers not found or not properly installed${NC}"
            echo ""
            echo "Playwright browsers need to be installed to run e2e tests."
            echo "This will download Chromium (approximately 150-300 MB)."
            echo ""
            read -p "Install Playwright browsers now using 'uv run playwright install chromium'? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo -e "${BLUE}Installing Playwright browsers...${NC}"
                uv run playwright install chromium
                if [ $? -eq 0 ]; then
                    echo -e "${GREEN}✓ Playwright browsers installed successfully${NC}"
                else
                    echo -e "${RED}✗ Failed to install Playwright browsers${NC}"
                    exit 1
                fi
            else
                echo -e "${RED}Cannot run e2e tests without Playwright browsers${NC}"
                echo "You can install them later by running:"
                echo "  uv run playwright install chromium"
                exit 1
            fi
        else
            echo -e "${GREEN}✓ Playwright browsers found${NC}"
        fi
        echo ""

        echo "Prerequisites:"
        echo "  ✓ Playwright browsers installed"
        echo "  1. Extension loaded in Chrome (chrome://extensions/)"
        echo "  2. Native messaging host installed"
        echo ""
        read -p "Continue with e2e tests? (y/n) " -n 1 -r
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
        echo "  ci           - Run CI-safe tests (no Chrome needed - for GitHub Actions)"
        echo "  unit         - Run unit tests (FastAPI schema, HTTP server, native messaging)"
        echo "  integration  - Run integration tests (requires native host)"
        echo "  e2e          - Run end-to-end tests (auto-checks & installs Playwright)"
        echo "  manual       - Run manual interactive test"
        echo "  coverage     - Run tests with coverage report"
        echo "  all          - Run all tests (default)"
        echo "  clean        - Clean test artifacts"
        echo "  help         - Show this help"
        echo ""
        echo "Test Environment Compatibility:"
        echo "  ✓ CI-safe:      ci, unit (no Chrome required)"
        echo "  ✗ Local only:   integration, e2e, manual (Chrome required)"
        echo ""
        echo "Environment Setup:"
        echo "  The 'e2e' test mode automatically checks environment setup and will"
        echo "  prompt to install missing dependencies (e.g., Playwright browsers)"
        echo "  within uv's managed .venv"
        echo ""
        echo "Examples:"
        echo "  $0              # Run all tests"
        echo "  $0 ci           # CI-safe tests (for GitHub Actions)"
        echo "  $0 unit         # Quick unit tests (no Chrome needed)"
        echo "  $0 manual       # Test actual Chrome connection"
        echo "  $0 e2e          # Full end-to-end test (auto-setup)"
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
