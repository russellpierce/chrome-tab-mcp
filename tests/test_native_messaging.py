"""
Chrome Tab Reader - Test Suite for Native Messaging

Tests the Native Messaging integration without requiring Claude Code.
Tests can be run locally with a real Chrome installation.

Test Levels:
1. Unit tests: Native messaging protocol implementation
2. Integration tests: Socket communication
3. E2E tests: Full flow with Chrome + Extension (using Playwright)

Requirements:
- pytest
- playwright (for E2E tests)
- Chrome browser with extension loaded
"""

import pytest
import json
import struct
import socket
import subprocess
import time
import threading
from pathlib import Path
import tempfile
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from chrome_tab_native_host import read_message, send_message, TCP_HOST, TCP_PORT


@pytest.mark.unit
class TestNativeMessagingProtocol:
    """Test the Chrome Native Messaging protocol implementation"""

    def test_message_encoding(self, capsys):
        """Test that messages are encoded correctly"""
        message = {"action": "test", "data": "hello"}

        # Redirect stdout to capture binary output
        import io
        old_stdout = sys.stdout.buffer
        sys.stdout.buffer = io.BytesIO()

        try:
            send_message(message)

            # Get the output
            sys.stdout.buffer.seek(0)
            output = sys.stdout.buffer.read()

            # Check length prefix (4 bytes, little-endian)
            length = struct.unpack('=I', output[:4])[0]

            # Check message content
            message_bytes = output[4:]
            assert len(message_bytes) == length

            decoded = json.loads(message_bytes.decode('utf-8'))
            assert decoded == message

        finally:
            sys.stdout.buffer = old_stdout

    def test_message_decoding(self):
        """Test that messages are decoded correctly"""
        message = {"action": "test", "status": "success"}
        encoded = json.dumps(message).encode('utf-8')
        length = len(encoded)

        # Create properly formatted input
        import io
        input_data = struct.pack('=I', length) + encoded

        # Redirect stdin
        old_stdin = sys.stdin.buffer
        sys.stdin.buffer = io.BytesIO(input_data)

        try:
            decoded = read_message()
            assert decoded == message
        finally:
            sys.stdin.buffer = old_stdin

    def test_empty_message_handling(self):
        """Test handling of connection close (empty input)"""
        import io
        old_stdin = sys.stdin.buffer
        sys.stdin.buffer = io.BytesIO(b'')

        try:
            result = read_message()
            assert result is None  # Should return None on connection close
        finally:
            sys.stdin.buffer = old_stdin


@pytest.mark.unit
class TestSocketCommunication:
    """Test TCP socket communication between MCP server and native host"""

    @pytest.fixture
    def tcp_port(self):
        """Provide a test TCP port"""
        return 19998  # Use a high port for testing

    @pytest.fixture
    def mock_socket_server(self, tcp_port):
        """Create a mock TCP socket server"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("127.0.0.1", tcp_port))
        server_socket.listen(1)

        yield server_socket

        server_socket.close()

    def test_socket_request_response(self, tcp_port, mock_socket_server):
        """Test sending request and receiving response via socket"""

        def server_handler():
            client_sock, _ = mock_socket_server.accept()

            # Receive request
            data = client_sock.recv(4096)
            request = json.loads(data.decode('utf-8').strip())

            # Send response
            response = {
                "status": "success",
                "content": "test content",
                "request_id": request.get("request_id")
            }
            client_sock.sendall((json.dumps(response) + '\n').encode('utf-8'))
            client_sock.close()

        # Start server in background
        server_thread = threading.Thread(target=server_handler)
        server_thread.daemon = True
        server_thread.start()

        # Give server time to start
        time.sleep(0.1)

        # Client: Connect and send request
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.connect(("127.0.0.1", tcp_port))

        request = {
            "action": "extract_current_tab",
            "strategy": "three-phase",
            "request_id": 1
        }
        client_sock.sendall((json.dumps(request) + '\n').encode('utf-8'))

        # Receive response
        response_data = b''
        while True:
            chunk = client_sock.recv(4096)
            if not chunk:
                break
            response_data += chunk
            if b'\n' in response_data:
                break

        client_sock.close()

        # Verify response
        response = json.loads(response_data.decode('utf-8').strip())
        assert response["status"] == "success"
        assert response["content"] == "test content"
        assert response["request_id"] == 1

    def test_socket_timeout_handling(self, tcp_port):
        """Test timeout when TCP server is not responding"""
        # Try to connect to a port with no server

        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.settimeout(1)

        with pytest.raises(ConnectionRefusedError):
            client_sock.connect(("127.0.0.1", tcp_port))


@pytest.mark.unit
class TestMCPServerExtraction:
    """Test MCP server's extraction via native messaging"""

    @pytest.fixture
    def mock_bridge_socket(self):
        """Create a mock TCP bridge that simulates the native host"""
        test_port = 19997  # Use a high port for testing

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", test_port))
        server.listen(1)

        yield server, test_port

        server.close()

    def test_extract_tab_content_success(self, mock_bridge_socket):
        """Test successful content extraction"""
        server, test_port = mock_bridge_socket

        # Import here to avoid issues if module not available
        from chrome_tab_mcp_server import extract_tab_content_via_extension, BRIDGE_HOST, BRIDGE_PORT

        # Temporarily override TCP settings
        original_port = BRIDGE_PORT
        import chrome_tab_mcp_server
        chrome_tab_mcp_server.BRIDGE_PORT = test_port

        def mock_extension_response():
            client, _ = server.accept()

            # Receive request
            data = client.recv(4096)
            request = json.loads(data.decode('utf-8').strip())

            # Send mock extraction result
            response = {
                "status": "success",
                "content": "This is the extracted page content",
                "title": "Test Page",
                "url": "https://example.com",
                "extraction_time_ms": 1234
            }
            client.sendall((json.dumps(response) + '\n').encode('utf-8'))
            client.close()

        # Start mock extension in background
        thread = threading.Thread(target=mock_extension_response)
        thread.daemon = True
        thread.start()

        # Give thread time to start
        time.sleep(0.1)

        try:
            # Test extraction
            result = extract_tab_content_via_extension()

            assert result["status"] == "success"
            assert result["content"] == "This is the extracted page content"
            assert result["title"] == "Test Page"
            assert result["url"] == "https://example.com"
        finally:
            # Restore original port
            chrome_tab_mcp_server.BRIDGE_PORT = original_port

    def test_extract_tab_content_no_connection(self):
        """Test error when TCP server is not running"""
        from chrome_tab_mcp_server import extract_tab_content_via_extension

        # Use a port that won't have a server
        import chrome_tab_mcp_server
        original_port = chrome_tab_mcp_server.BRIDGE_PORT
        chrome_tab_mcp_server.BRIDGE_PORT = 19996  # Unused port

        try:
            result = extract_tab_content_via_extension()

            assert result["status"] == "error"
            assert "not running" in result["error"].lower() or "refused" in result["error"].lower()
        finally:
            chrome_tab_mcp_server.BRIDGE_PORT = original_port


# Pytest configuration
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test (requires Chrome + Extension)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires native host)"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
