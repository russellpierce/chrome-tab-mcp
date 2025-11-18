#!/usr/bin/env pwsh
#
# Test Runner for Chrome Tab Reader (Windows PowerShell)
#
# Usage:
#   .\run_tests.ps1              # Run all tests
#   .\run_tests.ps1 unit         # Run unit tests only
#   .\run_tests.ps1 integration  # Run integration tests
#   .\run_tests.ps1 e2e          # Run end-to-end tests
#   .\run_tests.ps1 manual       # Run manual interactive test
#

param(
    [Parameter(Position=0)]
    [string]$TestType = "all"
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors
function Write-Header {
    param([string]$Message)
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue
    Write-Host "  $Message" -ForegroundColor Blue
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue
    Write-Host ""
}

function Write-Success {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Green
}

function Write-Error-Msg {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Red
}

function Write-Warning-Msg {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Blue
}

# Change to script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Print header
Write-Header "Chrome Tab Reader - Test Suite"

# Ensure dependencies are installed (skip for clean/help commands)
if ($TestType -notin @("clean", "help", "--help", "-h")) {
    Write-Warning-Msg "Checking dependencies..."
    try {
        $syncOutput = uv sync --extra test --quiet 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✓ Dependencies synced"
            Write-Host ""
        } else {
            Write-Error-Msg "✗ Failed to sync dependencies"
            Write-Host "Run: uv sync --extra test"
            exit 1
        }
    } catch {
        Write-Error-Msg "✗ Failed to sync dependencies"
        Write-Host "Run: uv sync --extra test"
        exit 1
    }
}

switch ($TestType) {
    "ci" {
        Write-Success "Running CI-safe tests (no Chrome required)..."
        Write-Warning-Msg "These tests can run in GitHub Actions, Claude Code, or locally"
        Write-Host ""
        Write-Info "→ Unit Tests (HTTP Server)"
        uv run pytest tests/test_http_server.py -v
        Write-Host ""
        Write-Info "→ Unit Tests (Native Messaging)"
        uv run pytest tests/test_native_messaging.py -v -m "not integration and not e2e"
    }

    "unit" {
        Write-Success "Running unit tests..."
        Write-Host ""
        Write-Info "→ Native Messaging Protocol Tests"
        uv run pytest tests/test_native_messaging.py -v -m "not integration and not e2e"
        Write-Host ""
        Write-Info "→ HTTP Server Tests"
        uv run pytest tests/test_http_server.py -v
    }

    "integration" {
        Write-Success "Running integration tests..."
        Write-Warning-Msg "Note: These tests require the native host to be running"
        uv run pytest tests/test_native_messaging.py -v -m integration
    }

    "e2e" {
        Write-Success "Running end-to-end tests..."
        Write-Warning-Msg "Note: These tests require Chrome with extension loaded"
        Write-Host ""

        # Check if Playwright browsers are installed
        Write-Info "Checking Playwright browser installation..."
        try {
            $null = uv run python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.chromium.launch(); p.stop()" 2>&1
            $playwrightInstalled = $LASTEXITCODE -eq 0
        } catch {
            $playwrightInstalled = $false
        }

        if (-not $playwrightInstalled) {
            Write-Warning-Msg "⚠ Playwright browsers not found or not properly installed"
            Write-Host ""
            Write-Host "Playwright browsers need to be installed to run e2e tests."
            Write-Host "This will download Chromium (approximately 150-300 MB)."
            Write-Host ""
            $response = Read-Host "Install Playwright browsers now using 'uv run playwright install chromium'? (y/n)"

            if ($response -match "^[Yy]") {
                Write-Info "Installing Playwright browsers..."
                uv run playwright install chromium
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "✓ Playwright browsers installed successfully"
                } else {
                    Write-Error-Msg "✗ Failed to install Playwright browsers"
                    exit 1
                }
            } else {
                Write-Error-Msg "Cannot run e2e tests without Playwright browsers"
                Write-Host "You can install them later by running:"
                Write-Host "  uv run playwright install chromium"
                exit 1
            }
        } else {
            Write-Success "✓ Playwright browsers found"
        }
        Write-Host ""

        Write-Host "Prerequisites:"
        Write-Host "  ✓ Playwright browsers installed"
        Write-Host "  1. Extension loaded in Chrome (chrome://extensions/)"
        Write-Host "  2. Native messaging host installed"
        Write-Host ""
        $response = Read-Host "Continue with e2e tests? (y/n)"

        if ($response -match "^[Yy]") {
            uv run pytest tests/test_e2e_native_messaging.py -v -m e2e -s
        } else {
            Write-Host "Cancelled"
            exit 0
        }
    }

    "extension" {
        Write-Success "Running Chrome extension tests..."
        Write-Warning-Msg "Note: These tests require Chrome and will open browser windows"
        Write-Host ""

        # Check if npm is available
        $npmExists = Get-Command npm -ErrorAction SilentlyContinue
        if (-not $npmExists) {
            Write-Error-Msg "✗ npm not found"
            Write-Host "Please install Node.js and npm to run extension tests"
            exit 1
        }

        # Check if node_modules exists
        if (-not (Test-Path "node_modules")) {
            Write-Warning-Msg "Installing npm dependencies..."
            npm install
            Write-Host ""
        }

        Write-Info "→ Running Jest/Puppeteer extension tests"
        npm test
    }

    "manual" {
        Write-Success "Running manual interactive tests..."
        Write-Warning-Msg "This will test the actual connection to Chrome"
        Write-Host ""
        uv run python tests/manual_test_native_messaging.py all
    }

    "coverage" {
        Write-Success "Running tests with coverage..."
        uv run pytest tests/ -v --cov=. --cov-report=html --cov-report=term
        Write-Host ""
        Write-Success "Coverage report generated: htmlcov/index.html"
    }

    "all" {
        Write-Success "Running all tests..."
        Write-Host ""

        Write-Info "1. Unit Tests - Native Messaging"
        try { uv run pytest tests/test_native_messaging.py -v -m "not integration and not e2e" } catch {}
        Write-Host ""

        Write-Info "2. Unit Tests - HTTP Server"
        try { uv run pytest tests/test_http_server.py -v } catch {}
        Write-Host ""

        Write-Info "3. Manual Test (Quick Check)"
        try { uv run python tests/manual_test_native_messaging.py protocol } catch {}
        Write-Host ""

        Write-Info "5. Chrome Extension Tests (Jest/Puppeteer)"
        $npmExists = Get-Command npm -ErrorAction SilentlyContinue
        if ($npmExists -and (Test-Path "node_modules")) {
            try { npm test } catch {}
            Write-Host ""
        } else {
            Write-Warning-Msg "⚠ Skipping extension tests (npm not found or dependencies not installed)"
            Write-Host "  Run: npm install && npm test"
            Write-Host ""
        }

        Write-Warning-Msg "Skipping integration and E2E tests (run with: .\run_tests.ps1 e2e)"
    }

    "clean" {
        Write-Success "Cleaning test artifacts..."
        $itemsToRemove = @(
            ".pytest_cache",
            "htmlcov",
            ".coverage",
            "coverage",
            "tests/__pycache__",
            "tests/.pytest_cache"
        )

        foreach ($item in $itemsToRemove) {
            if (Test-Path $item) {
                Remove-Item -Recurse -Force $item
            }
        }

        # Remove temp socket file if it exists (Windows may use named pipes)
        $tempSocket = "$env:TEMP\test_chrome_tab_mcp.sock"
        if (Test-Path $tempSocket) {
            Remove-Item -Force $tempSocket
        }

        Write-Success "✓ Cleaned"
    }

    { $_ -in @("help", "--help", "-h") } {
        Write-Host "Usage: .\run_tests.ps1 [test_type]"
        Write-Host ""
        Write-Host "Test types:"
        Write-Host "  ci           - Run CI-safe tests (no Chrome needed - for GitHub Actions)"
        Write-Host "  unit         - Run unit tests (FastAPI schema, HTTP server, native messaging)"
        Write-Host "  integration  - Run integration tests (requires native host)"
        Write-Host "  e2e          - Run end-to-end tests (auto-checks & installs Playwright)"
        Write-Host "  extension    - Run Chrome extension tests (Jest/Puppeteer - requires Chrome)"
        Write-Host "  manual       - Run manual interactive test"
        Write-Host "  coverage     - Run tests with coverage report"
        Write-Host "  all          - Run all tests (default)"
        Write-Host "  clean        - Clean test artifacts"
        Write-Host "  help         - Show this help"
        Write-Host ""
        Write-Host "Test Environment Compatibility:"
        Write-Host "  ✓ CI-safe:      ci, unit (no Chrome required)"
        Write-Host "  ✗ Local only:   integration, e2e, extension, manual (Chrome required)"
        Write-Host ""
        Write-Host "Environment Setup:"
        Write-Host "  The 'e2e' test mode automatically checks environment setup and will"
        Write-Host "  prompt to install missing dependencies (e.g., Playwright browsers)"
        Write-Host "  within uv's managed .venv"
        Write-Host ""
        Write-Host "Examples:"
        Write-Host "  .\run_tests.ps1              # Run all tests"
        Write-Host "  .\run_tests.ps1 ci           # CI-safe tests (for GitHub Actions)"
        Write-Host "  .\run_tests.ps1 unit         # Quick unit tests (no Chrome needed)"
        Write-Host "  .\run_tests.ps1 manual       # Test actual Chrome connection"
        Write-Host "  .\run_tests.ps1 e2e          # Full end-to-end test (auto-setup)"
        Write-Host ""
        Write-Host "Note: All tests use 'uv run' to ensure consistent Python environment"
    }

    default {
        Write-Error-Msg "Unknown test type: $TestType"
        Write-Host "Run '.\run_tests.ps1 help' for usage"
        exit 1
    }
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue
