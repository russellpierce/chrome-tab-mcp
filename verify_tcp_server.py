#!/usr/bin/env python3
"""
Quick verification that the native host TCP server is accessible.
This checks if the TCP server is listening without testing the full protocol.
"""

import socket
import subprocess
import time
import sys

def check_tcp_port(host='127.0.0.1', port=8765, timeout=2):
    """Check if TCP port is listening."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"Error checking port: {e}")
        return False

def main():
    print("=== TCP Server Verification ===")
    print()

    print("Starting native host...")
    proc = subprocess.Popen(
        ['python3', 'chrome_tab_native_host.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    print(f"Native host PID: {proc.pid}")
    print("Waiting 2 seconds for TCP server to bind...")
    time.sleep(2)

    # Check if process crashed
    if proc.poll() is not None:
        print(f"✗ Native host crashed (exit code: {proc.returncode})")
        stderr = proc.stderr.read().decode('utf-8')
        if stderr:
            print("\nStderr:")
            print(stderr)
        sys.exit(1)

    print("✓ Native host is running")
    print()

    # Check TCP port
    print("Checking if TCP port 8765 is accessible...")
    if check_tcp_port():
        print("✓ TCP server is listening on 127.0.0.1:8765")
        print()
        print("SUCCESS! The native host is working correctly:")
        print("  - Process starts without crashing")
        print("  - TCP server binds to port 8765")
        print("  - Port is accessible from localhost")
        print()
        print("When Chrome launches the native host:")
        print("  - It will keep stdin/stdout open")
        print("  - Extension messages will flow through the bridge")
        print("  - MCP server can connect to port 8765")
        result = 0
    else:
        print("✗ TCP server is NOT accessible on 127.0.0.1:8765")
        print()
        print("Check the log file at ~/.chrome-tab-reader/native_host.log")
        result = 1

    # Cleanup
    print()
    print("Stopping native host...")
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    sys.exit(result)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(130)
