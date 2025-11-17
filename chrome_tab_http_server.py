#!/usr/bin/env python3
"""
Chrome Tab Reader - HTTP Server

Provides HTTP API for Chrome tab content extraction.
Currently uses AppleScript (macOS) or Chrome DevTools Protocol.
Future: Will use extension via Native Messaging.

Endpoints:
  POST   /api/extract              - Extract current tab content
  POST   /api/navigate_and_extract - Navigate to URL and extract
  GET    /api/current_tab          - Get current tab info
  GET    /api/health               - Health check
  GET    /                          - API documentation

Port: 8888 (configurable)

Access Control:
  Requires Bearer token authentication for all API endpoints.

  Token configuration file location follows platform standards:
    - Linux: $XDG_CONFIG_HOME/chrome-tab-reader/tokens.json (XDG Base Directory Specification)
             Falls back to ~/.config/chrome-tab-reader/tokens.json if XDG_CONFIG_HOME not set
    - macOS: ~/Library/Application Support/chrome-tab-reader/tokens.json
    - Windows: %APPDATA%\chrome-tab-reader\tokens.json

Dependencies:
  Optional: platformdirs (for proper XDG compliance, will fallback if not available)
  Install with: pip install platformdirs
"""

import json
import sys
import platform
import subprocess
import threading
import time
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from typing import Dict, Any, Set, Callable, Optional
import logging
from functools import wraps

# Set up logging first
logging.basicConfig(
    level=logging.INFO,
    format='[Chrome Tab Reader] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# OpenAPI spec generation
try:
    from apispec import APISpec
    APISPEC_AVAILABLE = True
except ImportError:
    APISPEC_AVAILABLE = False
    logger.warning("apispec not available. OpenAPI spec generation will be disabled.")


# ============================================================================
# OpenAPI Specification Generation
# ============================================================================

# Initialize APISpec if available
if APISPEC_AVAILABLE:
    spec = APISpec(
        title="Chrome Tab Reader API",
        version="1.0.0",
        openapi_version="3.0.3",
        info={
            "description": "HTTP API for extracting content from Chrome tabs. "
                          "Supports both AppleScript (macOS) and Chrome extension-based extraction.",
            "contact": {
                "name": "Chrome Tab Reader",
                "url": "https://github.com/russellpierce/chrome-tab-mcp"
            }
        },
        servers=[
            {"url": "http://localhost:8888", "description": "Local development server"}
        ],
        # Security scheme for Bearer token authentication
        components={
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "Bearer token authentication. Get your token from the Chrome extension popup."
                }
            }
        }
    )
else:
    spec = None


# Endpoint metadata storage for OpenAPI spec generation
_endpoint_metadata = {}


def openapi_endpoint(
    method: str,
    path: str,
    summary: str,
    description: str = "",
    request_schema: Optional[Dict[str, Any]] = None,
    response_schema: Optional[Dict[str, Any]] = None,
    error_responses: Optional[Dict[int, str]] = None,
    requires_auth: bool = True,
    tags: Optional[list] = None
):
    """
    Decorator to add OpenAPI metadata to endpoint handlers.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: API endpoint path
        summary: Short summary of what the endpoint does
        description: Detailed description of the endpoint
        request_schema: JSON schema for request body (for POST/PUT)
        response_schema: JSON schema for successful response
        error_responses: Dict mapping status codes to error descriptions
        requires_auth: Whether the endpoint requires Bearer token authentication
        tags: List of tags for grouping endpoints

    Example:
        @openapi_endpoint(
            method="GET",
            path="/api/health",
            summary="Health check endpoint",
            response_schema={"type": "object", "properties": {...}},
            requires_auth=True
        )
        def handle_health(self):
            ...
    """
    def decorator(func: Callable) -> Callable:
        # Store metadata for later spec generation
        endpoint_key = f"{method}:{path}"
        _endpoint_metadata[endpoint_key] = {
            "method": method.lower(),
            "path": path,
            "summary": summary,
            "description": description,
            "request_schema": request_schema,
            "response_schema": response_schema,
            "error_responses": error_responses or {},
            "requires_auth": requires_auth,
            "tags": tags or ["API"]
        }

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper
    return decorator


def build_openapi_spec() -> Dict[str, Any]:
    """
    Build the OpenAPI specification from decorated endpoints.

    Returns:
        Dict containing the complete OpenAPI 3.0 specification
    """
    if not APISPEC_AVAILABLE or spec is None:
        return {
            "openapi": "3.0.3",
            "info": {
                "title": "Chrome Tab Reader API",
                "version": "1.0.0",
                "description": "OpenAPI spec generation unavailable (apispec not installed)"
            },
            "paths": {}
        }

    # Clear existing paths
    spec._paths = {}

    # Add each endpoint to the spec
    for endpoint_key, metadata in _endpoint_metadata.items():
        method = metadata["method"]
        path = metadata["path"]

        # Build operation object
        operation = {
            "summary": metadata["summary"],
            "description": metadata["description"],
            "tags": metadata["tags"],
        }

        # Add security requirement if needed
        if metadata["requires_auth"]:
            operation["security"] = [{"BearerAuth": []}]

        # Add request body if present
        if metadata["request_schema"]:
            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": metadata["request_schema"]
                    }
                }
            }

        # Add responses
        responses = {}

        # Success response
        if metadata["response_schema"]:
            responses["200"] = {
                "description": "Successful response",
                "content": {
                    "application/json": {
                        "schema": metadata["response_schema"]
                    }
                }
            }

        # Error responses
        if metadata["requires_auth"]:
            responses["401"] = {
                "description": "Unauthorized - Invalid or missing Bearer token",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {"type": "string"},
                                "message": {"type": "string"}
                            }
                        }
                    }
                }
            }

        # Add custom error responses
        for status_code, description in metadata.get("error_responses", {}).items():
            responses[str(status_code)] = {"description": description}

        operation["responses"] = responses

        # Add operation to spec
        spec.path(path=path, operations={method: operation})

    return spec.to_dict()


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
        return set()

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


class ChromeTabHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Chrome Tab Reader API"""

    def validate_token(self) -> bool:
        """Validate Bearer token from Authorization header"""
        auth_header = self.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return False

        token = auth_header[7:]  # Remove 'Bearer ' prefix
        return token in VALID_TOKENS

    def send_unauthorized(self):
        """Send 401 Unauthorized response"""
        response = {
            "error": "Unauthorized",
            "message": f"Valid Bearer token required. Configure tokens in {TOKENS_FILE}"
        }
        self.send_json_response(401, response)

    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        logger.info(f"GET {path}")

        # Root path is public (API documentation)
        if path == "/":
            self.send_api_docs()
            return

        # All other endpoints require authentication
        if not self.validate_token():
            logger.warning(f"Unauthorized GET request to {path}")
            self.send_unauthorized()
            return

        if path == "/api/current_tab":
            self.handle_current_tab()
        elif path == "/api/health":
            self.handle_health()
        elif path == "/api/openapi.json":
            self.handle_openapi_spec()
        else:
            self.send_json_response(404, {"error": "Not found"})

    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # All POST endpoints require authentication
        if not self.validate_token():
            logger.warning(f"Unauthorized POST request to {path}")
            self.send_unauthorized()
            return

        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            request_data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_json_response(400, {"error": "Invalid JSON in request body"})
            return

        logger.info(f"POST {path} - {request_data.get('action', 'unknown')}")

        if path == "/api/extract":
            self.handle_extract(request_data)
        elif path == "/api/navigate_and_extract":
            self.handle_navigate_and_extract(request_data)
        else:
            self.send_json_response(404, {"error": "Not found"})

    @openapi_endpoint(
        method="POST",
        path="/api/extract",
        summary="Extract content from current Chrome tab",
        description="Extracts text content from the currently active Chrome tab using the configured extraction strategy.",
        request_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["extract_current_tab"],
                    "default": "extract_current_tab",
                    "description": "Action to perform"
                },
                "strategy": {
                    "type": "string",
                    "enum": ["three-phase", "immediate"],
                    "default": "three-phase",
                    "description": "Extraction strategy: 'three-phase' waits for lazy-loaded content, 'immediate' extracts right away"
                }
            }
        },
        response_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["success", "error"]},
                "content": {"type": "string", "description": "Extracted text content"},
                "title": {"type": "string", "description": "Page title"},
                "url": {"type": "string", "description": "Page URL"},
                "extraction_time_ms": {"type": "number", "description": "Time taken for extraction in milliseconds"}
            },
            "required": ["status"]
        },
        error_responses={
            500: "Internal server error during extraction"
        },
        tags=["Content Extraction"]
    )
    def handle_extract(self, request_data: Dict):
        """Handle /api/extract endpoint"""
        strategy = request_data.get("strategy", "three-phase")
        action = request_data.get("action", "extract_current_tab")

        result = ChromeTabExtractor.extract_current_tab()
        self.send_json_response(200 if result.get("status") == "success" else 500, result)

    @openapi_endpoint(
        method="POST",
        path="/api/navigate_and_extract",
        summary="Navigate to URL and extract content",
        description="Navigate Chrome to a specific URL and extract its content. Currently not implemented - returns error.",
        request_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "default": "navigate_and_extract",
                    "description": "Action to perform"
                },
                "url": {
                    "type": "string",
                    "format": "uri",
                    "description": "URL to navigate to"
                },
                "strategy": {
                    "type": "string",
                    "enum": ["three-phase", "immediate"],
                    "default": "three-phase",
                    "description": "Extraction strategy"
                },
                "wait_for_ms": {
                    "type": "integer",
                    "default": 0,
                    "description": "Additional milliseconds to wait before extraction"
                }
            },
            "required": ["url"]
        },
        response_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["success", "error"]},
                "content": {"type": "string", "description": "Extracted text content"},
                "title": {"type": "string", "description": "Page title"},
                "url": {"type": "string", "description": "Page URL"},
                "extraction_time_ms": {"type": "number", "description": "Time taken for extraction in milliseconds"}
            },
            "required": ["status"]
        },
        error_responses={
            400: "Bad request - missing required URL parameter",
            500: "Not yet implemented or internal server error"
        },
        tags=["Content Extraction"]
    )
    def handle_navigate_and_extract(self, request_data: Dict):
        """Handle /api/navigate_and_extract endpoint"""
        url = request_data.get("url")
        if not url:
            self.send_json_response(400, {"error": "Missing 'url' parameter"})
            return

        strategy = request_data.get("strategy", "three-phase")
        wait_for_ms = request_data.get("wait_for_ms", 0)

        result = ChromeTabExtractor.navigate_and_extract(url, wait_for_ms)
        self.send_json_response(200 if result.get("status") == "success" else 500, result)

    @openapi_endpoint(
        method="GET",
        path="/api/current_tab",
        summary="Get current tab information",
        description="Retrieve information about the currently active Chrome tab without extracting its content.",
        response_schema={
            "type": "object",
            "properties": {
                "tab_id": {"type": "string", "description": "Tab identifier (may be 'unknown' on some platforms)"},
                "url": {"type": "string", "format": "uri", "description": "Current tab URL"},
                "title": {"type": "string", "description": "Current tab title"},
                "is_loading": {"type": "boolean", "description": "Whether the page is currently loading"}
            }
        },
        error_responses={
            500: "Tab information unavailable"
        },
        tags=["Tab Information"]
    )
    def handle_current_tab(self):
        """Handle /api/current_tab endpoint"""
        result = ChromeTabExtractor.get_current_tab_info()
        self.send_json_response(200 if result.get("status") != "error" else 500, result)

    @openapi_endpoint(
        method="GET",
        path="/api/health",
        summary="Health check endpoint",
        description="Check if the API server is running and responsive.",
        response_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["ok"], "description": "Server status"},
                "extension_version": {"type": "string", "description": "Extension version"},
                "port": {"type": "integer", "description": "Server port number"},
                "platform": {"type": "string", "description": "Operating system platform"}
            },
            "required": ["status"]
        },
        tags=["System"]
    )
    def handle_health(self):
        """Handle /api/health endpoint"""
        response = {
            "status": "ok",
            "extension_version": "1.0.0",
            "port": 8888,
            "platform": platform.system()
        }
        self.send_json_response(200, response)

    def handle_openapi_spec(self):
        """Handle /api/openapi.json endpoint - serve OpenAPI specification"""
        logger.info("Serving OpenAPI specification")
        spec_dict = build_openapi_spec()
        self.send_json_response(200, spec_dict)

    def send_api_docs(self):
        """Send API documentation"""
        # Get platform-specific config path for display
        config_path_display = str(TOKENS_FILE)

        docs = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Chrome Tab Reader API</title>
    <style>
        body {{ font-family: monospace; max-width: 900px; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .auth-notice {{ background: #fff3cd; border: 1px solid #ffc107; padding: 15px; margin: 15px 0; border-radius: 4px; }}
        .config-info {{ background: #d1ecf1; border: 1px solid #0c5460; padding: 15px; margin: 15px 0; border-radius: 4px; }}
        .endpoint {{ background: #f5f5f5; padding: 10px; margin: 10px 0; border-left: 3px solid #007bff; }}
        .method {{ font-weight: bold; color: #007bff; }}
        pre {{ background: #f9f9f9; padding: 10px; overflow-x: auto; border: 1px solid #ddd; border-radius: 3px; }}
        code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 3px; }}
        .platform-path {{ font-weight: bold; color: #0056b3; }}
    </style>
</head>
<body>
    <h1>Chrome Tab Reader HTTP API</h1>

    <p>Base URL: http://localhost:8888</p>

    <div class="config-info">
        <strong>📋 OpenAPI Specification</strong><br>
        Machine-readable API specification available at: <a href="/api/openapi.json" target="_blank"><code>/api/openapi.json</code></a><br>
        Use with tools like <a href="https://editor.swagger.io/" target="_blank">Swagger Editor</a> or <a href="https://www.postman.com/" target="_blank">Postman</a> for interactive API exploration.
    </div>

    <div class="config-info">
        <strong>Configuration File Location</strong><br>
        Your tokens file is located at:<br>
        <code class="platform-path">{config_path_display}</code><br><br>
        <strong>Platform-specific paths:</strong><br>
        • Linux: <code>$XDG_CONFIG_HOME/chrome-tab-reader/tokens.json</code> or <code>~/.config/chrome-tab-reader/tokens.json</code><br>
        • macOS: <code>~/Library/Application Support/chrome-tab-reader/tokens.json</code><br>
        • Windows: <code>%APPDATA%\\chrome-tab-reader\\tokens.json</code><br><br>
        <small>Linux follows <a href="https://specifications.freedesktop.org/basedir/latest/" target="_blank">XDG Base Directory Specification</a></small>
    </div>

    <div class="auth-notice">
        <strong>Authentication Required</strong><br>
        All API endpoints (except this documentation page) require Bearer token authentication.<br>
        Get your token from the Chrome extension popup, then add it to the configuration file shown above.
    </div>

    <h2>Endpoints</h2>

    <div class="endpoint">
        <div class="method">GET /api/openapi.json</div>
        <p>Get OpenAPI 3.0 specification (requires authentication)</p>
        <pre>Returns the complete OpenAPI specification in JSON format.
Can be imported into API testing tools like Postman, Insomnia, or Swagger UI.</pre>
    </div>

    <div class="endpoint">
        <div class="method">GET /api/health</div>
        <p>Health check</p>
        <pre>{{
  "status": "ok",
  "extension_version": "1.0.0",
  "port": 8888
}}</pre>
    </div>

    <div class="endpoint">
        <div class="method">POST /api/extract</div>
        <p>Extract content from current tab</p>
        <pre>Request:
{{
  "action": "extract_current_tab",
  "strategy": "three-phase"
}}

Response:
{{
  "status": "success",
  "content": "extracted text...",
  "title": "Page Title",
  "url": "https://example.com",
  "extraction_time_ms": 4500
}}</pre>
    </div>

    <div class="endpoint">
        <div class="method">POST /api/navigate_and_extract</div>
        <p>Navigate to URL and extract content</p>
        <pre>Request:
{{
  "action": "navigate_and_extract",
  "url": "https://example.com/page",
  "strategy": "three-phase",
  "wait_for_ms": 5000
}}

Response: (same as extract)</pre>
    </div>

    <div class="endpoint">
        <div class="method">GET /api/current_tab</div>
        <p>Get information about current tab</p>
        <pre>Response:
{{
  "tab_id": "unknown",
  "url": "https://example.com",
  "title": "Example",
  "is_loading": false
}}</pre>
    </div>

    <h2>Usage</h2>
    <pre>curl -X POST http://localhost:8888/api/extract \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \\
  -d '{{"action": "extract_current_tab", "strategy": "three-phase"}}'</pre>

    <h2>Setup</h2>
    <ol>
        <li>Install the Chrome Tab Reader extension</li>
        <li>Open the extension popup and copy your access token</li>
        <li>Create the tokens configuration file at:<br>
            <code>{config_path_display}</code>
            <pre>{{{{
  "tokens": ["your-token-here"],
  "note": "Get token from extension popup. You can add multiple tokens."
}}}}</pre>
        </li>
        <li>Start this server and include the token in all API requests</li>
    </ol>

    <h2>Token File Structure</h2>
    <p>The tokens.json file should contain:</p>
    <pre>{{{{
  "tokens": [
    "64-char-hex-token-from-extension-1",
    "64-char-hex-token-from-extension-2"
  ],
  "note": "Optional: Add notes or descriptions here"
}}}}</pre>
    <p><strong>TIP:</strong> Use the "Download Config File" button in the extension popup to automatically generate this file!</p>

</body>
</html>
"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(docs.encode())

    def send_json_response(self, status_code: int, data: Dict):
        """Send JSON response"""
        response_json = json.dumps(data, indent=2)
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_json)))
        self.end_headers()
        self.wfile.write(response_json.encode())

    def log_message(self, format, *args):
        """Override to use our logger instead"""
        pass  # We log in do_GET/do_POST


def run_server(port: int = 8888, host: str = "127.0.0.1"):
    """Run the HTTP server"""
    server_address = (host, port)
    httpd = HTTPServer(server_address, ChromeTabHTTPHandler)

    logger.info(f"Starting Chrome Tab Reader HTTP server on {host}:{port}")
    logger.info(f"API documentation available at http://{host}:{port}/")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server")
        httpd.shutdown()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Chrome Tab Reader - HTTP API Server",
        epilog="""
Examples:
  python chrome_tab_http_server.py                    # Start on port 8888
  python chrome_tab_http_server.py --port 9000        # Start on port 9000
  python chrome_tab_http_server.py --host 0.0.0.0     # Listen on all interfaces

Note: On macOS, this requires chrome_tab.scpt in the same directory.
        """
    )

    parser.add_argument("--port", type=int, default=8888, help="Port to listen on (default: 8888)")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")

    args = parser.parse_args()

    # Verify prerequisites
    if platform.system() == "Darwin":
        script_path = Path(__file__).parent / "chrome_tab.scpt"
        if not script_path.exists():
            logger.error(f"chrome_tab.scpt not found at {script_path}")
            logger.error("Please make sure the AppleScript file is in the same directory")
            sys.exit(1)

    run_server(port=args.port, host=args.host)


if __name__ == "__main__":
    main()
