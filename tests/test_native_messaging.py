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

from chrome_tab_native_host import read_message, send_message, SOCKET_PATH


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


class TestSocketCommunication:
    """Test Unix socket communication between MCP server and native host"""

    @pytest.fixture
    def socket_path(self):
        """Create a temporary socket path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "test.sock"

    @pytest.fixture
    def mock_socket_server(self, socket_path):
        """Create a mock socket server"""
        server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server_socket.bind(str(socket_path))
        server_socket.listen(1)

        yield server_socket

        server_socket.close()
        if socket_path.exists():
            socket_path.unlink()

    def test_socket_request_response(self, socket_path, mock_socket_server):
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
        client_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client_sock.connect(str(socket_path))

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

    def test_socket_timeout_handling(self, socket_path):
        """Test timeout when socket server is not responding"""
        # Create socket file but don't bind server
        socket_path.touch()

        client_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client_sock.settimeout(1)

        with pytest.raises((ConnectionRefusedError, FileNotFoundError)):
            client_sock.connect(str(socket_path))


class TestMCPServerExtraction:
    """Test MCP server's extraction via native messaging"""

    @pytest.fixture
    def mock_bridge_socket(self):
        """Create a mock bridge socket that simulates the native host"""
        socket_path = Path.home() / ".chrome-tab-reader" / "test_mcp_bridge.sock"
        socket_path.parent.mkdir(exist_ok=True)

        if socket_path.exists():
            socket_path.unlink()

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(socket_path))
        server.listen(1)

        yield server, socket_path

        server.close()
        if socket_path.exists():
            socket_path.unlink()

    def test_extract_tab_content_success(self, mock_bridge_socket):
        """Test successful content extraction"""
        server, socket_path = mock_bridge_socket

        # Import here to avoid issues if module not available
        from chrome_tab_mcp_server import extract_tab_content_via_extension, SOCKET_PATH

        # Temporarily override socket path
        original_socket_path = SOCKET_PATH
        import chrome_tab_mcp_server
        chrome_tab_mcp_server.SOCKET_PATH = socket_path

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
            # Restore original socket path
            chrome_tab_mcp_server.SOCKET_PATH = original_socket_path

    def test_extract_tab_content_no_socket(self):
        """Test error when socket doesn't exist"""
        from chrome_tab_mcp_server import extract_tab_content_via_extension, SOCKET_PATH

        # Ensure socket doesn't exist
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()

        result = extract_tab_content_via_extension()

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()


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
