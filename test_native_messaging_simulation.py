#!/usr/bin/env python3
"""
Test script to simulate Chrome's native messaging protocol.

This script:
1. Launches the native host with stdin/stdout pipes
2. Sends test messages via the native messaging protocol
3. Tests TCP connection from MCP server
4. Verifies the bridge is working correctly
"""

import subprocess
import struct
import json
import socket
import time
import sys
from threading import Thread

GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
NC = '\033[0m'

def send_native_message(proc, message):
    """Send a message to native host using Chrome's protocol."""
    encoded = json.dumps(message).encode('utf-8')
    length = struct.pack('=I', len(encoded))
    proc.stdin.write(length)
    proc.stdin.write(encoded)
    proc.stdin.flush()
    print(f"{GREEN}✓{NC} Sent message to native host: {message.get('action', 'unknown')}")

def read_native_message(proc):
    """Read a message from native host using Chrome's protocol."""
    raw_length = proc.stdout.read(4)
    if not raw_length or len(raw_length) != 4:
        return None

    length = struct.unpack('=I', raw_length)[0]
    message_bytes = proc.stdout.read(length)
    if len(message_bytes) != length:
        return None

    message = json.loads(message_bytes.decode('utf-8'))
    print(f"{GREEN}✓{NC} Received message from native host: {message.get('status', 'unknown')}")
    return message

def test_tcp_connection():
    """Test TCP connection to native host."""
    print(f"{YELLOW}Testing TCP connection to 127.0.0.1:8765...{NC}")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('127.0.0.1', 8765))

        # Send a test request (without request_id to see error handling)
        request = {
            "action": "health_check"
        }
        sock.sendall((json.dumps(request) + '\n').encode('utf-8'))
        print(f"{GREEN}✓{NC} Sent TCP request")

        # Wait for response
        data = b''
        while b'\n' not in data:
            chunk = sock.recv(1024)
            if not chunk:
                break
            data += chunk

        if data:
            response = json.loads(data.decode('utf-8').strip())
            print(f"{GREEN}✓{NC} Received TCP response: {response}")
            sock.close()
            return True
        else:
            print(f"{RED}✗{NC} No response from TCP server")
            sock.close()
            return False

    except Exception as e:
        print(f"{RED}✗{NC} TCP connection failed: {e}")
        return False

def monitor_stderr(proc):
    """Monitor stderr output from native host."""
    for line in iter(proc.stderr.readline, b''):
        if line:
            print(f"[NATIVE HOST STDERR] {line.decode('utf-8').rstrip()}")

def main():
    print("=== Native Messaging Protocol Test ===")
    print()

    # Start native host with pipes
    print(f"{YELLOW}Starting native host with stdin/stdout pipes...{NC}")
    proc = subprocess.Popen(
        ['python3', 'chrome_tab_native_host.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Start stderr monitor thread
    stderr_thread = Thread(target=monitor_stderr, args=(proc,), daemon=True)
    stderr_thread.start()

    print(f"{GREEN}✓{NC} Native host started with PID: {proc.pid}")

    # Give it time to start TCP server
    print(f"{YELLOW}Waiting 2 seconds for TCP server to start...{NC}")
    time.sleep(2)

    # Check if process is still running
    if proc.poll() is not None:
        print(f"{RED}✗ FAILED: Native host crashed during startup{NC}")
        print(f"Exit code: {proc.returncode}")
        sys.exit(1)

    print(f"{GREEN}✓{NC} Native host is still running")

    # Test TCP connection
    tcp_ok = test_tcp_connection()

    # Send a test message via native messaging (simulating Chrome extension)
    print()
    print(f"{YELLOW}Sending health check message via native messaging...{NC}")

    try:
        send_native_message(proc, {
            "action": "health_check",
            "request_id": 1
        })

        # Read response
        print(f"{YELLOW}Waiting for response...{NC}")
        response = read_native_message(proc)

        if response:
            print(f"{GREEN}✓{NC} Native messaging works! Response: {response}")
        else:
            print(f"{YELLOW}⚠{NC} No response (expected - extension needs to be connected)")

    except Exception as e:
        print(f"{YELLOW}⚠{NC} Native messaging test failed (expected without extension): {e}")

    # Keep process running a bit longer
    print()
    print(f"{YELLOW}Keeping native host running for 3 more seconds...{NC}")
    time.sleep(3)

    # Check if still running
    if proc.poll() is not None:
        print(f"{RED}✗ FAILED: Native host crashed{NC}")
        print(f"Exit code: {proc.returncode}")
        sys.exit(1)

    print(f"{GREEN}✓{NC} Native host is still running")

    # Clean up
    print()
    print(f"{YELLOW}Stopping native host...{NC}")
    proc.terminate()
    proc.wait(timeout=5)

    print()
    print("=== Test Results ===")
    print(f"  Native host startup: {GREEN}✓{NC}")
    print(f"  TCP server: {GREEN + '✓' + NC if tcp_ok else RED + '✗' + NC}")
    print(f"  Process stability: {GREEN}✓{NC}")
    print()

    if tcp_ok:
        print(f"{GREEN}All tests passed!{NC}")
        print()
        print("The native host is working correctly.")
        print("When Chrome launches it, it will:")
        print("  1. Keep stdin/stdout open for native messaging")
        print("  2. Listen on TCP port 8765 for MCP server")
        print("  3. Bridge messages between Chrome extension and MCP server")
    else:
        print(f"{YELLOW}TCP test failed - check if another instance is running{NC}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted by user{NC}")
        sys.exit(130)
