#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "fastmcp",
#   "requests",
# ]
# ///
"""Chrome Tab Reader MCP Server

A Model Context Protocol server that processes Chrome tab content using local Ollama.
Supports full page analysis or filtered content extraction with flexible keyword-based filtering.
"""

from fastmcp import FastMCP
import subprocess
import requests
import re
import os
import sys
import argparse
import json
import socket
from pathlib import Path

# Configuration - must be provided via command-line args or environment variables
# These will be validated and set in main()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
MODEL = os.getenv("OLLAMA_MODEL")

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful AI assistant. Process the attached webpage. "
    "Think about the questions someone might ask of the contents on this page and provide the answers. "
    "Certainly extract any key information that does not fit in the question and response format. "
    "Your total response must be smaller than the contents of the page you were provided."
)

# Native messaging bridge TCP configuration
BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 8765

# Initialize FastMCP server
mcp = FastMCP(
    "Chrome Tab Reader",
    instructions="""
    Processes content from the active Chrome tab using local AI analysis.

    Supports flexible content filtering:
    - Default: Full page content analysis
    - Custom system prompt: Analyze with custom instructions
    - Custom keywords: Filter specific sections (start/end parameters)

    Uses local Ollama server with Qwen3-30B-A3B-Thinking model.
    """
)


def extract_tab_content_via_extension() -> dict:
    """
    Extract content from current Chrome tab via Native Messaging bridge.

    Returns:
        dict: Response from extension with 'status', 'content', 'title', 'url', etc.
    """
    try:
        # Connect to TCP bridge
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(60)  # 60 second timeout

        try:
            sock.connect((BRIDGE_HOST, BRIDGE_PORT))
        except ConnectionRefusedError:
            return {
                "status": "error",
                "error": f"Native messaging bridge is not running on {BRIDGE_HOST}:{BRIDGE_PORT}. Please ensure:\n1. Chrome extension is installed\n2. Native messaging host is installed\n3. Chrome is running with the extension loaded"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to connect to native messaging bridge at {BRIDGE_HOST}:{BRIDGE_PORT}: {str(e)}"
            }

        # Send extraction request
        request = {
            "action": "extract_current_tab",
            "strategy": "three-phase"
        }

        request_json = json.dumps(request) + '\n'
        sock.sendall(request_json.encode('utf-8'))

        # Receive response
        response_data = b''
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response_data += chunk
            if b'\n' in response_data:
                break

        sock.close()

        if not response_data:
            return {
                "status": "error",
                "error": "No response from native messaging bridge"
            }

        # Parse response
        response = json.loads(response_data.decode('utf-8').strip())
        return response

    except socket.timeout:
        return {
            "status": "error",
            "error": "Timeout waiting for extension response (60 seconds)"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error communicating with extension: {str(e)}"
        }


@mcp.tool()
def process_chrome_tab(
    system_prompt: str | None = None
) -> str:
    """Process current Chrome tab content with AI analysis.

    Extracts and analyzes content from the active Chrome tab using the browser
    extension's sophisticated three-phase extraction (lazy-loading, DOM stability,
    Readability.js cleaning).

    Args:
        system_prompt: Optional custom prompt for AI analysis. Default prompt
            extracts key information and provides Q&A format responses about
            the page content. Custom prompts enable specialized analysis tasks.

    Returns:
        str: AI-generated analysis of the tab content. Thinking tags are automatically
            stripped from the response.

    Examples:
        process_chrome_tab()
        # → Full page analysis with default prompt

        process_chrome_tab(system_prompt="Summarize this page in 3 bullets")
        # → Custom analysis of page content

        process_chrome_tab(system_prompt="Extract all product names and prices")
        # → Specialized extraction task
    """
    # Extract content from Chrome tab via extension
    extraction_result = extract_tab_content_via_extension()

    if extraction_result.get("status") != "success":
        error_msg = extraction_result.get("error", "Unknown error during content extraction")
        return f"Error extracting tab content: {error_msg}"

    tab_content = extraction_result.get("content", "")
    if not tab_content:
        return "Error: No content retrieved from Chrome tab"

    # Use custom system prompt or default
    prompt = system_prompt if system_prompt is not None else DEFAULT_SYSTEM_PROMPT

    # Prepare API request
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": tab_content}
        ],
        "temperature": 0,
        "stream": False,
        "enable_thinking": True
    }

    # Call Ollama API
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/v1/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=300  # 5 minute timeout for thinking models
        )
        response.raise_for_status()

        data = response.json()

        if "choices" not in data or len(data["choices"]) == 0:
            return f"Error: No response from AI model. Response: {data}"

        generated_text = data["choices"][0]["message"]["content"]

        # Remove <think>...</think> tags and their content
        cleaned_text = re.sub(r'<think>.*?</think>', '', generated_text, flags=re.DOTALL).strip()

        if not cleaned_text:
            return "Error: AI generated only thinking content, no final answer"

        return cleaned_text

    except requests.exceptions.ConnectionError:
        return f"Error: Cannot connect to Ollama server at {OLLAMA_BASE_URL}. Make sure Ollama is running."
    except requests.exceptions.Timeout:
        return "Error: Timeout waiting for AI response (exceeded 5 minutes)"
    except requests.exceptions.HTTPError as e:
        error_msg = f"Error: HTTP {e.response.status_code} from Ollama server"
        if hasattr(e.response, 'text'):
            error_msg += f"\nResponse: {e.response.text}"
        return error_msg
    except json.JSONDecodeError as e:
        return (
            f"Error: Ollama server returned invalid JSON response. "
            f"This may indicate a server error or misconfiguration. "
            f"Details: {str(e)}"
        )
    except Exception as e:
        return f"Error calling Ollama API: {str(e)}"


def main():
    """Parse command-line arguments and validate configuration."""
    parser = argparse.ArgumentParser(
        description="Chrome Tab Reader MCP Server",
        epilog="Required configuration: Set --ollama-url and --model via CLI args or OLLAMA_BASE_URL and OLLAMA_MODEL env vars"
    )

    parser.add_argument(
        "--ollama-url",
        type=str,
        help="URL of the Ollama server (e.g., http://localhost:11434 or http://192.168.1.100:11434). "
             "Required: provide via CLI arg or OLLAMA_BASE_URL environment variable.",
        default=None
    )

    parser.add_argument(
        "--model",
        type=str,
        help="Name of the Ollama model to use (e.g., llama2, qwen, etc.). "
             "Required: provide via CLI arg or OLLAMA_MODEL environment variable.",
        default=None
    )

    args = parser.parse_args()

    # Apply command-line overrides to global configuration
    global OLLAMA_BASE_URL, MODEL

    if args.ollama_url:
        OLLAMA_BASE_URL = args.ollama_url

    if args.model:
        MODEL = args.model

    # Validate that configuration is provided
    if not OLLAMA_BASE_URL:
        raise ValueError(
            "OLLAMA_BASE_URL must be provided via --ollama-url argument or OLLAMA_BASE_URL environment variable. "
            "Example: uv run chrome_tab_mcp_server.py --ollama-url http://localhost:11434"
        )

    if not MODEL:
        raise ValueError(
            "OLLAMA_MODEL must be provided via --model argument or OLLAMA_MODEL environment variable. "
            "Example: uv run chrome_tab_mcp_server.py --model llama2"
        )


if __name__ == "__main__":
    main()
    mcp.run()
