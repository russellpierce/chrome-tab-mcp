#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "fastapi>=0.104.0",
#   "uvicorn[standard]>=0.24.0",
#   "platformdirs>=4.0.0",
# ]
# ///
"""
Chrome Tab Reader - HTTP Server (FastAPI)

Provides HTTP API for Chrome tab content extraction.
Currently uses AppleScript (macOS) or Chrome DevTools Protocol.
Future: Will use extension via Native Messaging.

Endpoints:
  POST   /api/extract              - Extract current tab content
  POST   /api/navigate_and_extract - Navigate to URL and extract
  GET    /api/current_tab          - Get current tab info
  GET    /api/health               - Health check
  GET    /                          - API documentation (redirects to /docs)

Port: 8888 (configurable)

Access Control:
  Requires Bearer token authentication for all API endpoints.

  Token configuration file location follows platform standards:
    - Linux: $XDG_CONFIG_HOME/chrome-tab-reader/tokens.json (XDG Base Directory Specification)
             Falls back to ~/.config/chrome-tab-reader/tokens.json if XDG_CONFIG_HOME not set
    - macOS: ~/Library/Application Support/chrome-tab-reader/tokens.json
    - Windows: %APPDATA%\chrome-tab-reader\tokens.json

Dependencies:
  Run with uv: uv run chrome_tab_http_server.py
  Or install manually: pip install -r requirements.txt
"""

import json
import sys
import platform
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, Set, Optional, List
import logging

# FastAPI imports
from fastapi import FastAPI, HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, Field

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[Chrome Tab Reader] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models (Request/Response Schemas)
# ============================================================================

class ExtractRequest(BaseModel):
    """Request model for extracting tab content"""
    action: str = Field(
        default="extract_current_tab",
        description="Action to perform",
        examples=["extract_current_tab"]
    )
    strategy: str = Field(
        default="three-phase",
        description="Extraction strategy: 'three-phase' waits for lazy-loaded content, 'immediate' extracts right away",
        examples=["three-phase", "immediate"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "action": "extract_current_tab",
                "strategy": "three-phase"
            }
        }


class NavigateAndExtractRequest(BaseModel):
    """Request model for navigating to URL and extracting content"""
    url: str = Field(
        ...,
        description="URL to navigate to",
        examples=["https://example.com"]
    )
    action: str = Field(
        default="navigate_and_extract",
        description="Action to perform"
    )
    strategy: str = Field(
        default="three-phase",
        description="Extraction strategy",
        examples=["three-phase", "immediate"]
    )
    wait_for_ms: int = Field(
        default=0,
        description="Additional milliseconds to wait before extraction",
        ge=0
    )

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com",
                "strategy": "three-phase",
                "wait_for_ms": 5000
            }
        }


class ExtractionResponse(BaseModel):
    """Response model for extraction operations"""
    status: str = Field(..., description="Operation status", examples=["success", "error"])
    content: Optional[str] = Field(None, description="Extracted text content")
    title: Optional[str] = Field(None, description="Page title")
    url: Optional[str] = Field(None, description="Page URL")
    extraction_time_ms: Optional[float] = Field(None, description="Time taken for extraction in milliseconds")
    error: Optional[str] = Field(None, description="Error message if status is 'error'")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "content": "Extracted page content...",
                "title": "Example Domain",
                "url": "https://example.com",
                "extraction_time_ms": 4500
            }
        }


class TabInfoResponse(BaseModel):
    """Response model for current tab information"""
    tab_id: Optional[str] = Field(None, description="Tab identifier (may be 'unknown' on some platforms)")
    url: Optional[str] = Field(None, description="Current tab URL")
    title: Optional[str] = Field(None, description="Current tab title")
    is_loading: Optional[bool] = Field(None, description="Whether the page is currently loading")
    status: Optional[str] = Field(None, description="Status of the operation")
    error: Optional[str] = Field(None, description="Error message if any")

    class Config:
        json_schema_extra = {
            "example": {
                "tab_id": "unknown",
                "url": "https://example.com",
                "title": "Example Domain",
                "is_loading": False
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str = Field(..., description="Server status", examples=["ok"])
    extension_version: str = Field(..., description="Extension version")
    port: int = Field(..., description="Server port number")
    platform: str = Field(..., description="Operating system platform")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "extension_version": "1.0.0",
                "port": 8888,
                "platform": "Darwin"
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Unauthorized",
                "message": "Valid Bearer token required"
            }
        }


# ============================================================================
# Configuration and Token Management
# ============================================================================

def get_config_dir() -> Path:
    """Get platform-specific config directory following XDG Base Directory Specification.

    Uses platformdirs library for proper cross-platform support.
    Falls back to manual implementation if platformdirs is not available.

    Returns:
        Path: Config directory for chrome-tab-reader
            - Linux: $XDG_CONFIG_HOME/chrome-tab-reader or ~/.config/chrome-tab-reader
            - macOS: ~/Library/Application Support/chrome-tab-reader
            - Windows: %APPDATA%\\chrome-tab-reader

    References:
        - XDG Base Directory Specification: https://specifications.freedesktop.org/basedir/latest/
        - platformdirs: https://github.com/platformdirs/platformdirs
    """
    try:
        # Use platformdirs for proper XDG compliance and cross-platform support
        import platformdirs
        config_dir = Path(platformdirs.user_config_dir("chrome-tab-reader", appauthor=False))
        logger.debug(f"Using platformdirs for config directory: {config_dir}")
        return config_dir
    except ImportError:
        # Fallback implementation following XDG spec manually
        logger.debug("platformdirs not available, using fallback implementation")
        system = platform.system()

        if system == "Windows":
            # Windows: Use APPDATA
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
            return base / "chrome-tab-reader"
        elif system == "Darwin":
            # macOS: Use ~/Library/Application Support
            return Path.home() / "Library" / "Application Support" / "chrome-tab-reader"
        else:
            # Linux and others: Follow XDG Base Directory Specification
            # XDG_CONFIG_HOME defines the base directory relative to which user-specific
            # configuration files should be stored. If not set, defaults to ~/.config
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config:
                base = Path(xdg_config)
            else:
                base = Path.home() / ".config"
            return base / "chrome-tab-reader"


# Token configuration
CONFIG_DIR = get_config_dir()
TOKENS_FILE = CONFIG_DIR / "tokens.json"


def load_valid_tokens() -> Set[str]:
    """Load valid access tokens from configuration file"""
    if not TOKENS_FILE.exists():
        logger.warning(f"Tokens file not found at {TOKENS_FILE}")
        logger.info("Creating default tokens file. Please add your extension token.")
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(TOKENS_FILE, 'w') as f:
            json.dump({
                "tokens": [],
                "note": "Add your extension access token here. Get it from the extension popup."
            }, f, indent=2)

        # Set secure permissions on newly created file (Unix-like systems only)
        if platform.system() != "Windows":
            try:
                TOKENS_FILE.chmod(0o600)
                logger.info(f"Set secure permissions (600) on {TOKENS_FILE}")
            except Exception as e:
                logger.warning(f"Could not set file permissions: {e}")

        return set()

    # Check and enforce file permissions on existing file
    if platform.system() != "Windows":
        try:
            stat_info = TOKENS_FILE.stat()
            current_perms = stat_info.st_mode & 0o777

            if current_perms != 0o600:
                logger.warning(f"Tokens file has insecure permissions: {oct(current_perms)}")
                logger.warning(f"Attempting to fix permissions to 600...")
                TOKENS_FILE.chmod(0o600)
                logger.info(f"Fixed permissions on {TOKENS_FILE}")
        except Exception as e:
            logger.warning(f"Could not check/set file permissions: {e}")

    try:
        with open(TOKENS_FILE, 'r') as f:
            data = json.load(f)
            tokens = data.get("tokens", [])
            logger.info(f"Loaded {len(tokens)} valid token(s)")
            return set(tokens)
    except Exception as e:
        logger.error(f"Error loading tokens file: {e}")
        return set()


# Load valid tokens
VALID_TOKENS = load_valid_tokens()


# ============================================================================
# Chrome Tab Extraction Logic
# ============================================================================

class ChromeTabExtractor:
    """Extract content from Chrome tabs"""

    @staticmethod
    def run_applescript(script_path: str) -> Dict[str, Any]:
        """Run AppleScript and return JSON result"""
        try:
            result = subprocess.run(
                ["osascript", script_path],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes
            )

            if result.returncode != 0:
                return {
                    "status": "error",
                    "error": f"AppleScript error: {result.stderr}"
                }

            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "error": f"Invalid JSON from AppleScript: {result.stdout[:200]}"
                }
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "AppleScript execution timeout (5 minutes)"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"AppleScript error: {str(e)}"
            }

    @staticmethod
    def extract_current_tab() -> Dict[str, Any]:
        """Extract current tab content"""
        logger.info("Extracting current tab content")

        # macOS: Use AppleScript
        if platform.system() == "Darwin":
            script_path = Path(__file__).parent / "chrome_tab.scpt"
            if not script_path.exists():
                return {
                    "status": "error",
                    "error": "AppleScript not found at " + str(script_path)
                }
            return ChromeTabExtractor.run_applescript(str(script_path))

        # Other platforms: Would use extension or other method
        return {
            "status": "error",
            "error": "Tab extraction not yet implemented for " + platform.system() + ". "
                     "Please use extension with Native Messaging support."
        }

    @staticmethod
    def navigate_and_extract(url: str, wait_for_ms: int = 0) -> Dict[str, Any]:
        """Navigate to URL and extract content"""
        logger.info(f"Navigate and extract: {url}")

        # This would require AppleScript enhancement or extension with navigation
        return {
            "status": "error",
            "error": "Navigate and extract not yet implemented. "
                     "Use extract endpoint on the target page instead."
        }

    @staticmethod
    def get_current_tab_info() -> Dict[str, Any]:
        """Get current tab info"""
        logger.info("Getting current tab info")

        if platform.system() == "Darwin":
            script_path = Path(__file__).parent / "chrome_tab.scpt"
            result = ChromeTabExtractor.run_applescript(str(script_path))
            if result.get("status") == "success":
                return {
                    "tab_id": "unknown",
                    "url": result.get("url", ""),
                    "title": result.get("title", ""),
                    "is_loading": False
                }
            return result

        return {
            "status": "error",
            "error": "Tab info not available"
        }


# ============================================================================
# FastAPI Application Setup
# ============================================================================

app = FastAPI(
    title="Chrome Tab Reader API",
    description="""
HTTP API for extracting content from Chrome tabs.

## Features
- Extract content from the currently active Chrome tab
- Bearer token authentication for security
- Cross-platform configuration (XDG-compliant on Linux)
- Support for multiple extraction strategies

## Authentication
All endpoints (except documentation) require Bearer token authentication.
Get your token from the Chrome extension popup, then add it to the configuration file.

## Configuration
Token file location:
- Linux: `$XDG_CONFIG_HOME/chrome-tab-reader/tokens.json` or `~/.config/chrome-tab-reader/tokens.json`
- macOS: `~/Library/Application Support/chrome-tab-reader/tokens.json`
- Windows: `%APPDATA%\\chrome-tab-reader\\tokens.json`
    """,
    version="1.0.0",
    contact={
        "name": "Chrome Tab Reader",
        "url": "https://github.com/russellpierce/chrome-tab-mcp"
    },
    servers=[
        {"url": "http://localhost:8888", "description": "Local development server"}
    ]
)

# Security scheme
security = HTTPBearer()


# ============================================================================
# Authentication Dependency
# ============================================================================

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Verify Bearer token from Authorization header.

    Raises:
        HTTPException: 401 if token is invalid

    Returns:
        str: The validated token
    """
    token = credentials.credentials
    if token not in VALID_TOKENS:
        logger.warning(f"Invalid token attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "Unauthorized",
                "message": f"Valid Bearer token required. Configure tokens in {TOKENS_FILE}"
            }
        )
    return token


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to interactive API documentation"""
    return RedirectResponse(url="/docs")


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check endpoint",
    description="Check if the API server is running and responsive."
)
async def health_check(token: str = Depends(verify_token)):
    """
    Health check endpoint to verify the server is running.

    Returns server status, version, port, and platform information.
    """
    return HealthResponse(
        status="ok",
        extension_version="1.0.0",
        port=8888,
        platform=platform.system()
    )


@app.get(
    "/api/current_tab",
    response_model=TabInfoResponse,
    tags=["Tab Information"],
    summary="Get current tab information",
    description="Retrieve information about the currently active Chrome tab without extracting its content.",
    responses={
        200: {"description": "Current tab information retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized - Invalid or missing Bearer token"},
        500: {"description": "Tab information unavailable"}
    }
)
async def get_current_tab(token: str = Depends(verify_token)):
    """
    Get information about the currently active Chrome tab.

    Returns tab ID, URL, title, and loading status.
    """
    result = ChromeTabExtractor.get_current_tab_info()
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result)
    return TabInfoResponse(**result)


@app.post(
    "/api/extract",
    response_model=ExtractionResponse,
    tags=["Content Extraction"],
    summary="Extract content from current Chrome tab",
    description="Extracts text content from the currently active Chrome tab using the configured extraction strategy.",
    responses={
        200: {"description": "Content extracted successfully"},
        401: {"model": ErrorResponse, "description": "Unauthorized - Invalid or missing Bearer token"},
        500: {"description": "Internal server error during extraction"}
    }
)
async def extract_tab_content(
    request: ExtractRequest,
    token: str = Depends(verify_token)
):
    """
    Extract content from the currently active Chrome tab.

    Supports different extraction strategies:
    - **three-phase**: Waits for lazy-loaded content (recommended)
    - **immediate**: Extracts content immediately

    Returns the extracted text content along with page metadata.
    """
    logger.info(f"Extract request: action={request.action}, strategy={request.strategy}")
    result = ChromeTabExtractor.extract_current_tab()

    if result.get("status") != "success":
        raise HTTPException(status_code=500, detail=result)

    return ExtractionResponse(**result)


@app.post(
    "/api/navigate_and_extract",
    response_model=ExtractionResponse,
    tags=["Content Extraction"],
    summary="Navigate to URL and extract content",
    description="Navigate Chrome to a specific URL and extract its content. Currently not implemented - returns error.",
    responses={
        200: {"description": "Navigation and extraction successful"},
        400: {"model": ErrorResponse, "description": "Bad request - missing required URL parameter"},
        401: {"model": ErrorResponse, "description": "Unauthorized - Invalid or missing Bearer token"},
        500: {"description": "Not yet implemented or internal server error"}
    }
)
async def navigate_and_extract(
    request: NavigateAndExtractRequest,
    token: str = Depends(verify_token)
):
    """
    Navigate to a URL and extract its content.

    **Note**: This endpoint is not yet fully implemented and will return an error.
    Use the `/api/extract` endpoint on the target page instead.
    """
    logger.info(f"Navigate and extract request: url={request.url}, strategy={request.strategy}")
    result = ChromeTabExtractor.navigate_and_extract(request.url, request.wait_for_ms)

    if result.get("status") != "success":
        raise HTTPException(status_code=500, detail=result)

    return ExtractionResponse(**result)


# ============================================================================
# Server Startup
# ============================================================================

def main():
    """Main entry point"""
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(
        description="Chrome Tab Reader - HTTP API Server (FastAPI)",
        epilog="""
Examples:
  python chrome_tab_http_server.py                    # Start on port 8888
  python chrome_tab_http_server.py --port 9000        # Start on port 9000
  python chrome_tab_http_server.py --host 0.0.0.0     # Listen on all interfaces

Interactive API documentation available at:
  - Swagger UI: http://localhost:8888/docs
  - ReDoc: http://localhost:8888/redoc
  - OpenAPI JSON: http://localhost:8888/openapi.json

Note: On macOS, this requires chrome_tab.scpt in the same directory.
        """
    )

    parser.add_argument("--port", type=int, default=8888, help="Port to listen on (default: 8888)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    # Security: Force localhost binding only
    # On untrusted LANs, binding to 0.0.0.0 would expose the service to all network devices
    args.host = "127.0.0.1"
    logger.info("Security: Server restricted to localhost (127.0.0.1) only")

    # Verify prerequisites
    if platform.system() == "Darwin":
        script_path = Path(__file__).parent / "chrome_tab.scpt"
        if not script_path.exists():
            logger.error(f"chrome_tab.scpt not found at {script_path}")
            logger.error("Please make sure the AppleScript file is in the same directory")
            sys.exit(1)

    logger.info(f"Starting Chrome Tab Reader HTTP server on {args.host}:{args.port}")
    logger.info(f"Interactive API documentation:")
    logger.info(f"  - Swagger UI: http://{args.host}:{args.port}/docs")
    logger.info(f"  - ReDoc: http://{args.host}:{args.port}/redoc")
    logger.info(f"  - OpenAPI spec: http://{args.host}:{args.port}/openapi.json")

    uvicorn.run(
        "chrome_tab_http_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()
