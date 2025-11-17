#!/usr/bin/env python3
"""
Manual Test Script for Native Messaging

This script allows you to manually test the native messaging setup
without requiring pytest or Playwright.

Usage:
    python tests/manual_test_native_messaging.py [test_name]

Available tests:
    - protocol: Test native messaging protocol encoding/decoding
    - socket: Test Unix socket communication
    - extension: Test MCP → Extension communication (requires Chrome running)
    - all: Run all tests

Requirements:
    - Chrome with extension loaded
    - Native messaging host installed
"""

import sys
import json
import struct
import socket
import time
from pathlib import Path
import io

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_protocol():
    """Test Native Messaging protocol encoding/decoding"""
    print("\n=== Testing Native Messaging Protocol ===\n")

    # Test encoding
    print("Test 1: Message encoding")
    message = {"action": "test", "data": "hello world"}
    encoded = json.dumps(message).encode('utf-8')
    length = len(encoded)
    wire_format = struct.pack('=I', length) + encoded

    print(f"  Original message: {message}")
    print(f"  Encoded length: {length} bytes")
    print(f"  Wire format: {wire_format[:20]}... ({len(wire_format)} bytes total)")
    print("  ✓ Encoding works\n")

    # Test decoding
    print("Test 2: Message decoding")
    length_bytes = wire_format[:4]
    decoded_length = struct.unpack('=I', length_bytes)[0]
    message_bytes = wire_format[4:]
    decoded_message = json.loads(message_bytes.decode('utf-8'))

    print(f"  Decoded length: {decoded_length}")
    print(f"  Decoded message: {decoded_message}")

    assert decoded_message == message, "Decoded message doesn't match original!"
    print("  ✓ Decoding works\n")

    return True


def test_socket_communication():
    """Test TCP socket communication"""
    print("\n=== Testing TCP Socket Communication ===\n")

    test_host = "127.0.0.1"
    test_port = 19999  # Use a high port for testing

    print("Test 1: Create server socket")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((test_host, test_port))
        server.listen(1)
        server.settimeout(5)
        print(f"  Server listening on: {test_host}:{test_port}")
        print("  ✓ Server created\n")
    except OSError as e:
        print(f"  ✗ Failed to bind: {e}")
        print(f"  Port {test_port} may be in use\n")
        server.close()
        return False

    import threading

    response_received = []

    def handle_client():
        try:
            client, _ = server.accept()
            print("  Server: Client connected")

            # Receive request
            data = client.recv(4096)
            request = json.loads(data.decode('utf-8').strip())
            print(f"  Server: Received request: {request}")

            # Send response
            response = {
                "status": "success",
                "content": "Test content from server",
                "request_id": request.get("request_id")
            }
            client.sendall((json.dumps(response) + '\n').encode('utf-8'))
            print(f"  Server: Sent response")
            client.close()
        except Exception as e:
            print(f"  Server error: {e}")

    # Start server in background
    server_thread = threading.Thread(target=handle_client)
    server_thread.daemon = True
    server_thread.start()

    # Give server time to start
    time.sleep(0.2)

    print("Test 2: Client connection and communication")
    try:
        # Create client
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5)
        client.connect((test_host, test_port))
        print("  Client: Connected to server")

        # Send request
        request = {
            "action": "extract_current_tab",
            "strategy": "three-phase",
            "request_id": 42
        }
        client.sendall((json.dumps(request) + '\n').encode('utf-8'))
        print(f"  Client: Sent request: {request}")

        # Receive response
        response_data = b''
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            response_data += chunk
            if b'\n' in response_data:
                break

        response = json.loads(response_data.decode('utf-8').strip())
        print(f"  Client: Received response: {response}")

        client.close()

        # Verify
        assert response["status"] == "success", "Response status is not success!"
        assert response["request_id"] == 42, "Request ID mismatch!"
        print("  ✓ Socket communication works\n")

        return True

    except Exception as e:
        print(f"  ✗ Socket test failed: {e}\n")
        return False

    finally:
        server.close()


def test_extension_communication():
    """Test MCP → Extension communication"""
    print("\n=== Testing MCP → Extension Communication ===\n")

    bridge_host = "127.0.0.1"
    bridge_port = 8765

    print("Test 1: Check if native messaging TCP server is running")
    print(f"  Attempting to connect to {bridge_host}:{bridge_port}...")

    print("\nTest 2: Connect to native messaging bridge")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((bridge_host, bridge_port))
        print("  ✓ Connected to native host\n")

    except ConnectionRefusedError:
        print(f"  ✗ Connection refused to {bridge_host}:{bridge_port}")
        print("\n  Setup instructions:")
        print("  1. Load extension in Chrome (chrome://extensions/)")
        print("  2. Run: ./install_native_host.sh <extension-id>")
        print("  3. Open any webpage in Chrome")
        print("  4. Open extension popup to trigger connection")
        print("  5. Check native host log: tail -f ~/.chrome-tab-reader/native_host.log")
        print(f"  6. Verify TCP server is listening: lsof -i :{bridge_port}")
        return False
    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        return False

    print("Test 3: Send extraction request")
    request = {
        "action": "extract_current_tab",
        "strategy": "three-phase"
    }
    try:
        sock.sendall((json.dumps(request) + '\n').encode('utf-8'))
        print(f"  Request sent: {request}\n")
    except Exception as e:
        print(f"  ✗ Failed to send request: {e}")
        sock.close()
        return False

    print("Test 4: Receive extraction response")
    try:
        response_data = b''
        start_time = time.time()

        while time.time() - start_time < 10:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response_data += chunk
            if b'\n' in response_data:
                break

        sock.close()

        if not response_data:
            print("  ✗ No response received (timeout)")
            print("  Check if Chrome has an active tab open")
            return False

        response = json.loads(response_data.decode('utf-8').strip())
        print(f"  Response status: {response.get('status')}")

        if response.get('status') == 'success':
            content_preview = response.get('content', '')[:100]
            print(f"  Content preview: {content_preview}...")
            print(f"  Title: {response.get('title')}")
            print(f"  URL: {response.get('url')}")
            print(f"  Extraction time: {response.get('extraction_time_ms')}ms")
            print("  ✓ Extension communication works!\n")
            return True
        else:
            print(f"  ✗ Extraction failed: {response.get('error')}")
            return False

    except Exception as e:
        print(f"  ✗ Failed to receive response: {e}")
        sock.close()
        return False


def test_mcp_server_function():
    """Test the MCP server's extract function"""
    print("\n=== Testing MCP Server Function ===\n")

    try:
        from chrome_tab_mcp_server import extract_tab_content_via_extension

        print("Test 1: Call extract_tab_content_via_extension()")
        result = extract_tab_content_via_extension()

        if result.get("status") == "success":
            print(f"  ✓ Extraction successful")
            print(f"  Title: {result.get('title')}")
            print(f"  URL: {result.get('url')}")
            print(f"  Content length: {len(result.get('content', ''))} characters")
            print(f"  Extraction time: {result.get('extraction_time_ms')}ms\n")
            return True
        else:
            print(f"  ✗ Extraction failed: {result.get('error')}\n")
            return False

    except ImportError as e:
        print(f"  ✗ Could not import MCP server: {e}\n")
        return False


def main():
    """Main test runner"""
    print("="*60)
    print("Chrome Tab Reader - Native Messaging Manual Tests")
    print("="*60)

    # Parse command line argument
    test_name = sys.argv[1] if len(sys.argv) > 1 else "all"

    results = {}

    if test_name in ["protocol", "all"]:
        results["protocol"] = test_protocol()

    if test_name in ["socket", "all"]:
        results["socket"] = test_socket_communication()

    if test_name in ["extension", "all"]:
        results["extension"] = test_extension_communication()

    if test_name in ["mcp", "all"]:
        results["mcp"] = test_mcp_server_function()

    # Print summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:20s} {status}")

    print("="*60)

    # Exit with appropriate code
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
