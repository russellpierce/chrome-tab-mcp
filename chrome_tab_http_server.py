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
"""

import json
import sys
import platform
import subprocess
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from typing import Dict, Any
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[Chrome Tab Reader] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


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

    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        logger.info(f"GET {path}")

        if path == "/":
            self.send_api_docs()
        elif path == "/api/current_tab":
            self.handle_current_tab()
        elif path == "/api/health":
            self.handle_health()
        else:
            self.send_json_response(404, {"error": "Not found"})

    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

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

    def handle_extract(self, request_data: Dict):
        """Handle /api/extract endpoint"""
        strategy = request_data.get("strategy", "three-phase")
        action = request_data.get("action", "extract_current_tab")

        result = ChromeTabExtractor.extract_current_tab()
        self.send_json_response(200 if result.get("status") == "success" else 500, result)

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

    def handle_current_tab(self):
        """Handle /api/current_tab endpoint"""
        result = ChromeTabExtractor.get_current_tab_info()
        self.send_json_response(200 if result.get("status") != "error" else 500, result)

    def handle_health(self):
        """Handle /api/health endpoint"""
        response = {
            "status": "ok",
            "extension_version": "1.0.0",
            "port": 8888,
            "platform": platform.system()
        }
        self.send_json_response(200, response)

    def send_api_docs(self):
        """Send API documentation"""
        docs = """
<!DOCTYPE html>
<html>
<head>
    <title>Chrome Tab Reader API</title>
    <style>
        body { font-family: monospace; max-width: 800px; margin: 40px; }
        h1 { color: #333; }
        .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-left: 3px solid #007bff; }
        .method { font-weight: bold; color: #007bff; }
        pre { background: #f9f9f9; padding: 10px; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>Chrome Tab Reader HTTP API</h1>

    <p>Base URL: http://localhost:8888</p>

    <h2>Endpoints</h2>

    <div class="endpoint">
        <div class="method">GET /api/health</div>
        <p>Health check</p>
        <pre>{
  "status": "ok",
  "extension_version": "1.0.0",
  "port": 8888
}</pre>
    </div>

    <div class="endpoint">
        <div class="method">POST /api/extract</div>
        <p>Extract content from current tab</p>
        <pre>Request:
{
  "action": "extract_current_tab",
  "strategy": "three-phase"
}

Response:
{
  "status": "success",
  "content": "extracted text...",
  "title": "Page Title",
  "url": "https://example.com",
  "extraction_time_ms": 4500
}</pre>
    </div>

    <div class="endpoint">
        <div class="method">POST /api/navigate_and_extract</div>
        <p>Navigate to URL and extract content</p>
        <pre>Request:
{
  "action": "navigate_and_extract",
  "url": "https://example.com/page",
  "strategy": "three-phase",
  "wait_for_ms": 5000
}

Response: (same as extract)</pre>
    </div>

    <div class="endpoint">
        <div class="method">GET /api/current_tab</div>
        <p>Get information about current tab</p>
        <pre>Response:
{
  "tab_id": "unknown",
  "url": "https://example.com",
  "title": "Example",
  "is_loading": false
}</pre>
    </div>

    <h2>Usage</h2>
    <pre>curl -X POST http://localhost:8888/api/extract \\
  -H "Content-Type: application/json" \\
  -d '{"action": "extract_current_tab", "strategy": "three-phase"}'</pre>

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
