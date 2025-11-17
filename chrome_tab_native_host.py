#!/usr/bin/env python3
"""
Chrome Tab Reader - Native Messaging Host

This script acts as a bridge between the MCP server and the Chrome extension.
It implements Chrome's Native Messaging protocol for bidirectional communication.

Architecture:
- Extension connects to this host via Chrome Native Messaging (stdin/stdout)
- MCP server connects to this host via TCP (localhost)
- Host forwards requests between MCP server and extension

Protocol:
- Native Messaging: 4-byte length prefix (little-endian) + JSON message
- TCP: JSON messages terminated by newline

Authentication (Optional):
- When --require-auth is enabled, TCP clients must send "AUTH <token>" as first line
- Tokens are loaded from platform-specific config directory (same as HTTP server)
- Extension does not need auth (it connects via stdin/stdout, already trusted)

Reference: https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging
"""

import sys
import json
import struct
import logging
import socket
import threading
import os
import time
import argparse
import platform
from pathlib import Path

# Configuration
TCP_HOST = "127.0.0.1"
TCP_PORT = 8765  # Port for MCP server to connect to
LOG_DIR = Path.home() / ".chrome-tab-reader"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "native_host.log"

# Authentication configuration (populated by command-line args)
REQUIRE_AUTH = False
VALID_TOKENS = set()

# Set up logging
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Global state
extension_connected = False
pending_requests = {}  # request_id -> response_queue
request_counter = 0
request_lock = threading.Lock()


def read_message():
    """
    Read a message from stdin using Chrome Native Messaging protocol.

    Returns:
        dict: The parsed JSON message, or None if connection closed
    """
    try:
        # Read the message length (first 4 bytes)
        raw_length = sys.stdin.buffer.read(4)
        if not raw_length or len(raw_length) != 4:
            logger.info("Connection closed by Chrome")
            return None

        # Unpack the length as little-endian unsigned int
        message_length = struct.unpack('=I', raw_length)[0]
        logger.debug(f"Receiving message of length: {message_length}")

        # Read the message content
        message_bytes = sys.stdin.buffer.read(message_length)
        if len(message_bytes) != message_length:
            logger.error(f"Expected {message_length} bytes, got {len(message_bytes)}")
            return None

        # Decode and parse JSON
        message = json.loads(message_bytes.decode('utf-8'))
        logger.debug(f"Received from extension: {message}")
        return message

    except Exception as e:
        logger.error(f"Error reading message: {e}", exc_info=True)
        return None


def send_message(message):
    """
    Send a message to stdout using Chrome Native Messaging protocol.

    Args:
        message (dict): The message to send (will be JSON-encoded)
    """
    try:
        # Encode message as JSON
        encoded_message = json.dumps(message).encode('utf-8')
        message_length = len(encoded_message)

        logger.debug(f"Sending to extension, length: {message_length}")
        logger.debug(f"Message content: {message}")

        # Write the message length (4 bytes, little-endian unsigned int)
        sys.stdout.buffer.write(struct.pack('=I', message_length))

        # Write the message content
        sys.stdout.buffer.write(encoded_message)

        # Flush to ensure immediate delivery
        sys.stdout.buffer.flush()

    except Exception as e:
        logger.error(f"Error sending message: {e}", exc_info=True)


def get_config_dir() -> Path:
    """Get platform-specific config directory (same as HTTP server)."""
    try:
        import platformdirs
        return Path(platformdirs.user_config_dir("chrome-tab-reader", appauthor=False))
    except ImportError:
        system = platform.system()
        if system == "Windows":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
            return base / "chrome-tab-reader"
        elif system == "Darwin":
            return Path.home() / "Library" / "Application Support" / "chrome-tab-reader"
        else:
            # Linux: XDG Base Directory Specification
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config:
                base = Path(xdg_config)
            else:
                base = Path.home() / ".config"
            return base / "chrome-tab-reader"


def load_valid_tokens() -> set:
    """Load valid tokens from config file."""
    config_dir = get_config_dir()
    tokens_file = config_dir / "tokens.json"

    if not tokens_file.exists():
        logger.warning(f"Tokens file not found at {tokens_file}")
        return set()

    try:
        with open(tokens_file, 'r') as f:
            data = json.load(f)
            tokens = data.get("tokens", [])
            logger.info(f"Loaded {len(tokens)} valid token(s) from {tokens_file}")
            return set(tokens)
    except Exception as e:
        logger.error(f"Error loading tokens file: {e}")
        return set()


def authenticate_tcp_client(client_socket) -> bool:
    """
    Authenticate TCP client by reading AUTH line.

    Returns:
        bool: True if authenticated (or auth not required), False otherwise
    """
    if not REQUIRE_AUTH:
        return True

    try:
        # Read first line (auth line)
        auth_line = b''
        while True:
            chunk = client_socket.recv(1)
            if not chunk or chunk == b'\n':
                break
            auth_line += chunk

        auth_str = auth_line.decode('utf-8').strip()

        if not auth_str.startswith('AUTH '):
            logger.warning("TCP client did not send AUTH line")
            return False

        token = auth_str[5:]  # Remove "AUTH " prefix

        if token in VALID_TOKENS:
            logger.info("TCP client authenticated successfully")
            return True
        else:
            logger.warning("TCP client sent invalid token")
            return False

    except Exception as e:
        logger.error(f"Error during authentication: {e}", exc_info=True)
        return False


def handle_mcp_client(client_socket):
    """
    Handle a connection from the MCP server.

    Args:
        client_socket: The socket connection from MCP server
    """
    global request_counter, extension_connected

    try:
        # Authenticate client if required
        if not authenticate_tcp_client(client_socket):
            error_response = {
                "status": "error",
                "error": "Authentication required. Send 'AUTH <token>' as first line."
            }
            client_socket.sendall((json.dumps(error_response) + '\n').encode('utf-8'))
            return

        # Read request from MCP server (newline-delimited JSON)
        data = b''
        while True:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            data += chunk
            if b'\n' in data:
                break

        if not data:
            logger.warning("No data received from MCP client")
            return

        # Parse request
        request = json.loads(data.decode('utf-8').strip())
        logger.info(f"Received from MCP: {request.get('action', 'unknown')}")

        # Check if extension is connected
        if not extension_connected:
            response = {
                "status": "error",
                "error": "Extension not connected. Please open Chrome and ensure the extension is installed."
            }
            client_socket.sendall((json.dumps(response) + '\n').encode('utf-8'))
            return

        # Generate unique request ID
        with request_lock:
            request_counter += 1
            request_id = request_counter

        # Add request ID to message
        request['request_id'] = request_id

        # Create a queue for the response
        response_queue = []
        pending_requests[request_id] = response_queue

        # Forward request to extension
        send_message(request)

        # Wait for response (with timeout)
        timeout = 60  # 60 seconds
        start_time = time.time()
        while time.time() - start_time < timeout:
            if response_queue:
                response = response_queue[0]
                break
            time.sleep(0.1)
        else:
            response = {
                "status": "error",
                "error": "Timeout waiting for extension response"
            }

        # Clean up
        if request_id in pending_requests:
            del pending_requests[request_id]

        # Send response back to MCP server
        client_socket.sendall((json.dumps(response) + '\n').encode('utf-8'))

    except Exception as e:
        logger.error(f"Error handling MCP client: {e}", exc_info=True)
        error_response = {
            "status": "error",
            "error": str(e)
        }
        try:
            client_socket.sendall((json.dumps(error_response) + '\n').encode('utf-8'))
        except:
            pass
    finally:
        client_socket.close()


def socket_server_thread():
    """
    Run a TCP server to accept connections from MCP server.
    """
    global extension_connected

    # Create TCP socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind((TCP_HOST, TCP_PORT))
        server.listen(5)
        logger.info(f"TCP server listening on {TCP_HOST}:{TCP_PORT}")
    except OSError as e:
        logger.error(f"Failed to bind to {TCP_HOST}:{TCP_PORT}: {e}")
        logger.error("Is another instance already running?")
        return

    try:
        while True:
            client_socket, client_addr = server.accept()
            logger.info(f"MCP client connected from {client_addr}")

            # Handle client in a new thread
            client_thread = threading.Thread(target=handle_mcp_client, args=(client_socket,))
            client_thread.daemon = True
            client_thread.start()

    except Exception as e:
        logger.error(f"TCP server error: {e}", exc_info=True)
    finally:
        server.close()


def extension_message_loop():
    """
    Main loop: Process messages from Chrome extension.
    """
    global extension_connected

    logger.info("Extension message loop started")
    extension_connected = True

    try:
        while True:
            # Read message from extension
            message = read_message()

            if message is None:
                logger.info("Extension disconnected")
                extension_connected = False
                break

            # Check if this is a response to a pending request
            request_id = message.get('request_id')
            if request_id and request_id in pending_requests:
                # This is a response to a pending request
                logger.info(f"Received response for request {request_id}")
                pending_requests[request_id].append(message)
            else:
                # Unsolicited message from extension (e.g., notification)
                logger.info(f"Unsolicited message from extension: {message}")

    except Exception as e:
        logger.error(f"Error in extension message loop: {e}", exc_info=True)
        extension_connected = False


def main():
    """
    Main entry point: Start TCP server and extension message loop.
    """
    global REQUIRE_AUTH, VALID_TOKENS

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Chrome Tab Reader - Native Messaging Host",
        epilog="Bridges communication between Chrome extension and MCP server via TCP"
    )
    parser.add_argument(
        "--require-auth",
        action="store_true",
        help="Require authentication for TCP connections (default: disabled for backward compatibility)"
    )
    args = parser.parse_args()

    REQUIRE_AUTH = args.require_auth

    logger.info("=== Native Messaging Host Starting ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"PID: {os.getpid()}")
    logger.info(f"TCP: {TCP_HOST}:{TCP_PORT}")
    logger.info(f"Authentication: {'REQUIRED' if REQUIRE_AUTH else 'DISABLED'}")
    logger.info(f"Log file: {LOG_FILE}")

    # Load tokens if authentication is required
    if REQUIRE_AUTH:
        VALID_TOKENS = load_valid_tokens()
        if not VALID_TOKENS:
            logger.error("Authentication is required but no tokens are configured!")
            logger.error("Please add tokens to tokens.json or disable authentication")
            sys.exit(1)

    try:
        # Start TCP server in background thread
        socket_thread = threading.Thread(target=socket_server_thread)
        socket_thread.daemon = True
        socket_thread.start()

        logger.info("TCP server started, waiting for extension connection...")

        # Run extension message loop in main thread
        extension_message_loop()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
    finally:
        logger.info("=== Native Messaging Host Stopped ===")


if __name__ == "__main__":
    main()
