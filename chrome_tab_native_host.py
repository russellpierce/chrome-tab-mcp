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

# Emergency logging to stderr FIRST before any imports that might fail
import sys
import datetime

def emergency_log(msg):
    """Log to stderr immediately, bypassing all logging infrastructure"""
    try:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] EMERGENCY: {msg}", file=sys.stderr, flush=True)
    except (BrokenPipeError, OSError):
        # stderr is closed or broken - this is OK, just skip emergency logging
        pass

emergency_log("Native host starting...")
emergency_log(f"Python version: {sys.version}")
emergency_log(f"sys.executable: {sys.executable}")

try:
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
    emergency_log("All imports successful")
except Exception as e:
    emergency_log(f"FATAL: Import failed: {e}")
    sys.exit(1)

# Configuration
TCP_HOST = "127.0.0.1"
TCP_PORT = 8765  # Port for MCP server to connect to

try:
    LOG_DIR = Path.home() / ".chrome-tab-reader"
    emergency_log(f"Log directory: {LOG_DIR}")
    LOG_DIR.mkdir(exist_ok=True)
    emergency_log("Log directory created/verified")
    LOG_FILE = LOG_DIR / "native_host.log"
    emergency_log(f"Log file: {LOG_FILE}")
except Exception as e:
    emergency_log(f"FATAL: Failed to create log directory: {e}")
    # Fall back to /tmp or current directory
    LOG_FILE = Path("/tmp/chrome_tab_native_host.log") if os.path.exists("/tmp") else Path("native_host.log")
    emergency_log(f"Using fallback log file: {LOG_FILE}")

# Authentication configuration (populated by command-line args)
REQUIRE_AUTH = False
VALID_TOKENS = set()

# Set up dual logging (file + stderr for Chrome to capture)
try:
    emergency_log("Setting up logging infrastructure...")

    class DualHandler(logging.Handler):
        """Log to both file and stderr with UTF-8 encoding"""
        def __init__(self, filename):
            super().__init__()
            self.file_handler = logging.FileHandler(filename, encoding='utf-8')
            self.stream_handler = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
            self.file_handler.setFormatter(formatter)
            self.stream_handler.setFormatter(formatter)

            # Reconfigure stderr to use UTF-8 encoding (fixes Windows cp1252 encoding issues)
            if hasattr(sys.stderr, 'reconfigure'):
                sys.stderr.reconfigure(encoding='utf-8')
            elif hasattr(sys.stderr, 'buffer'):
                import io
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)

        def emit(self, record):
            try:
                self.file_handler.emit(record)
                self.stream_handler.emit(record)
                # Flush immediately to ensure logs appear
                self.file_handler.flush()
                self.stream_handler.flush()
            except Exception as e:
                emergency_log(f"Logging error: {e}")

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(DualHandler(str(LOG_FILE)))
    logger.propagate = False
    emergency_log("Logging infrastructure ready")
    logger.info("=== Logger initialized successfully ===")
except Exception as e:
    emergency_log(f"FATAL: Failed to set up logging: {e}")
    sys.exit(1)

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

        # Warn about unusually large messages
        mb_32 = 32 * 1024 * 1024
        if message_length > mb_32:
            size_mb = message_length / (1024 * 1024)
            logger.warning(f"Receiving very large message: {size_mb:.1f} MB ({message_length} bytes)")

        # Read the message content in chunks to bypass Python's 32 MB read limit
        message_bytes = b''
        remaining = message_length
        chunk_size = 1024 * 1024  # 1 MB chunks
        mb_32_threshold = 32 * 1024 * 1024

        while remaining > 0:
            to_read = min(chunk_size, remaining)
            chunk = sys.stdin.buffer.read(to_read)
            if not chunk:
                logger.error(f"Connection closed while reading message (got {len(message_bytes)}/{message_length} bytes)")
                return None
            message_bytes += chunk
            remaining -= len(chunk)

            # Debug logging for large messages (after first 32 MB)
            bytes_read = len(message_bytes)
            if bytes_read > mb_32_threshold and bytes_read % chunk_size == 0:
                # Log first 1000 bytes of each MB after 32 MB
                mb_count = bytes_read // (1024 * 1024)
                sample_start = bytes_read - chunk_size
                sample_end = min(sample_start + 1000, bytes_read)
                sample = message_bytes[sample_start:sample_end]
                try:
                    sample_preview = sample.decode('utf-8', errors='replace')[:200]
                except:
                    sample_preview = repr(sample[:200])
                logger.warning(f"Large message: {mb_count} MB read. Sample from MB {mb_count}: {sample_preview}")

        if len(message_bytes) != message_length:
            logger.error(f"Expected {message_length} bytes, got {len(message_bytes)}")
            return None

        # Decode and parse JSON
        message = json.loads(message_bytes.decode('utf-8'))
        logger.debug(f"Received from extension: {message}")
        return message

    except ValueError as e:
        logger.error(f"Error reading message: {e}")
        return None
    except Exception:
        logger.exception("Unexpected error reading message")
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

    Keeps connection open and handles multiple requests until client disconnects.

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

        logger.info("MCP client authenticated and ready for requests")

        # Handle multiple requests on the same connection
        request_count = 0
        while True:
            # Read request from MCP server (newline-delimited JSON)
            data = b''
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    # Client disconnected
                    logger.info(f"MCP client disconnected after {request_count} request(s)")
                    return
                data += chunk
                # Find first newline (JSON should have escaped newlines in strings)
                if b'\n' in data:
                    # Extract first complete message
                    newline_pos = data.index(b'\n')
                    message_data = data[:newline_pos]
                    # Keep any remaining data for next message (shouldn't happen in practice)
                    remaining = data[newline_pos + 1:]
                    if remaining:
                        logger.warning(f"Received extra data after message: {len(remaining)} bytes")
                    break

            if not data:
                logger.info(f"MCP client closed connection after {request_count} request(s)")
                return

            request_count += 1

            # Parse request
            try:
                request = json.loads(message_data.decode('utf-8'))
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from MCP client: {e}")
                error_response = {
                    "status": "error",
                    "error": f"Invalid JSON: {str(e)}"
                }
                client_socket.sendall((json.dumps(error_response) + '\n').encode('utf-8'))
                continue

            logger.info(f"Request #{request_count} from MCP: {request.get('action', 'unknown')}")

            # Check if extension is connected
            if not extension_connected:
                response = {
                    "status": "error",
                    "error": "Extension not connected. Please open Chrome and ensure the extension is installed."
                }
                client_socket.sendall((json.dumps(response) + '\n').encode('utf-8'))
                continue

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
            try:
                client_socket.sendall((json.dumps(response) + '\n').encode('utf-8'))
                logger.debug(f"Response sent for request #{request_count}")
            except (OSError, socket.error) as e:
                logger.error(f"Failed to send response: {e}")
                return

            # Continue to next request (keep connection open)

    except Exception as e:
        logger.error(f"Error handling MCP client: {e}", exc_info=True)
        error_response = {
            "status": "error",
            "error": str(e)
        }
        try:
            client_socket.sendall((json.dumps(error_response) + '\n').encode('utf-8'))
        except (OSError, socket.error):
            # Expected error when client disconnects before receiving error response
            pass
    finally:
        try:
            client_socket.close()
        except (OSError, socket.error):
            # Ignore close errors (socket may already be closed)
            pass
        logger.info("MCP client handler exiting")


def socket_server_thread():
    """
    Run a TCP server to accept connections from MCP server.
    If port is already in use, exits gracefully (another instance has the server).
    """
    global extension_connected

    emergency_log("Starting TCP server thread...")

    # Create TCP socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind((TCP_HOST, TCP_PORT))
        server.listen(5)
        logger.info(f"✓ TCP server listening on {TCP_HOST}:{TCP_PORT}")
        emergency_log(f"TCP server bound successfully to {TCP_HOST}:{TCP_PORT}")
    except OSError as e:
        if e.errno == 98 or "Address already in use" in str(e):  # errno 98 = Address already in use
            logger.info(f"TCP port {TCP_PORT} already in use - another native host instance is handling TCP")
            emergency_log(f"TCP port {TCP_PORT} already in use - this is OK, another instance has the server")
            return
        else:
            logger.error(f"Failed to bind to {TCP_HOST}:{TCP_PORT}: {e}")
            emergency_log(f"FATAL: Failed to bind TCP server: {e}")
            return

    try:
        while True:
            logger.debug("Waiting for MCP client connection...")
            client_socket, client_addr = server.accept()
            logger.info(f"✓ MCP client connected from {client_addr}")

            # Handle client in a new thread
            client_thread = threading.Thread(target=handle_mcp_client, args=(client_socket,))
            client_thread.daemon = True
            client_thread.start()

    except Exception as e:
        logger.error(f"TCP server error: {e}", exc_info=True)
        emergency_log(f"TCP server crashed: {e}")
    finally:
        server.close()
        logger.info("TCP server shut down")


def extension_message_loop():
    """
    Main loop: Process messages from Chrome extension.
    Exits when Chrome disconnects (Chrome will launch a new instance if needed).
    """
    global extension_connected

    logger.info("✓ Extension message loop started")
    emergency_log("Extension message loop started, waiting for messages...")
    extension_connected = True

    try:
        message_count = 0
        while True:
            # Read message from extension
            logger.debug("Waiting for next message from Chrome...")
            message = read_message()

            if message is None:
                logger.info("Chrome extension disconnected")
                emergency_log("Chrome disconnected - native host will exit")
                extension_connected = False
                break

            message_count += 1
            logger.info(f"✓ Message #{message_count} from extension: {message.get('action', 'unknown')}")

            # Check if this is a response to a pending request
            request_id = message.get('request_id')
            if request_id and request_id in pending_requests:
                logger.info(f"✓ Matched response to request {request_id}")
                pending_requests[request_id].append(message)
            else:
                logger.warning(f"Received unsolicited message (no pending request): {message}")

    except Exception as e:
        logger.error(f"Error in extension message loop: {e}", exc_info=True)
        emergency_log(f"Extension message loop crashed: {e}")
        extension_connected = False


def main():
    """
    Main entry point: Start TCP server and extension message loop.
    """
    global REQUIRE_AUTH, VALID_TOKENS

    try:
        emergency_log("main() function started")

        # Parse command-line arguments
        emergency_log("Parsing command-line arguments...")
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
        emergency_log(f"Arguments parsed: require_auth={args.require_auth}")

        REQUIRE_AUTH = args.require_auth

        logger.info("=== Native Messaging Host Starting ===")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"PID: {os.getpid()}")
        logger.info(f"TCP: {TCP_HOST}:{TCP_PORT}")
        logger.info(f"Authentication: {'REQUIRED' if REQUIRE_AUTH else 'DISABLED'}")
        logger.info(f"Log file: {LOG_FILE}")
        emergency_log(f"Main initialization complete, PID={os.getpid()}")

        # Load tokens if authentication is required
        if REQUIRE_AUTH:
            emergency_log("Loading authentication tokens...")
            VALID_TOKENS = load_valid_tokens()
            if not VALID_TOKENS:
                logger.error("Authentication is required but no tokens are configured!")
                emergency_log("FATAL: No tokens configured but auth is required")
                logger.error("Please add tokens to tokens.json or disable authentication")
                sys.exit(1)
            logger.info(f"Loaded {len(VALID_TOKENS)} authentication token(s)")

        try:
            # Start TCP server in background thread
            emergency_log("Starting TCP server thread...")
            socket_thread = threading.Thread(target=socket_server_thread, name="TCPServer")
            socket_thread.daemon = True
            socket_thread.start()
            logger.info("✓ TCP server thread started")
            emergency_log("TCP server thread launched")

            # Give TCP server a moment to bind
            time.sleep(0.5)

            # Run extension message loop in main thread
            emergency_log("Starting extension message loop...")
            extension_message_loop()
            emergency_log("Extension message loop exited normally")

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            emergency_log("Interrupted by user (Ctrl+C)")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
            emergency_log(f"FATAL: Main loop crashed: {e}")
            raise
        finally:
            logger.info("=== Native Messaging Host Stopped ===")
            emergency_log("Native host shutting down")

    except Exception as e:
        emergency_log(f"FATAL: Uncaught exception in main(): {e}")
        import traceback
        emergency_log(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    emergency_log("Script __main__ executing")
    try:
        main()
    except Exception as e:
        emergency_log(f"FATAL: Exception escaped main(): {e}")
        import traceback
        emergency_log(traceback.format_exc())
        sys.exit(1)
    emergency_log("Script exiting normally")
