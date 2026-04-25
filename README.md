# Lightroom Classic MCP Server

Model Context Protocol (MCP) server for Adobe Lightroom Classic. Provides AI agents and LLMs with comprehensive catalog management, develop adjustments, preview generation, and histogram analysis capabilities.

## Features

- **📚 Catalog Operations** - Search photos, manage collections, extract metadata
- **🎨 Develop Tools** - 114 RAW adjustment parameters across 49 commands with batch operations
- **🖼️ Preview Generation** - JPEG thumbnails with automatic resizing and optimization
- **📊 Histogram Analysis** - RGB and luminance histograms from preview data
- **⚡ Performance** - Efficient batch operations and chunked transfers

## Quick Start

### 1. Install Plugin
**Option A - Plugin Manager (Recommended):**
1. In Lightroom: `File → Plug-in Manager`
2. Click "Add" and select `lightroom-python-bridge.lrdevplugin`

**Option B - Manual Install:**
Copy `lightroom-python-bridge.lrdevplugin` to:
- **Mac**: `~/Library/Application Support/Adobe/Lightroom/Modules/`
- **Windows**: `%APPDATA%\Adobe\Lightroom\Modules\`

### 2. Start Bridge
In Lightroom: `File → Plug-in Extras → Start Python Bridge`

### 3. Install Dependencies

**Recommended: [uv](https://docs.astral.sh/uv/) (fast Python package manager)**
```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and create virtualenv automatically
uv sync
```

**Alternative: pip**
```bash
pip install -r requirements.txt
```

### 4. Run MCP Server

**With uv (recommended):**
```bash
uv run python -m mcp_server.main
```

**With pip/virtualenv:**
```bash
python -m mcp_server.main
```

## Usage with Claude Desktop

Add to your `claude_desktop_config.json`:

**Using uv (recommended):**
```json
{
  "mcpServers": {
    "lightroom": {
      "command": "uv",
      "args": ["--directory", "/path/to/lightroom_mcp", "run", "python", "-m", "mcp_server.main"]
    }
  }
}
```

**Using system Python:**
```json
{
  "mcpServers": {
    "lightroom": {
      "command": "python",
      "args": ["-m", "mcp_server.main"],
      "cwd": "/path/to/lightroom_mcp"
    }
  }
}
```

## Usage with Claude Code

**Using uv (recommended):**
```bash
claude mcp add-json -s user lightroom '{
  "command": "uv",
  "args": ["--directory", "/path/to/lightroom_mcp", "run", "python", "-m", "mcp_server.main"]
}'
```

**Using a virtualenv Python directly:**
```bash
claude mcp add-json -s user lightroom '{
  "command": "/path/to/lightroom_mcp/venv/bin/python",
  "args": ["/path/to/lightroom_mcp/mcp_server/main.py"],
  "env": {
    "PYTHONPATH": "/path/to/lightroom_mcp"
  }
}'
```

## Usage with LM Studio

Add to your MCP configuration in LM Studio:

```json
{
  "mcpServers": {
    "lightroom": {
      "command": "uv",
      "args": ["--directory", "/path/to/lightroom_mcp", "run", "python", "-m", "mcp_server.main"]
    }
  }
}
```

> **Note**: LM Studio's MCP client does not currently pass `ImageContent` tool results to the
> LLM's vision encoder. The `preview_get_image_data` tool will return an image content block
> that LM Studio cannot display. As a workaround, use `preview_generate` instead — it saves
> the preview to disk and returns the file path, which you can open manually.

## Sample Prompts

**Basic adjustments:**
> "Select the first RAW photo and increase exposure by +0.5, add some vibrance, and reduce highlights"

**Batch processing:**
> "Find all photos from today and apply a warm tone preset: temperature +200K, tint +10, vibrance +20"

**Advanced masking:**
> "Create an AI subject mask, brighten the subject by +0.3 exposure, then create a background mask and add subtle blur"

**Tone curves:**
> "Apply a gentle S-curve to the main tone curve for more contrast, then warm up the highlights using the red channel curve"

**Preview generation:**
> "Generate a medium-sized JPEG preview of the current photo and save it as 'hero_image.jpg'"

**Visual inspection:**
> "Show me the current photo so I can evaluate the exposure"

> "Examine all the selected photos and tell me how the content differs"

**Histogram analysis:**
> "Analyze the RGB histogram of the current photo and tell me if it's properly exposed"

**Organization:**
> "Show me all photos in the 'Portraits' collection taken with a 85mm lens"

## MCP Tools Overview

**System** (4 tools): `system_ping`, `system_status`, `system_reconnect`, `system_check_photo_selected`

**Catalog** (21 tools): Photo search, metadata extraction, folder/collection management, selection control, keyword management, plugin metadata access

**Develop** (49 tools): All basic adjustments (exposure, contrast, etc.), tone curves, HSL/color, detail, lens corrections, effects, calibration, masking

**Preview** (6 tools): Generate optimized JPEGs with automatic PIL-based resizing; `preview_get_image_data` returns a proper MCP `ImageContent` block for vision-capable LLMs

**Histogram** (3 tools): RGB, luminance, and full spectrum analysis

## Requirements

- **Lightroom Classic** 12.x or newer
- **Python** 3.10+ (3.14+ recommended)
- **uv** (recommended) or pip
- **Dependencies**: FastMCP, Pillow, NumPy (see `pyproject.toml`)

## Architecture

```
[AI Agent/LLM] ↔ [MCP Server] ↔ [Lightroom Plugin] ↔ [Lightroom Classic]
```

### MCP Server Components
- **Main Server**: `mcp_server/main.py` - FastMCP composition layer
- **Modular Servers**: System, Catalog, Develop (9 modules), Preview
- **Resilient Client**: Auto-reconnection and timeout handling
- **Error Middleware**: Comprehensive error handling and validation
- **Lightroom SDK**: Type-safe Python client with structured exceptions

### Lightroom Bridge Components
- **Plugin**: `lightroom-python-bridge.lrdevplugin` - Lua-based Lightroom extension
- **Single Socket + HTTP Callback**: Single `mode="receive"` TCP socket for commands + HTTP POST callbacks on port 54400 for responses
- **Command Router**: Dynamic dispatch with 69+ registered handlers
- **Protocol**: JSON with chunked transfer for large data (>10MB)

## Key Notes

- Temperature and Tint parameters are set individually (not in batch) for compatibility
- Preview generation uses PIL for resizing since Lightroom returns full-resolution images
- Most develop operations require a photo to be selected in Lightroom and the Develop tab open
- Chunked transfer automatically handles large preview files (>10MB)
- `preview_get_image_data` returns a proper MCP `ImageContent` block — works with Claude Desktop, Continue, and other spec-compliant MCP clients

## Error Handling

The server provides comprehensive error handling with structured exceptions:

**Common Error Types:**
- `PhotoNotSelectedError` - No photo selected in Lightroom
- `ParameterOutOfRangeError` - Parameter value outside valid range
- `PhotoNotFoundError` - Photo with given ID not found
- `ConnectionError` - Socket connection issues
- `CatalogAccessError` - Failed to access Lightroom catalog

**Error Response Format:**
```json
{
  "error": {
    "code": "NO_PHOTO_SELECTED",
    "message": "Please select a photo in Lightroom",
    "severity": "error"
  }
}
```

## Troubleshooting

**Plugin Logs**: Check Lightroom plugin activity and errors:
- **Mac**: `~/Logs/Adobe/Lightroom/LrClassicLogs/LightroomPythonBridge.log`
- **Windows**: `%USERPROFILE%\Logs\Adobe\Lightroom\LrClassicLogs\LightroomPythonBridge.log`

**Common Issues**:
- Plugin not appearing: Restart Lightroom after installation
- Connection errors: Ensure bridge is started via `File → Plug-in Extras → Start Python Bridge`
- Parameter errors: Verify a photo is selected in Lightroom before develop operations
- Port conflict: Ensure ports 53101 (commands) and 54400 (HTTP callbacks) are free

## Testing

```bash
# Run Python tests
uv run python -m pytest lightroom_sdk/tests/

# Test MCP server import
uv run python -c "from mcp_server.main import main_server; print('Server loaded successfully')"
```
