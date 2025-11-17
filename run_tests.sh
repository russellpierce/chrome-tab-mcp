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

case "$TEST_TYPE" in
    unit)
        echo -e "${GREEN}Running unit tests...${NC}"
        pytest tests/test_native_messaging.py -v -m "not integration and not e2e"
        ;;

    integration)
        echo -e "${GREEN}Running integration tests...${NC}"
        echo -e "${YELLOW}Note: These tests require the native host to be running${NC}"
        pytest tests/test_native_messaging.py -v -m integration
        ;;

    e2e)
        echo -e "${GREEN}Running end-to-end tests...${NC}"
        echo -e "${YELLOW}Note: These tests require Chrome with extension loaded${NC}"
        echo ""
        echo "Prerequisites:"
        echo "  1. Extension loaded in Chrome (chrome://extensions/)"
        echo "  2. Native messaging host installed"
        echo "  3. Playwright installed (pip install playwright && playwright install chrome)"
        echo ""
        read -p "Continue? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            pytest tests/test_e2e_native_messaging.py -v -m e2e -s
        else
            echo "Cancelled"
            exit 0
        fi
        ;;

    manual)
        echo -e "${GREEN}Running manual interactive tests...${NC}"
        echo -e "${YELLOW}This will test the actual connection to Chrome${NC}"
        echo ""
        python tests/manual_test_native_messaging.py all
        ;;

    coverage)
        echo -e "${GREEN}Running tests with coverage...${NC}"
        pytest tests/ -v --cov=. --cov-report=html --cov-report=term
        echo ""
        echo -e "${GREEN}Coverage report generated: htmlcov/index.html${NC}"
        ;;

    all)
        echo -e "${GREEN}Running all tests...${NC}"
        echo ""

        echo -e "${BLUE}1. Unit Tests${NC}"
        pytest tests/test_native_messaging.py -v -m "not integration and not e2e" || true
        echo ""

        echo -e "${BLUE}2. Manual Test (Quick Check)${NC}"
        python tests/manual_test_native_messaging.py protocol || true
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
        echo "  unit         - Run unit tests (fast, no Chrome needed)"
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
        echo "  $0 unit         # Quick unit tests"
        echo "  $0 manual       # Test actual Chrome connection"
        echo "  $0 e2e          # Full end-to-end test"
        ;;

    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo "Run '$0 help' for usage"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
