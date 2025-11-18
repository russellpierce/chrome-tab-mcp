# HTTP API Server & Access Control Setup Guide

> **Note:** This document is AI-authored with human oversight.

> **When This Is Relevant:** This guide applies **only if you are using the HTTP API server** (`chrome_tab_http_server.py`). If you're using the browser extension with Native Messaging (the recommended cross-platform approach for MCP), you do not need the HTTP server or token-based authentication.

## Overview

The Chrome Tab Reader HTTP API server provides a REST API for programmatic access to webpage content extraction. It uses token-based authentication to secure all endpoints.

**Use Cases:**
- Custom scripts and automation
- Third-party integrations
- Direct API access without MCP
- Multi-client access with different tokens

**Components:**
- **Extension**: Generates and stores a unique access token
- **HTTP Server**: Validates tokens for all API requests
- **Scripts/MCP**: Must include the token in API requests

## Security Model

- Tokens are cryptographically random (256-bit)
- Stored securely in Chrome extension storage
- Validated on every HTTP API request
- Can be regenerated at any time
- Multiple tokens supported (for different clients)

## Setup Steps

### 1. Install the Chrome Extension

1. Navigate to `chrome://extensions/`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Select the `extension` directory from this repository
5. The extension icon will appear in your toolbar

### 2. Get Your Access Token

1. Click the Chrome Tab Reader extension icon
2. The popup will display your unique access token at the top
3. Click the "Copy" button to copy it to clipboard
4. **Keep this token secure** - it's like a password

### 3. Configure the HTTP Server

Create the tokens configuration file:

```bash
mkdir -p ~/.chrome-tab-reader
cat > ~/.chrome-tab-reader/tokens.json << 'EOF'
{
  "tokens": [
    "paste-your-token-here"
  ],
  "note": "Get token from extension popup"
}
EOF
```

Or copy the example file:

```bash
cp tokens.json.example ~/.chrome-tab-reader/tokens.json
# Then edit ~/.chrome-tab-reader/tokens.json and add your token
```

### 4. Install Python Dependencies

```bash
# Option A: Using uv (recommended)
# uv handles dependencies automatically via PEP 723 inline metadata

# Option B: Using pip
pip install -r requirements.txt
```

### 5. Start the HTTP Server

```bash
# Using uv (recommended)
uv run chrome_tab_http_server.py

# Or using Python directly
python chrome_tab_http_server.py
```

The server will:
- Load tokens from `~/.chrome-tab-reader/tokens.json`
- Bind to `http://localhost:8888` (localhost only for security)
- Provide OpenAPI documentation at `/docs` and `/redoc`

### 6. Test Authentication

Test with curl:

```bash
# This should fail (401 Unauthorized)
curl http://localhost:8888/api/health

# This should succeed
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     http://localhost:8888/api/health
```

## HTTP API Usage

### API Documentation

The HTTP server provides interactive API documentation:

- **Swagger UI:** http://localhost:8888/docs
- **ReDoc:** http://localhost:8888/redoc
- **OpenAPI Spec:** http://localhost:8888/openapi.json

### Available Endpoints

**Health Check:**
```bash
GET /api/health
```

**Get Current Tab Info:**
```bash
GET /api/current_tab
```

**Extract Content:**
```bash
POST /api/extract
{
  "action": "extract_current_tab",
  "strategy": "three-phase"
}
```

### Using Tokens in Your Scripts

**Python Example:**

```python
import requests

TOKEN = "your-token-here"  # Get from extension popup

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

response = requests.post(
    "http://localhost:8888/api/extract",
    headers=headers,
    json={"action": "extract_current_tab", "strategy": "three-phase"}
)

print(response.json())
```

### curl Example

```bash
TOKEN="your-token-here"

curl -X POST http://localhost:8888/api/extract \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "extract_current_tab", "strategy": "three-phase"}'
```

### MCP Server Configuration

If using with the MCP server, add the token to your environment or configuration:

```bash
# In your shell profile or .env file
export CHROME_TAB_READER_TOKEN="your-token-here"
```

## Token Management

### Viewing Your Current Token

1. Click the extension icon
2. Your token is displayed at the top of the popup
3. Click "Copy" to copy it

### Regenerating a Token

If you need to regenerate your token (e.g., if it was compromised):

1. Click the extension icon
2. Click "Regenerate" button
3. Confirm the action
4. Copy the new token
5. **Update the token in `~/.chrome-tab-reader/tokens.json`**
6. **Update the token in any scripts or configurations**

### Multiple Tokens

You can configure multiple tokens for different clients:

```json
{
  "tokens": [
    "extension-token-abc123",
    "script-token-def456",
    "mcp-server-token-ghi789"
  ],
  "note": "One token per client/use case"
}
```

This allows you to:
- Use different tokens for different purposes
- Revoke specific tokens without affecting others
- Track which client is making requests

## Security Best Practices

1. **Keep tokens secret**: Don't commit tokens to git, share in public channels, etc.
2. **Use environment variables**: Store tokens in env vars or secure config files
3. **Regenerate if compromised**: If a token is exposed, regenerate it immediately
4. **One token per client**: Use different tokens for different scripts/services
5. **File permissions**: Ensure `~/.chrome-tab-reader/tokens.json` has restricted permissions

```bash
chmod 600 ~/.chrome-tab-reader/tokens.json
```

## Troubleshooting

### "401 Unauthorized" Errors

- Verify token is correct (copy from extension popup)
- Check `~/.chrome-tab-reader/tokens.json` contains the token
- Ensure token is in the "tokens" array
- Restart the HTTP server after updating tokens.json
- Verify Authorization header format: `Bearer YOUR_TOKEN`

### Token Not Showing in Extension

- Refresh the extension popup
- Check browser console for errors (F12)
- Reinstall the extension if needed

### Server Not Loading Tokens

- Check file exists: `ls -la ~/.chrome-tab-reader/tokens.json`
- Verify JSON syntax: `cat ~/.chrome-tab-reader/tokens.json | python -m json.tool`
- Check server logs for error messages

## Technical Details

### Token Format

- **Length**: 64 hexadecimal characters (256 bits)
- **Generation**: `crypto.getRandomValues()` (browser's cryptographic RNG)
- **Storage**: Chrome extension local storage (encrypted by Chrome)

### Authentication Flow

```
1. Client makes API request with Authorization header
2. Server extracts token from "Bearer <token>" header
3. Server checks if token exists in VALID_TOKENS set
4. If valid: Process request
   If invalid: Return 401 Unauthorized
```

### Token Validation

The server validates tokens by:
- Extracting the Authorization header
- Checking for "Bearer " prefix
- Comparing token to set of valid tokens from config file
- Constant-time comparison (prevents timing attacks)

## API Documentation

Once the server is running, visit:

http://localhost:8888/

This displays the full API documentation with authentication examples.
