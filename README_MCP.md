# Chrome Tab Reader MCP Server

A Model Context Protocol (MCP) server that extracts and analyzes content from the active Chrome tab using a local Ollama AI model.

## Features

- **Flexible Content Filtering**: Extract specific sections or full page content
- **Local AI Processing**: Uses Ollama with Qwen3-30B-A3B-Thinking model
- **Full Page Analysis**: Defaults to complete page extraction and intelligent Q&A generation
- **Customizable**: Override filtering keywords and analysis prompts

## Installation

### Prerequisites

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) package manager
- [Ollama](https://ollama.ai/) running locally with Qwen3-30B-A3B-Thinking model
- Google Chrome

### Setup

1. Clone or copy the files to your system:
   ```bash
   /Users/russell/repos/chrome-tab-mcp/
   ├── chrome_tab_mcp_server.py
   ├── chrome_tab.scpt
   └── chrome_tab_mcp_config.json
   ```

2. Add the MCP server to your Claude Code configuration:
   - Location: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Or: Claude Code Settings → MCP Servers

3. Copy the configuration from `chrome_tab_mcp_config.json`:
   ```json
   {
     "mcpServers": {
       "chrome-tab-reader": {
         "command": "uv",
         "args": [
           "run",
           "/Users/russell/repos/chrome-tab-mcp/chrome_tab_mcp_server.py"
         ],
         "env": {
           "OLLAMA_BASE_URL": "http://192.168.46.79:11434",
           "OLLAMA_MODEL": "Qwen3-30B-A3B-Thinking:Q8_K_XL"
         }
       }
     }
   }
   ```

4. Restart Claude Code to load the MCP server

## Usage

The server provides one tool: `process_chrome_tab`

### Parameters

- **`system_prompt`** (optional): Custom AI analysis prompt
- **`start`** (optional): Start keyword for content filtering
- **`end`** (optional): End keyword for content filtering

### Examples

#### Default Full Page Analysis
```python
process_chrome_tab()
```
Extracts full page content and analyzes with default prompt (Q&A format with key information extraction).

#### Custom Analysis with Full Page
```python
process_chrome_tab(system_prompt="Summarize the main points of this page")
```
Gets full unfiltered page content and analyzes with custom prompt.

#### Filter Between Custom Keywords
```python
process_chrome_tab(start="Skills", end="Experience")
```
Extracts content between "Skills" and "Experience" keywords.

#### From Keyword to End of Page
```python
process_chrome_tab(start="Contact Information")
```
Extracts from "Contact Information" to the end of the page.

#### From Start to Keyword
```python
process_chrome_tab(end="References")
```
Extracts from the beginning of the page to "References".

#### Custom Analysis with Custom Filtering
```python
process_chrome_tab(
    system_prompt="List all technical skills mentioned",
    start="Skills",
    end="Projects"
)
```

## Filtering Logic

| Parameters | Behavior |
|------------|----------|
| No params | Full page with default prompt |
| `system_prompt` only | Full page with custom prompt |
| `start` + `end` | Filter between keywords |
| `start` only | From keyword → end of page |
| `end` only | From start of page → keyword |
| `system_prompt` + `start`/`end` | Custom analysis with filtering |

## Configuration

### Environment Variables

Set these in the MCP config `env` section:

- **`OLLAMA_BASE_URL`**: Ollama server URL (default: `http://192.168.46.79:11434`)
- **`OLLAMA_MODEL`**: Model to use (default: `Qwen3-30B-A3B-Thinking:Q8_K_XL`)

### Default System Prompt

```
You are a helpful AI assistant. Process the attached webpage.
Think about the questions someone might ask of the contents on this page and provide the answers.
Certainly extract any key information that does not fit in the question and response format.
Your total response must be smaller than the contents of the page you were provided.
```

## How It Works

1. **Content Extraction**: AppleScript (`chrome_tab.scpt`) extracts text from active Chrome tab
2. **Filtering**: Content is filtered based on keywords or returned in full
3. **AI Processing**: Content is sent to local Ollama server with appropriate prompt
4. **Response Cleaning**: `<think>...</think>` tags are stripped from reasoning model output
5. **Return**: Clean analysis is returned to Claude Code

## AppleScript Capabilities

The `chrome_tab.scpt` script supports:

- `osascript chrome_tab.scpt` - Full page content (default)
- `osascript chrome_tab.scpt --no-filter` - Full page content (explicit)
- `osascript chrome_tab.scpt <start> <end>` - Custom keyword range
- `osascript chrome_tab.scpt <start> --to-end` - From keyword to end
- `osascript chrome_tab.scpt --from-start <end>` - From start to keyword

## Troubleshooting

### "Cannot connect to Ollama server"
- Verify Ollama is running: `ollama list`
- Check the URL in your MCP config matches your Ollama server
- Ensure the model is installed: `ollama pull Qwen3-30B-A3B-Thinking:Q8_K_XL`

### "No content retrieved from Chrome tab"
- Ensure Chrome is running with an active tab
- Check that Chrome has accessibility permissions for AppleScript
- Try manually running: `osascript chrome_tab.scpt --no-filter`

### "Timeout waiting for AI response"
- The Qwen3 thinking model can take several minutes for complex tasks
- Default timeout is 5 minutes
- Consider using a faster model for simpler tasks

### MCP server not appearing in Claude Code
- Verify the config file syntax is valid JSON
- Check file paths are absolute and correct
- Restart Claude Code completely
- Check Claude Code logs for errors

## License

MIT

## Author

Russell (with Claude Code assistance)
