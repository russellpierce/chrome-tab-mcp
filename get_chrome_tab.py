#!/usr/bin/env python3
"""
Chrome Tab Reader - Command Line Tool

Simple CLI tool to extract content from the current Chrome tab.
Uses Chrome DevTools Protocol for direct tab access.

Usage:
    python get_chrome_tab.py                    # Get current tab content
    python get_chrome_tab.py --title            # Get just the title
    python get_chrome_tab.py --url              # Get just the URL
    python get_chrome_tab.py --info             # Get tab info (title, url)
"""

import json
import subprocess
import sys
import socket
import time
from pathlib import Path
from typing import Dict, Any, Optional
import argparse


class ChromeTabReader:
    """
    Reads content from Chrome tabs using various methods.

    Methods:
    1. Chrome DevTools Protocol (CDP) - requires Chrome with remote debugging
    2. Extension Native Messaging - requires extension setup
    """

    def __init__(self, port: int = 9222):
        """Initialize with Chrome DevTools Protocol port"""
        self.port = port
        self.base_url = f"http://localhost:{port}"

    def get_chrome_version_and_path(self) -> Optional[str]:
        """Get Chrome executable path"""
        import platform
        system = platform.system()

        if system == "Darwin":  # macOS
            chrome_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            ]
        elif system == "Windows":
            chrome_paths = [
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Program Files\\Chromium\\Application\\chrome.exe",
                "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
            ]
        elif system == "Linux":
            chrome_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                "/snap/bin/chromium",
            ]
        else:
            return None

        for path in chrome_paths:
            if Path(path).exists():
                return path
        return None

    def is_port_open(self) -> bool:
        """Check if Chrome debugging port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', self.port))
            sock.close()
            return result == 0
        except:
            return False

    def start_chrome_with_debugging(self) -> bool:
        """Start Chrome with remote debugging enabled"""
        chrome_path = self.get_chrome_version_and_path()
        if not chrome_path:
            print("Error: Chrome not found on this system", file=sys.stderr)
            return False

        # Check if Chrome is already running with debugging
        if self.is_port_open():
            print(f"Chrome debugging port {self.port} already open")
            return True

        print(f"Starting Chrome with remote debugging on port {self.port}...")
        try:
            # Start Chrome with remote debugging
            if sys.platform == "win32":
                subprocess.Popen([
                    chrome_path,
                    f"--remote-debugging-port={self.port}",
                    "--new-window"
                ])
            else:
                subprocess.Popen([
                    chrome_path,
                    f"--remote-debugging-port={self.port}",
                    "--new-window"
                ])

            # Wait for port to open
            for i in range(30):
                if self.is_port_open():
                    print("Chrome debugging port opened successfully")
                    return True
                time.sleep(0.5)

            print("Timeout waiting for Chrome debugging port", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Error starting Chrome: {e}", file=sys.stderr)
            return False

    def get_current_tab_via_cdp(self) -> Dict[str, Any]:
        """Get current tab content via Chrome DevTools Protocol"""
        import urllib.request
        import urllib.error

        try:
            # Ensure Chrome debugging is available
            if not self.is_port_open():
                print("Chrome debugging port not open. Please start Chrome with --remote-debugging-port=9222",
                      file=sys.stderr)
                return {
                    "status": "error",
                    "error": "Chrome DevTools Protocol not available. Please start Chrome with --remote-debugging-port=9222"
                }

            # Get list of tabs
            url = f"{self.base_url}/json"
            try:
                with urllib.request.urlopen(url, timeout=5) as response:
                    tabs = json.loads(response.read().decode())
            except urllib.error.URLError as e:
                return {
                    "status": "error",
                    "error": f"Failed to connect to Chrome: {e}"
                }

            if not tabs:
                return {
                    "status": "error",
                    "error": "No tabs found"
                }

            # Get the first page tab (skip extensions/other types)
            tab = next((t for t in tabs if t.get("type") == "page"), None)
            if not tab:
                tab = tabs[0]

            return {
                "status": "success",
                "tab_id": tab.get("id"),
                "title": tab.get("title"),
                "url": tab.get("url"),
                "tab_data": tab
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Error getting tab via CDP: {str(e)}"
            }

    def get_current_tab_via_applescript(self) -> Dict[str, Any]:
        """Get current tab via AppleScript (macOS only)"""
        import platform

        if platform.system() != "Darwin":
            return {
                "status": "error",
                "error": "AppleScript method only available on macOS"
            }

        try:
            # Run the AppleScript to get Chrome tab content
            result = subprocess.run(
                ["osascript", "chrome_tab.scpt"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return {
                    "status": "error",
                    "error": f"AppleScript error: {result.stderr}"
                }

            # Parse the JSON response
            try:
                data = json.loads(result.stdout)
                return data
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "error": f"Invalid JSON response from AppleScript: {result.stdout[:200]}"
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "AppleScript execution timeout"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"AppleScript error: {str(e)}"
            }

    def extract_current_tab(self) -> Dict[str, Any]:
        """
        Extract current tab content.
        Tries methods in order of preference:
        1. AppleScript (macOS, fastest)
        2. Chrome DevTools Protocol (cross-platform)
        """
        import platform

        # Try AppleScript on macOS first (if available)
        if platform.system() == "Darwin":
            print("[*] Trying AppleScript method (macOS)...", file=sys.stderr)
            result = self.get_current_tab_via_applescript()
            if result.get("status") == "success":
                return result
            print(f"[!] AppleScript failed: {result.get('error')}", file=sys.stderr)

        # Fall back to CDP
        print("[*] Trying Chrome DevTools Protocol method...", file=sys.stderr)
        return self.get_current_tab_via_cdp()

    def print_result(self, result: Dict[str, Any], format: str = "json"):
        """Print result in specified format"""
        if format == "json":
            print(json.dumps(result, indent=2))
        elif format == "text":
            if result.get("status") == "success":
                content = result.get("content", "")
                title = result.get("title", "")
                url = result.get("url", "")

                if title:
                    print(f"Title: {title}")
                if url:
                    print(f"URL: {url}")
                if content:
                    print(f"\nContent:\n{content}")
            else:
                print(f"Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
        elif format == "plain":
            if result.get("status") == "success":
                print(result.get("content", ""))
            else:
                print(f"Error: {result.get('error')}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Chrome Tab Reader - Extract content from current Chrome tab",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python get_chrome_tab.py                    # Get current tab content (JSON)
  python get_chrome_tab.py --plain            # Get plain text content only
  python get_chrome_tab.py --title            # Get just the title
  python get_chrome_tab.py --url              # Get just the URL
  python get_chrome_tab.py --info             # Get tab info (title, url)
  python get_chrome_tab.py --cdp-port 9222    # Use custom debugging port

Requirements:
  - Chrome/Chromium running with --remote-debugging-port=9222
  - OR on macOS with extension installed for AppleScript method
        """
    )

    parser.add_argument("--title", action="store_true", help="Output only the title")
    parser.add_argument("--url", action="store_true", help="Output only the URL")
    parser.add_argument("--info", action="store_true", help="Output tab info (title, url)")
    parser.add_argument("--plain", action="store_true", help="Output plain text content only")
    parser.add_argument("--json", action="store_true", help="Output as JSON (default)", default=True)
    parser.add_argument("--cdp-port", type=int, default=9222, help="Chrome DevTools Protocol port")
    parser.add_argument("--start-chrome", action="store_true", help="Attempt to start Chrome if not running")

    args = parser.parse_args()

    reader = ChromeTabReader(port=args.cdp_port)

    # Optionally start Chrome
    if args.start_chrome and not reader.is_port_open():
        reader.start_chrome_with_debugging()

    # Get tab content
    result = reader.extract_current_tab()

    # Handle special output formats
    if args.title and result.get("status") == "success":
        print(result.get("title", ""))
    elif args.url and result.get("status") == "success":
        print(result.get("url", ""))
    elif args.info and result.get("status") == "success":
        print(f"{result.get('title', '')} - {result.get('url', '')}")
    elif args.plain:
        reader.print_result(result, format="plain")
    else:
        reader.print_result(result, format="json")

    # Exit with error code if failed
    if result.get("status") != "success":
        sys.exit(1)


if __name__ == "__main__":
    main()
