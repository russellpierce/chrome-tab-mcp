# Chrome Tab Reader MCP - Design Document

## Project Overview

A Model Context Protocol (MCP) server that extracts and analyzes content from the active Google Chrome tab using a local Ollama AI server. Handles any web page content with flexible filtering capabilities and customizable analysis prompts.

## Architecture

```
┌─────────────────┐
│  Claude Code    │
│  (MCP Client)   │
└────────┬────────┘
         │ MCP Protocol
         │
┌────────▼─────────────────────┐
│  chrome_tab_mcp_server.py    │
│  (FastMCP Server)            │
│  - Tool: process_chrome_tab  │
└────┬──────────────────┬──────┘
     │                  │
     │ subprocess       │ HTTP POST
     │                  │
┌────▼──────────────┐    ┌───▼──────────────┐
│  chrome_tab.scpt  │    │  Ollama Server   │
│  (AppleScript)    │    │  (Configurable)  │
│                   │    │                  │
└────┬──────────────┘    └───┬──────────────┘
     │                 │
     │ Chrome API      │ Model Inference
     │                 │
┌────▼────────┐    ┌───▼──────────────┐
│  Chrome     │    │  Qwen3-30B       │
│  Active Tab │    │  Thinking Model  │
└─────────────┘    └──────────────────┘
```

## Components

### 1. MCP Server (`chrome_tab_mcp_server.py`)

**Technology:** Python 3.8+ with FastMCP framework

**Responsibilities:**
- Expose `process_chrome_tab` tool via MCP protocol
- Parse and validate tool parameters
- Orchestrate AppleScript execution
- Call Ollama API for AI processing
- Post-process AI responses (strip `<think>` tags)
- Error handling and user feedback

**Key Dependencies:**
- `fastmcp` - MCP server framework
- `requests` - HTTP client for Ollama
- `re` - Regex for cleaning responses
- `subprocess` - Execute AppleScript

**Configuration (Priority Order - One of Each is Required):**
1. **Command-line arguments** (highest priority):
   - `--ollama-url <url>` - **REQUIRED**: Ollama server URL
   - `--model <model_name>` - **REQUIRED**: Model name to use

2. **Environment variables** (fallback):
   - `OLLAMA_BASE_URL` - Ollama server URL (alternative to --ollama-url)
   - `OLLAMA_MODEL` - Model name to use (alternative to --model)

**Note:** Configuration is required. The server will raise a `ValueError` if both OLLAMA_BASE_URL and --ollama-url are not provided, or if both OLLAMA_MODEL and --model are not provided.

**Example Configurations:**
```bash
# Using command-line arguments (recommended)
uv run chrome_tab_mcp_server.py --ollama-url http://localhost:11434 --model llama2

# Using environment variables
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=llama2
uv run chrome_tab_mcp_server.py

# Mixed: env var + CLI arg
export OLLAMA_BASE_URL=http://192.168.1.100:11434
uv run chrome_tab_mcp_server.py --model qwen

# Remote Ollama server
uv run chrome_tab_mcp_server.py --ollama-url http://example.com:11434 --model llama2
```

### 2. AppleScript Extractor (`chrome_tab.scpt`)

**Technology:** AppleScript with shell integration

**Responsibilities:**
- Connect to Google Chrome via AppleScript API
- Extract visible text content from active tab
- Deduplicate lines (case-insensitive)
- Filter content based on keywords
- Copy result to clipboard (for user convenience)

**Supported Arguments:**
- `--no-filter`: Return full deduplicated text
- `<start> <end>`: Filter between both keywords
- `<start> --to-end`: Filter from start keyword to document end
- `--from-start <end>`: Filter from document start to end keyword

**Key Functions:**
- `getChromeTextContent()` - Extract tab text via JavaScript
- `deduplicateLines()` - Remove duplicate lines using awk
- `filterContentBetweenKeywords()` - Extract between two keywords
- `filterFromStart()` - Extract from start to keyword
- `filterToEnd()` - Extract from keyword to end
- `trimWhitespace()` - Clean whitespace from results

### 3. MCP Configuration (`chrome_tab_mcp_config.json`)

**Format:** JSON configuration for Claude Code

**Purpose:** Registers the MCP server with Claude Code

**Key Fields:**
- `command`: "uv" (uses uv package manager)
- `args`: Array containing script path and command-line arguments:
  - Path to Python script
  - `--ollama-url` with server URL (**REQUIRED**)
  - `--model` with model name (**REQUIRED**)

**Configuration Example:**
```json
{
  "mcpServers": {
    "chrome-tab-reader": {
      "command": "uv",
      "args": [
        "run",
        "/path/to/chrome_tab_mcp_server.py",
        "--ollama-url",
        "http://192.168.1.100:11434",
        "--model",
        "Qwen3-30B-A3B-Thinking:Q8_K_XL"
      ]
    }
  }
}
```

**Alternative: Environment Variables**
You can configure via environment variables instead of command-line args (both methods are supported):
```json
{
  "mcpServers": {
    "chrome-tab-reader": {
      "command": "uv",
      "args": ["run", "/path/to/chrome_tab_mcp_server.py"],
      "env": {
        "OLLAMA_BASE_URL": "http://192.168.1.100:11434",
        "OLLAMA_MODEL": "Qwen3-30B-A3B-Thinking:Q8_K_XL"
      }
    }
  }
}
```

**Note:** Configuration is required. If neither method provides `OLLAMA_BASE_URL`/`--ollama-url` or `OLLAMA_MODEL`/`--model`, the server will raise a `ValueError` on startup.

## Data Flow

### Example: Default Full Page Analysis

```
1. User calls: process_chrome_tab()
   ↓
2. MCP Server determines: No params → get full page
   ↓
3. Execute: osascript chrome_tab.scpt --no-filter
   ↓
4. AppleScript:
   - Gets Chrome active tab text
   - Deduplicates lines
   - Returns full page text
   ↓
5. MCP Server builds request:
   - System: DEFAULT_SYSTEM_PROMPT (general analysis)
   - User: <page text>
   - Model: Configured via --model or OLLAMA_MODEL env var
   - Temperature: 0
   - enable_thinking: True
   ↓
6. POST to Ollama: /v1/chat/completions
   (URL configured via --ollama-url or OLLAMA_BASE_URL env var)
   ↓
7. Ollama processes with thinking model
   - Generates <think>reasoning</think>
   - Generates final answer
   ↓
8. MCP Server receives response
   ↓
9. Strip <think> tags with regex: r'<think>.*?</think>'
   ↓
10. Return clean analysis to Claude Code
```

### Example: Custom Analysis with Filtering

```
User calls: process_chrome_tab(
    system_prompt="List main topics",
    start="Introduction",
    end="Conclusion"
)
   ↓
Execute: osascript chrome_tab.scpt Introduction Conclusion
   ↓
Filter between "Introduction" and "Conclusion"
   ↓
Build request with custom system prompt
   ↓
Call Ollama → Clean response → Return
```

## Parameter Logic Matrix

| system_prompt | start | end | osascript call | Behavior |
|--------------|-------|-----|----------------|----------|
| None | None | None | `chrome_tab.scpt --no-filter` | Full page with default analysis |
| Custom | None | None | `chrome_tab.scpt --no-filter` | Full page with custom analysis |
| Any | value | value | `chrome_tab.scpt <start> <end>` | Filter between keywords |
| Any | value | None | `chrome_tab.scpt <start> --to-end` | From keyword to end |
| Any | None | value | `chrome_tab.scpt --from-start <end>` | From start to keyword |

**Key Design Decision:** When no start/end keywords are provided, always get the full page content. The difference between default and custom modes is the `system_prompt` used for AI analysis, not the content extraction.

## API Integration

### Ollama OpenAI-Compatible API

**Endpoint:** `POST /v1/chat/completions`

**Request Format:**
```json
{
  "model": "Qwen3-30B-A3B-Thinking:Q8_K_XL",
  "messages": [
    {"role": "system", "content": "<system_prompt>"},
    {"role": "user", "content": "<tab_content>"}
  ],
  "temperature": 0,
  "stream": false,
  "enable_thinking": true
}
```

**Response Format:**
```json
{
  "choices": [
    {
      "message": {
        "content": "<think>...</think>\nFinal answer here"
      }
    }
  ]
}
```

**Why temperature=0 (hardcoded)?** For consistent, deterministic results in analysis. This is intentionally hardcoded (not configurable) to ensure users always get reproducible outputs. This is essential for reliable webpage analysis and content extraction.

**Why enable_thinking=true?** Qwen3-A3B-Thinking is a reasoning model that performs better with explicit thinking enabled.

## Design Decisions

### 1. Why FastMCP?

**Considered:**
- Raw MCP SDK
- FastMCP
- Custom implementation

**Chosen:** FastMCP

**Rationale:**
- Declarative API (decorators)
- Automatic parameter validation
- Built-in MCP protocol handling
- Less boilerplate than raw SDK
- Active development and support

### 2. Why AppleScript for Chrome?

**Considered:**
- Chrome DevTools Protocol
- Browser extensions
- AppleScript
- Selenium/WebDriver

**Chosen:** AppleScript

**Rationale:**
- No browser modification required
- Works with existing Chrome installation
- Simpler deployment (no extension install)
- Native macOS integration
- Can access visible text directly

**Trade-offs:**
- macOS only
- Requires Chrome accessibility permissions
- Slower than direct DOM access

### 3. Why Inline Script Metadata (PEP 723)?

**Format:**
```python
# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "fastmcp",
#   "requests",
# ]
# ///
```

**Rationale:**
- Works seamlessly with `uv run`
- No separate requirements.txt needed
- Self-contained executable
- Dependencies documented in-file
- Standard PEP 723 format

### 4. Why Strip `<think>` Tags?

**Problem:** Reasoning models (like Qwen3-A3B-Thinking) output internal reasoning in `<think>` tags, which isn't useful in the final response.

**Solution:** Regex post-processing

**Implementation:**
```python
re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
```

**Rationale:**
- User wants final answer, not reasoning process
- Keeps responses concise
- Simple and reliable with regex
- Preserves all non-thinking content

**Alternative considered:** Use `verbosity: "low"` parameter
- **Issue:** Not reliably supported across all Ollama models
- **Decision:** Client-side stripping is more portable

### 5. Why Default to Full Page Analysis?

**Decision:** Default to full page content extraction

**Rationale:**
- More flexible for user customization
- Can be combined with custom system prompts for specialized analysis
- Users can still apply filtering by specifying `start` and `end` parameters
- Better aligns with product as "Chrome Tab Reader" (generic tool)

## Error Handling Strategy

### Levels of Error Handling

**1. AppleScript Level (`getChromeTextContent()`):**

The function implements multi-level error detection:

| Condition | Error Message | Actionable Suggestion |
|-----------|---------------|---------------------|
| No Chrome windows open | "Chrome has no open windows. Please open Chrome and navigate to a page." | User needs to open Chrome |
| Cannot access active tab | "Unable to access Chrome's active tab. Check Chrome accessibility permissions." | Enable Chrome in System Preferences > Security & Privacy > Accessibility |
| JavaScript returns null | "JavaScript returned null/undefined. The page may not have loaded properly or tab may be a special page (e.g., PDF, blank)." | Wait for page to load or use a regular web page |
| JavaScript execution fails | "Failed to extract text from page: [specific error]" | Various JS execution issues |

**2. AppleScript Main Run Level:**

- Content retrieval errors → "Error retrieving Chrome content: [details]"
- Deduplication errors → "Error deduplicating content: [details]"
- Both errors include error codes for debugging

**3. AppleScript Helper Functions:**

- `deduplicateLines()` → Catches awk errors and reports details
- `trimWhitespace()` → Gracefully falls back to original text if sed fails
- Filtering functions → Return empty string if keywords not found

**4. Python subprocess Level:**
- Timeout (30s) → Return error message
- Non-zero exit code → Return stderr with context
- File not found → Return error with path

**5. Ollama API Level:**
- Connection error → Helpful message with URL
- Timeout (5min) → Timeout message
- HTTP errors → Include status code and response
- JSON decode error → Indicate invalid response with parsing details
- Empty response → Check for choices array

**6. MCP Tool Level:**
- All errors return `str` (not exceptions)
- User-friendly error messages with context
- Include actionable suggestions

**Rationale:**
- Errors are handled at each level to provide specific feedback
- Messages describe the problem AND suggest the solution
- Error codes are included for debugging but not primary message
- MCP tools return strings (not exceptions) for Claude Code display

## Testing Strategy

### Manual Test Cases

**1. Default Full Page Mode:**
```python
process_chrome_tab()
```
- Verify extracts full page content
- Verify uses default system prompt
- Verify returns analysis

**2. Custom Analysis:**
```python
process_chrome_tab(system_prompt="Summarize")
```
- Verify gets full page (--no-filter)
- Verify uses custom prompt

**3. Keyword Filtering:**
```python
process_chrome_tab(start="Skills", end="Experience")
```
- Verify filters between keywords
- Case-insensitive matching

**4. Partial Keywords:**
```python
process_chrome_tab(start="Contact")  # To end
process_chrome_tab(end="Education")   # From start
```

**5. Error Cases:**
- Chrome not running
- Empty tab
- Ollama server down
- Invalid keywords (not found in page)

### Unit Testing (Future Enhancement)

Recommended structure:
```
tests/
├── test_applescript.py
├── test_mcp_server.py
├── test_filtering_logic.py
└── fixtures/
    └── sample_chrome_content.txt
```

## Deployment

### Requirements

**System:**
- macOS (for AppleScript)
- Python 3.8+
- uv package manager
- Google Chrome
- Ollama server with Qwen3-30B-A3B-Thinking model

**Python Dependencies:**
- fastmcp
- requests

### Installation Steps

1. Copy files to `~/repos/chrome-tab-mcp/`
2. Update paths in `chrome_tab_mcp_config.json`
3. Add config to Claude Code settings
4. Restart Claude Code
5. Test with Chrome tab open

### Configuration Points

**For different Ollama servers (Required):**
- **Method 1 (Recommended):** Pass `--ollama-url` argument in `chrome_tab_mcp_config.json` args
- **Method 2:** Set `OLLAMA_BASE_URL` environment variable
- **Must provide at least one method above or ValueError will be raised**

**For different models (Required):**
- **Method 1 (Recommended):** Pass `--model` argument in `chrome_tab_mcp_config.json` args
- **Method 2:** Set `OLLAMA_MODEL` environment variable
- **Note:** Model must support OpenAI-compatible API
- **Must provide at least one method above or ValueError will be raised**

**For different content filtering:**
- Edit filtering logic in chrome_tab.scpt (AppleScript)

**For custom analysis prompts:**
- Set `system_prompt` parameter when calling `process_chrome_tab()` from Claude Code

## Future Enhancements

### Potential Improvements

1. **Multi-browser Support**
   - Safari, Firefox, Edge
   - Browser detection and selection

2. **Cross-platform**
   - Windows: PowerShell/COM automation
   - Linux: X11 automation or browser extensions

3. **Streaming Responses**
   - Set `stream: true` in Ollama API
   - Yield partial results as they arrive

4. **Caching**
   - Cache tab content to avoid re-extraction
   - Hash-based cache invalidation

5. **Multiple Models**
   - Allow model selection per request
   - Fallback to different models

6. **Structured Output**
   - JSON extraction from profiles
   - Schema validation

7. **Batch Processing**
   - Process multiple tabs
   - Aggregate results

8. **Configuration File**
   - YAML/TOML config for defaults
   - Per-domain settings

## Known Limitations

1. **macOS Only:** AppleScript requires macOS
2. **Chrome Only:** No support for other browsers
3. **Single Tab:** Only processes active tab
4. **Text Only:** No image or PDF processing
5. **Local Ollama:** Requires local server (no cloud API)
6. **Synchronous:** Blocks during AI processing (can be 5+ minutes)
7. **No History:** Doesn't store past analyses

## Troubleshooting

### Common Issues

**ValueError: "OLLAMA_BASE_URL must be provided"**
- Configuration is required. Must provide one of:
  - `--ollama-url` command-line argument
  - `OLLAMA_BASE_URL` environment variable
- Example: `uv run chrome_tab_mcp_server.py --ollama-url http://localhost:11434 --model llama2`

**ValueError: "OLLAMA_MODEL must be provided"**
- Configuration is required. Must provide one of:
  - `--model` command-line argument
  - `OLLAMA_MODEL` environment variable
- Example: `uv run chrome_tab_mcp_server.py --ollama-url http://localhost:11434 --model llama2`

**"Cannot connect to Ollama server"**
- Check Ollama is running: `ollama list`
- Verify URL in config or --ollama-url argument
- Test connectivity: `curl $OLLAMA_BASE_URL/v1/models` (or replace with your configured URL)

**"Chrome has no open windows. Please open Chrome and navigate to a page."**
- Chrome is not running or all windows are closed
- Solution: Open Chrome and navigate to a web page

**"Unable to access Chrome's active tab. Check Chrome accessibility permissions."**
- Chrome is running but accessibility API is not available
- Solution: Grant Chrome accessibility permissions:
  1. System Preferences → Security & Privacy
  2. Accessibility (left panel)
  3. Add or enable "Google Chrome" in the application list
  4. Restart Chrome or Claude Code

**"JavaScript returned null/undefined. The page may not have loaded properly or tab may be a special page (e.g., PDF, blank)."**
- The active tab either hasn't fully loaded or is a special page (PDF, blank tab, etc.)
- Solution:
  - Wait for the page to finish loading
  - Switch to a regular web page (not a PDF or special Chrome page)
  - Try a different tab with content

**"Failed to extract text from page: [error details]"**
- JavaScript execution failed on the page
- Solution: Check the error details and try:
  - Switching to a different tab
  - Reloading the current page
  - Checking if the page blocks JavaScript execution

**"No content retrieved from Chrome tab" (general)**
- Catch-all message when content retrieval fails
- First, check which specific error you got above
- Test manually: `osascript chrome_tab.scpt --no-filter`

**"Ollama server returned invalid JSON response"**
- Ollama server returned malformed JSON
- Check Ollama server logs for errors: `ollama logs`
- Verify Ollama is not crashing or restarting
- Try restarting Ollama server
- Ensure model is compatible with the OpenAI-compatible API
- Check for network issues if using remote Ollama server

**"Timeout waiting for AI response"**
- Qwen3-30B with thinking takes 2-5 minutes
- Increase timeout in server code
- Consider faster model for testing

**MCP server not appearing**
- Check JSON syntax in config
- Verify absolute file paths
- Restart Claude Code completely
- Check logs: `~/Library/Logs/Claude/`

## Development Notes

### Code Organization

```
chrome_tab_mcp_server.py
├── Imports
├── Configuration (env vars)
├── Constants (paths)
├── FastMCP initialization
├── @mcp.tool() decorator
│   ├── process_chrome_tab()
│   ├── Parameter parsing
│   ├── AppleScript execution
│   ├── Ollama API call
│   └── Response cleaning
└── main() entry point
```

### Key Code Sections

**Parameter Logic:**
```python
if start is None and end is None:
    if system_prompt is not None:
        cmd.append("--no-filter")
else:
    # Custom filtering
```

**Response Cleaning:**
```python
cleaned_text = re.sub(
    r'<think>.*?</think>',
    '',
    generated_text,
    flags=re.DOTALL
).strip()
```

### Adding New Features

**New Tool:** Add another `@mcp.tool()` function

**New Parameter:** Add to function signature with type hint

**New Filtering Mode:** Extend li.scpt argument parsing

**New Model:** Change `OLLAMA_MODEL` env var

## Version History

**v1.0 (2025-10-02)**
- Initial implementation
- General webpage analysis
- Flexible keyword filtering
- Qwen3-30B-A3B-Thinking integration
- FastMCP server
- Full documentation

**v1.1 (2025-11-13)**
- Removed LinkedIn-specific defaults
- Made tool fully general-purpose
- Simplified parameter logic
- Updated documentation for general use

**v1.2 (2025-11-13)**
- Added command-line argument support for Ollama server configuration
- Removed hardcoded IP address (192.168.46.79) from code and docs
- Defaults to localhost:11434 for local Ollama setup
- Support both --ollama-url and environment variables for configuration
- Updated MCP configuration examples with CLI args
- Enhanced configuration documentation

**v1.3 (2025-11-13)**
- Made OLLAMA_BASE_URL and OLLAMA_MODEL configuration mandatory
- Server raises ValueError if configuration not provided via CLI args or env vars
- Removed implicit defaults to ensure explicit configuration
- Improved error messages with helpful examples
- Updated documentation to clarify required configuration
- Enhanced type safety and configuration validation

**v1.4 (2025-11-13)**
- Added explicit JSON error handling for malformed API responses
- Added json.JSONDecodeError exception handler in Ollama API calls
- Improved error messages for invalid JSON responses
- Updated error handling documentation to include JSON parsing errors
- Enhanced troubleshooting guide with JSON error resolution steps

## Authors

- Russell (original concept and requirements)
- Claude Code (implementation and documentation)

## License

MIT (assumed - update as needed)

---

**Last Updated:** November 13, 2025
**Status:** Production Ready (v1.4)
**Next Steps:** Deploy with robust error handling and test in real-world scenarios with various Ollama server configurations
