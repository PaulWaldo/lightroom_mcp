# Tech Context

## Technology Stack

### Python Stack (MCP Server)
- **Python**: 3.8+ required
- **FastMCP**: MCP server framework for tool composition
- **Pillow (PIL)**: Image processing and resizing for previews
- **NumPy**: Histogram calculation and array operations
- **asyncio**: Async/await patterns for non-blocking operations

### Lua Stack (Lightroom Plugin)
- **Lua 5.1**: Embedded in Lightroom Classic
- **Lightroom SDK**: Built-in APIs for catalog and development
- **LrSocket**: TCP socket communication (with limitations)
- **LrTasks**: Asynchronous task management

### Development Tools
- **uv**: Python package manager (optional)
- **pytest**: Testing framework
- **Git**: Version control

## Project Structure

```
lightroom_mcp/
├── mcp_server/                  # MCP Server (Python)
│   ├── main.py                  # Main composition server
│   ├── servers/                 # Individual server modules
│   │   ├── system.py
│   │   ├── catalog.py
│   │   ├── preview.py
│   │   └── develop/             # 11 develop modules
│   ├── middleware/
│   │   └── error_handler.py     # Exception handling
│   └── shared/
│       ├── base.py              # BaseServer class
│       ├── client.py            # LightroomClient
│       └── resilient_client.py  # Auto-reconnection
│
├── lightroom_sdk/               # Lightroom SDK Client
│   ├── client.py                # Main client class
│   ├── socket_bridge.py         # Dual socket manager
│   ├── protocol.py              # JSON-RPC protocol
│   ├── exceptions.py            # Structured errors
│   └── types/                   # Type definitions
│       ├── catalog.py
│       └── develop.py
│
├── lightroom-python-bridge.lrdevplugin/  # Lightroom Plugin (Lua)
│   ├── Info.lua                 # Plugin metadata
│   ├── PluginInit.lua           # Startup logic
│   ├── SimpleSocketBridge.lua   # Socket management
│   ├── CommandRouter.lua        # Command dispatch
│   ├── CatalogModule.lua        # Catalog operations
│   ├── DevelopModule.lua        # Develop operations
│   ├── PreviewModule.lua        # Preview generation
│   ├── PluginMetadataModule.lua # Third-party plugin metadata
│   ├── MessageProtocol.lua      # JSON encoding/decoding
│   ├── ErrorUtils.lua           # Validation & errors
│   └── Logger.lua               # Logging system
│
├── docs/
│   ├── API_REFERENCE.md         # Complete API documentation
│   └── API_DEVELOP_REFERENCE.md # Develop parameters reference
│
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Project metadata
├── README.md                   # Main documentation
├── CLAUDE.md                   # Claude-specific guidance
└── memory-bank/                # Memory bank (this directory)
```

## Development Setup

### Prerequisites
1. **Lightroom Classic 12.x or newer** installed
2. **Python 3.8+** installed
3. **pip** or **uv** for package management

### Installation Steps

**1. Install Python Dependencies**:
```bash
# Using pip
pip install -r requirements.txt

# Using uv (faster)
uv pip install -r requirements.txt

# With virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

**2. Install Lightroom Plugin**:
```bash
# Option A: Via Lightroom UI
# 1. Open Lightroom Classic
# 2. File → Plug-in Manager
# 3. Click "Add"
# 4. Select lightroom-python-bridge.lrdevplugin

# Option B: Manual Copy
# Mac:
cp -r lightroom-python-bridge.lrdevplugin ~/Library/Application\ Support/Adobe/Lightroom/Modules/

# Windows:
copy lightroom-python-bridge.lrdevplugin %APPDATA%\Adobe\Lightroom\Modules\
```

**3. Start Bridge in Lightroom**:
```
File → Plug-in Extras → Start Python Bridge
```

**4. Run MCP Server**:
```bash
# As module (recommended)
python -m mcp_server.main

# Direct execution
python mcp_server/main.py

# With virtual environment
./venv/bin/python -m mcp_server.main
```

### Claude Desktop Configuration

Add to `claude_desktop_config.json`:
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

**Claude Code CLI**:
```bash
claude mcp add-json -s user Lightroom '{
    "command": "/path/to/venv/bin/python",
    "args": ["/path/to/lightroom_mcp/mcp_server/main.py"],
    "env": {
      "PYTHONPATH": "/path/to/lightroom_mcp"
    }
  }'
```

## Dependencies Detail

### Python Requirements (requirements.txt)
```
fastmcp>=0.1.0      # MCP server framework
Pillow>=10.0.0      # Image processing
numpy>=1.24.0       # Numerical operations
```

### Critical Python Versions
- **Minimum**: Python 3.8 (asyncio improvements)
- **Recommended**: Python 3.10+ (better type hints)
- **Tested**: Python 3.8, 3.9, 3.10, 3.11, 3.12

## Technical Constraints

### Lightroom Constraints

**1. Socket Limitations**:
```lua
-- LrSocket is unidirectional
local send_socket = LrSocket.bind({
    port = 53100,
    mode = 'send'  -- Can only send, not receive
})

local recv_socket = LrSocket.bind({
    port = 53101,
    mode = 'receive'  -- Can only receive, not send
})
```

**2. Module Caching**:
- Lua modules cached by Lightroom on first load
- Must restart Lightroom to reload plugin code changes
- Use `_G.LightroomPythonBridge` for shared state

**3. Catalog Access**:
```lua
-- REQUIRED pattern for all catalog operations
catalog:withReadAccessDo(function()
    -- Read operations only
end)

catalog:withWriteAccessDo(function()
    -- Write operations only
    -- Cannot nest another withWriteAccessDo
end)
```

**4. Develop Module Requirements**:
- Photo must be selected in Lightroom
- Develop tab must be active (for most operations)
- Returns `NO_PHOTO_SELECTED` error if violated

**5. Temperature/Tint Compatibility**:
- Must be set individually (not in batch)
- Special handling required for these parameters

### Python Constraints

**1. Async Operations**:
```python
# All client operations are async
await client.connect()
await client.execute_command('command', params)
```

**2. Socket Timeout**:
- Default: 30 seconds per operation
- Configurable in ResilientClientManager
- Large preview generation may take longer

**3. Command Delay**:
```python
# In client.py:58
await asyncio.sleep(0.1)  # 100ms between commands
```
- Required to prevent race conditions
- Adds 100ms overhead per command
- Use batch operations to minimize impact

**4. Memory Management**:
- Large preview files (>10MB) use chunked transfer
- Automatic reassembly in protocol layer
- PIL resizing reduces memory footprint

## Testing

### Python Tests
```bash
# Run all tests
python -m pytest lightroom_sdk/tests/

# Run specific test file
python -m pytest lightroom_sdk/tests/test_client.py

# With verbose output
python -m pytest -v lightroom_sdk/tests/

# With coverage
python -m pytest --cov=lightroom_sdk lightroom_sdk/tests/
```

### Manual Testing
```python
# Test server loading
python -c "from mcp_server.main import main_server; print('Server loaded')"

# Test client connection
python -c "
from lightroom_sdk.client import LightroomClient
import asyncio
async def test():
    client = LightroomClient()
    await client.connect()
    result = await client.ping()
    print('Connected:', result)
asyncio.run(test())
"
```

### Lightroom Plugin Testing
1. Check plugin logs:
   - **Mac**: `~/Library/Logs/Adobe/Lightroom/LrClassicLogs/LightroomPythonBridge.log`
   - **Windows**: `%USERPROFILE%\Logs\Adobe\Lightroom\LrClassicLogs\LightroomPythonBridge.log`

2. Add debug logging in Lua:
```lua
logger:info("Debug message here")
```

3. Restart Lightroom to reload plugin code

## Debugging

### Python Debugging
```python
# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Trace command execution
from lightroom_sdk.client import LightroomClient
client = LightroomClient()
client.debug = True  # Enable debug output
```

### Common Issues

**1. Connection Refused**:
- Ensure Lightroom bridge is started
- Check ports 53100/53101 are not in use
- Verify firewall settings

**2. No Photo Selected Error**:
- Select a photo in Lightroom first
- Some operations require Develop tab to be active
- Check error message for specific requirements

**3. Timeout Errors**:
- Large operations may exceed 30s timeout
- Increase timeout in ResilientClientManager
- Use batch operations for multiple photos

**4. Parameter Out of Range**:
- Check valid ranges in API_DEVELOP_REFERENCE.md
- Use `develop_get_range` tool to verify ranges
- Some ranges vary by photo/camera

**5. Plugin Not Loading**:
- Restart Lightroom after plugin installation
- Check Info.lua has correct version
- Verify plugin folder is in correct location

## Performance Considerations

### Optimization Strategies

**1. Use Batch Operations**:
```python
# Bad: N × 100ms delay
for photo_id in photo_ids:
    await client.execute_command('develop_adjust_exposure', {
        'photo_id': photo_id,
        'value': 0.5
    })

# Good: 1 × command time
await client.execute_command('develop_batch_apply_settings', {
    'photo_ids': photo_ids,
    'settings': {'Exposure2012': 0.5}
})
```

**2. Optimize Preview Sizes**:
- Use "small" (640px) for histogram analysis
- Use "medium" (1080px) for general preview
- Avoid "full" unless absolutely necessary

**3. Minimize Socket Round-trips**:
- Combine multiple parameters in single command
- Use `develop_set_parameters` instead of individual tools

**4. Connection Management**:
- ResilientClientManager maintains persistent connection
- Auto-reconnection on failure
- 3 retry attempts before giving up

## Tool Usage Patterns

### Lightroom SDK Access
```python
# Import client
from lightroom_sdk.client import LightroomClient

# Connect
client = LightroomClient()
await client.connect()

# Execute command
result = await client.execute_command('catalog_get_selected_photos')

# Close
await client.close()
```

### MCP Server Extension
```python
# Add new tool to existing server
from mcp_server.shared.base import BaseServer

@server.tool
async def my_new_tool(param: str) -> dict:
    """Tool description for AI agents."""
    result = await resilient_client_manager.execute_command(
        'my_lua_command',
        {'param': param}
    )
    return result
```

### Lua Handler Addition
```lua
-- In CommandRouter.lua
CommandRouter.handlers['my_lua_command'] = function(params)
    -- Implementation
    return {success = true, data = result}
end

-- Or register in PluginInit.lua
CommandRouter.registerCommand("my_lua_command", MyModule.myFunction, "sync")
