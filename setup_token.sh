#!/bin/bash
#
# Chrome Tab Reader - Token Setup Helper
#
# This script helps you configure access tokens for the HTTP server.
#

set -e

CONFIG_DIR="$HOME/.chrome-tab-reader"
TOKENS_FILE="$CONFIG_DIR/tokens.json"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Chrome Tab Reader - Token Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Create config directory if it doesn't exist
if [ ! -d "$CONFIG_DIR" ]; then
    echo "Creating configuration directory: $CONFIG_DIR"
    mkdir -p "$CONFIG_DIR"
fi

# Check if tokens file already exists
if [ -f "$TOKENS_FILE" ]; then
    echo "⚠️  Tokens file already exists: $TOKENS_FILE"
    echo
    echo "Current tokens:"
    cat "$TOKENS_FILE"
    echo
    read -p "Do you want to add a new token? (y/N): " response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Exiting without changes."
        exit 0
    fi

    # Load existing tokens
    existing_tokens=$(cat "$TOKENS_FILE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(json.dumps(data.get('tokens', [])))")
else
    echo "No existing tokens file found. Creating new one."
    existing_tokens="[]"
fi

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Get Your Access Token"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "To get your access token:"
echo "  1. Open Chrome and install the Chrome Tab Reader extension"
echo "  2. Click the extension icon in your toolbar"
echo "  3. Copy the 'Access Token' shown at the top of the popup"
echo "  4. Paste it below"
echo
read -p "Enter your access token: " token

# Validate token (should be 64 hex characters)
if [[ ! "$token" =~ ^[0-9a-f]{64}$ ]]; then
    echo
    echo "⚠️  Warning: Token doesn't match expected format (64 hex characters)"
    echo "   Expected format: lowercase hexadecimal, 64 characters"
    echo "   Your input: $token"
    echo
    read -p "Continue anyway? (y/N): " response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Exiting without changes."
        exit 1
    fi
fi

# Add token to list
new_tokens=$(echo "$existing_tokens" | python3 -c "
import sys, json
tokens = json.load(sys.stdin)
new_token = '$token'
if new_token not in tokens:
    tokens.append(new_token)
    print('Token added successfully!')
else:
    print('Token already exists in the list.')
print(json.dumps(tokens))
")

# Extract just the tokens array from the output
added_msg=$(echo "$new_tokens" | head -1)
tokens_array=$(echo "$new_tokens" | tail -1)

# Create the full JSON structure
cat > "$TOKENS_FILE" << EOF
{
  "tokens": $tokens_array,
  "note": "Access tokens for Chrome Tab Reader HTTP server",
  "setup_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Setup Complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "$added_msg"
echo
echo "Configuration saved to: $TOKENS_FILE"
echo

# Show the file contents
echo "Current configuration:"
cat "$TOKENS_FILE"
echo

# Set secure permissions
chmod 600 "$TOKENS_FILE"
echo "✅ File permissions set to 600 (owner read/write only)"

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Next Steps"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "1. Start the HTTP server:"
echo "   python chrome_tab_http_server.py"
echo
echo "2. Test authentication:"
echo "   curl -H 'Authorization: Bearer $token' http://localhost:8888/api/health"
echo
echo "3. View API documentation:"
echo "   http://localhost:8888/"
echo
echo "For more information, see ACCESS_CONTROL_SETUP.md"
echo
