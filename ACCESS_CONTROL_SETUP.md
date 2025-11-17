# Access Control Setup Guide

> **⚠️ Important:** This guide is **only for the HTTP API server**. If you're using Native Messaging with the MCP server, **you do not need tokens** - Native Messaging uses Chrome's built-in manifest-based security instead.

The Chrome Tab Reader HTTP API uses token-based authentication to secure communication between clients and the HTTP server.

## Overview

- **Tokens**: Must be manually generated (cryptographically random)
- **HTTP Server**: Validates tokens for all API requests
- **Scripts/MCP**: Must include the token in API requests when using HTTP API

## Security Model

- Tokens are cryptographically random (256-bit)
- Stored securely in Chrome extension storage
- Validated on every HTTP API request
- Can be regenerated at any time
- Multiple tokens supported (for different clients)

## Setup Steps

### 1. Generate an Access Token

Since the extension no longer generates tokens, you need to create your own secure random token:

```bash
# Generate a 256-bit random token (Linux/macOS)
python3 -c "import secrets; print(secrets.token_hex(32))"

# Or use openssl
openssl rand -hex 32
```

**Keep this token secure** - it's like a password.

### 2. Configure the HTTP Server

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

### 3. Start the HTTP Server

```bash
python chrome_tab_http_server.py
```

The server will load tokens from `~/.chrome-tab-reader/tokens.json`

### 4. Test Authentication

Test with curl:

```bash
# This should fail (401 Unauthorized)
curl http://localhost:8888/api/health

# This should succeed
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     http://localhost:8888/api/health
```

## Using Tokens in Your Scripts

### Python Example

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

### Regenerating a Token

If you need to regenerate your token (e.g., if it was compromised):

1. Generate a new token using the same method as before:
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
2. **Update the token in `~/.chrome-tab-reader/tokens.json`**
3. **Update the token in any scripts or configurations**
4. **Restart the HTTP server**

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

- Verify token is correct (check your secure storage where you saved it)
- Check `~/.chrome-tab-reader/tokens.json` contains the token
- Ensure token is in the "tokens" array
- Restart the HTTP server after updating tokens.json
- Verify Authorization header format: `Bearer YOUR_TOKEN`

### Server Not Loading Tokens

- Check file exists: `ls -la ~/.chrome-tab-reader/tokens.json`
- Verify JSON syntax: `cat ~/.chrome-tab-reader/tokens.json | python -m json.tool`
- Check server logs for error messages

## Technical Details

### Token Format

- **Length**: 64 hexadecimal characters (256 bits)
- **Generation**: `secrets.token_hex(32)` or `openssl rand -hex 32`
- **Storage**: Stored in `~/.chrome-tab-reader/tokens.json`

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
