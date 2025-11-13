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
│  (AppleScript)    │    │  192.168.46.79   │
│                   │    │  Port 11434      │
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

**Configuration (via environment variables):**
- `OLLAMA_BASE_URL` - Ollama server URL
- `OLLAMA_MODEL` - Model name to use

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
- `args`: Path to Python script
- `env`: Environment variables for configuration

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
   - Model: Qwen3-30B-A3B-Thinking:Q8_K_XL
   - Temperature: 0
   - enable_thinking: True
   ↓
6. POST to Ollama: http://192.168.46.79:11434/v1/chat/completions
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

**Why temperature=0?** For consistent, deterministic results in profile analysis.

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

## Error Handling Strategy

### Levels of Error Handling

**1. AppleScript Level:**
- Chrome not running → AppleScript error
- No active tab → AppleScript error
- Empty content → Return empty string

**2. Python subprocess Level:**
- Timeout (30s) → Return error message
- Non-zero exit code → Return stderr
- File not found → Return error with path

**3. Ollama API Level:**
- Connection error → Helpful message with URL
- Timeout (5min) → Timeout message
- HTTP errors → Include status code and response
- Empty response → Check for choices array

**4. MCP Tool Level:**
- All errors return `str` (not exceptions)
- User-friendly error messages
- Include actionable information

**Rationale:** MCP tools should return string results, not raise exceptions. Claude Code displays these to users, so they should be readable and actionable.

## Testing Strategy

### Manual Test Cases

**1. Default Full Page Analysis:**
```python
process_chrome_tab()
```
- Verify gets full page content
- Verify uses default system prompt
- Verify returns analysis

**2. Custom Full Page:**
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

**For different Ollama servers:**
- Edit `OLLAMA_BASE_URL` in config env

**For different models:**
- Edit `OLLAMA_MODEL` in config env
- Note: Model must support OpenAI-compatible API

**For different default keywords:**
- Edit filtering logic in chrome_tab.scpt

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

**"Cannot connect to Ollama server"**
- Check Ollama is running: `ollama list`
- Verify URL in config
- Test with: `curl http://192.168.46.79:11434/v1/models`

**"No content retrieved from Chrome tab"**
- Ensure Chrome is running
- Check active tab has content
- Grant Chrome accessibility permissions
- Test manually: `osascript chrome_tab.scpt --no-filter`

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

## Authors

- Russell (original concept and requirements)
- Claude Code (implementation and documentation)

## License

MIT (assumed - update as needed)

---

**Last Updated:** November 13, 2025
**Status:** Production Ready (v1.1)
**Next Steps:** Deploy and test in real-world scenarios
