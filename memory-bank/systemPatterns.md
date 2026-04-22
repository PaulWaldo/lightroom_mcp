# System Patterns

## Architecture Overview

### Three-Tier System
```
┌─────────────────┐     MCP      ┌──────────────────┐   JSON/TCP   ┌─────────────────┐
│   AI Agent/LLM  │ ◄─────────► │  FastMCP Server  │ ◄──────────► │ Lightroom Plugin│
│   (Claude, etc) │              │    (Python)       │              │      (Lua)       │
└─────────────────┘              └──────────────────┘              └─────────────────┘
                                                                             │
                                                                             ▼
                                                                    ┌─────────────────┐
                                                                    │ Lightroom Classic│
                                                                    │   Application    │
                                                                    └─────────────────┘
```

### Layer Responsibilities

**Layer 1: AI Agent/LLM**
- Interprets user natural language requests
- Selects appropriate MCP tools
- Formats parameters
- Processes responses

**Layer 2: MCP Server (Python)**
- Exposes FastMCP tools to AI agents
- Validates parameters
- Manages resilient connection to Lightroom
- Handles errors and exceptions
- Processes large data transfers (chunking)

**Layer 3: Lightroom Plugin (Lua)**
- Receives JSON-RPC commands over TCP
- Routes commands to appropriate handlers
- Interacts with Lightroom SDK
- Returns results as JSON

**Layer 4: Lightroom Classic**
- Executes actual catalog and develop operations
- Provides access to photos and metadata

## Key Technical Decisions

### 1. Single Socket + HTTP Callback Pattern
**Problem**: Lightroom's LrSocket `mode="send"` has a 10-second idle timeout. The original dual-socket architecture used a send-mode socket for Python to receive responses. After the initial `connection.established` event, the send-mode socket went idle and Lightroom closed it — causing all responses to be lost and 30-second timeouts on every command.

**Credit**: Fix implemented by **[kmanley1](https://github.com/Kmanley1/lightroom_mcp)** in PR #9 (`windows-compat` branch), merged April 2026.

**Solution**: Single `mode="receive"` TCP socket + HTTP POST callbacks
- **Command Socket** (`mode="receive"`, port ~53101): Python → Lightroom Plugin (commands only)
- **HTTP Callback Server** (port 54400): Lightroom Plugin → Python (responses via LrHttp.post)

```
Python sends command → TCP port 53101 → Lightroom receives
Lightroom processes → LrHttp.post("http://localhost:54400/response") → Python HTTP server
```

**Key Implementation Notes**:
- Python runs a ThreadingHTTPServer on port 54400
- Lightroom wraps LrHttp.post() in LrTasks.startAsyncTask() to avoid blocking catalog handlers
- Python uses `loop.call_soon_threadsafe()` to resolve futures from the HTTP server thread
- Port file: `~/lightroom_ports.txt` (home dir via LrPathUtils.getStandardFilePath("home"))

### 2. Modular FastMCP Composition
**Pattern**: Compose multiple FastMCP servers into one main server

**Structure**:
```
mcp_server/
  main.py                    # Composition layer, mounts all servers
  servers/
    system.py                # Health checks, ping, status
    catalog.py               # Photo search, metadata, collections
    preview.py               # JPEG generation, histogram analysis
    develop/                 # Development tools (11 modules)
      main.py                # Develop composition server
      basic_tools.py         # Exposure, contrast, highlights, shadows
      tone_curves.py         # Tone curve manipulation
      color_tools.py         # HSL, color grading, point colors
      detail_tools.py        # Sharpening, noise reduction
      lens_tools.py          # Lens corrections, distortion
      effects_tools.py       # Vignette, grain, split toning
      calibration_tools.py   # Camera calibration
      parameter_management.py # Get/set/reset parameters
      helper_tools.py        # Auto tone, styles, suggestions
```

**Benefits**:
- Clear separation of concerns
- Easy to add new tool categories
- Independent testing of modules
- Scalable tool organization

### 3. Resilient Client Pattern
**Problem**: Socket connections can drop, Lightroom can restart, network issues occur

**Solution**: `ResilientClientManager` wrapper with auto-reconnection
```python
class ResilientClientManager:
    async def execute_command(self, command: str, params: Dict):
        retries = 3
        for attempt in range(retries):
            try:
                return await self.client.execute_command(command, params)
            except (ConnectionError, TimeoutError):
                if attempt < retries - 1:
                    await self.reconnect()
                else:
                    raise
```

**Features**:
- Automatic reconnection on connection loss
- Configurable timeout (30 seconds default)
- Retry logic with exponential backoff
- Connection state monitoring

### 4. Chunked Transfer Protocol
**Problem**: Large preview images (>10MB) can block or timeout

**Solution**: Automatic chunking in protocol layer
```lua
-- Lightroom Plugin
if data_size > 10_000_000 then
    -- Send in chunks
    for i = 1, #data, chunk_size do
        local chunk = data:sub(i, i + chunk_size - 1)
        socket.send(chunk)
    end
else
    -- Send directly
    socket.send(data)
end
```

**Reassembly** in Python client handles reconstruction automatically.

### 5. Command Router Pattern
**Implementation**: Dynamic dispatch in Lua
```lua
-- CommandRouter.lua
CommandRouter.handlers = {
    ['catalog_get_selected_photos'] = CatalogModule.getSelectedPhotos,
    ['develop_adjust_exposure'] = DevelopModule.adjustExposure,
    ['preview_generate'] = PreviewModule.generate,
    -- ... 66+ handlers
}

function CommandRouter.route(command, params)
    local handler = CommandRouter.handlers[command]
    if handler then
        return handler(params)
    else
        return {success = false, error = {code = "UNKNOWN_COMMAND"}}
    end
end
```

**Benefits**:
- Easy to add new commands
- Centralized command registry
- Type-safe parameter validation per handler

### 6. Catalog Access Pattern
**Critical Constraint**: ALL catalog operations must wrap in access functions

```lua
-- READ operations
local result = catalog:withReadAccessDo(function()
    return catalog:getTargetPhoto()
end)

-- WRITE operations
catalog:withWriteAccessDo(function()
    photo:setRating(5)
end)
```

**Consequences**:
- Silent failures if pattern violated
- Cannot nest write operations
- Must minimize time in access blocks
- Lightroom can crash if misused

### 7. Error Mapping Pattern
**Flow**: Lightroom errors → Python exceptions → MCP errors

```python
# lightroom_sdk/exceptions.py
ERROR_CODE_MAP = {
    "NO_PHOTO_SELECTED": PhotoNotSelectedError,
    "INVALID_PARAM_VALUE": ParameterOutOfRangeError,
    "PHOTO_NOT_FOUND": PhotoNotFoundError,
    "CATALOG_ACCESS_FAILED": CatalogAccessError,
}

# mcp_server/middleware/error_handler.py
@server.error_handler
async def handle_error(error):
    if isinstance(error, PhotoNotSelectedError):
        return {"error": "Please select a photo in Lightroom", "code": "NO_PHOTO_SELECTED"}
```

**Structured Format**:
```json
{
  "success": false,
  "error": {
    "code": "NO_PHOTO_SELECTED",
    "message": "Please select a photo in Lightroom",
    "severity": "error"
  }
}
```

## Component Relationships

### MCP Server → Lightroom Plugin
```
┌─────────────────────────────────────────┐
│         FastMCP Server                   │
│  ┌─────────────────────────────────┐   │
│  │   ResilientClientManager         │   │
│  │  ┌──────────────────────────┐   │   │
│  │  │  LightroomClient          │   │   │
│  │  │  ┌────────────────────┐  │   │   │
│  │  │  │ SocketBridge        │  │   │   │
│  │  │  │  - Send Socket      │  │   │   │
│  │  │  │  - Receive Socket   │  │   │   │
│  │  │  └────────────────────┘  │   │   │
│  │  └──────────────────────────┘   │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
                    ↕ TCP JSON-RPC
┌─────────────────────────────────────────┐
│     Lightroom Plugin (Lua)               │
│  ┌─────────────────────────────────┐   │
│  │  SimpleSocketBridge              │   │
│  │  - Dual Socket Manager           │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │  CommandRouter                   │   │
│  │  - 66+ Command Handlers          │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │  Module Handlers                 │   │
│  │  - CatalogModule                 │   │
│  │  - DevelopModule                 │   │
│  │  - PreviewModule                 │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────┐
│       Lightroom Classic SDK              │
│  - LrCatalog                             │
│  - LrDevelopController                   │
│  - LrPhoto                               │
│  - LrSelection                           │
└─────────────────────────────────────────┘
```

## Critical Implementation Paths

### Path 1: Basic Develop Adjustment
```
1. AI Agent: "Increase exposure by +0.5"
2. MCP Tool: develop_adjust_exposure(value=0.5)
3. ResilientClientManager: execute_command()
4. LightroomClient: Send JSON-RPC over socket
5. Lightroom Plugin: CommandRouter receives
6. DevelopModule: adjustExposure handler
7. Check: Photo selected? Develop tab open?
8. LrDevelopController: Set Exposure2012=0.5
9. Response: {success: true, value: 0.5}
10. Return to AI Agent
```

### Path 2: Batch Operation
```
1. AI Agent: "Apply settings to 100 photos"
2. MCP Tool: develop_batch_apply_settings()
3. Single command with all photo IDs + settings
4. Lightroom Plugin: Loop through photos
5. For each: Apply settings in batch
6. Response: {success: true, applied: 100}
7. 10-20x faster than individual calls
```

### Path 3: Preview Generation
```
1. AI Agent: "Generate medium preview"
2. MCP Tool: preview_generate_current(size="medium")
3. Lightroom: Generate full-resolution JPEG
4. Data > 10MB: Automatic chunking
5. Python: Reassemble chunks
6. PIL: Resize to 1080px longest edge
7. Save to disk: preview_<timestamp>.jpg
8. Return: {file_path: "...", width: 1080}
```

### Path 4: Error Recovery
```
1. Command sent to Lightroom
2. Connection lost (network issue)
3. ConnectionError raised
4. ResilientClientManager: Retry attempt 1
5. Reconnect to Lightroom
6. Resend command
7. Success: Return result
8. Or: Retry 2 more times before failing
```

## Performance Patterns

### 1. Batch vs Individual Operations
**Individual** (slow):
```python
for photo_id in photo_ids:
    await client.execute_command('develop_adjust_exposure', {
        'photo_id': photo_id,
        'value': 0.5
    })
# Time: N × (100ms delay + command time)
```

**Batch** (fast):
```python
await client.execute_command('develop_batch_apply_settings', {
    'photo_ids': photo_ids,
    'settings': {'Exposure2012': 0.5}
})
# Time: 1 × command time (10-20x faster)
```

### 2. Preview Size Optimization
- **Small (640px)**: Quick thumbnails, histogram analysis
- **Medium (1080px)**: Default, good balance
- **Large (1440px)**: High quality preview
- **Full**: Original resolution (use sparingly)

### 3. Command Delay Pattern
```python
# In client.py line 58
await asyncio.sleep(0.1)  # 100ms delay after each command
```
**Reason**: Prevents race conditions in Lightroom's event loop

## Module Dependencies

```
main.py
├── servers/system.py → ResilientClientManager
├── servers/catalog.py → ResilientClientManager
├── servers/preview.py → ResilientClientManager, PIL, NumPy
└── servers/develop/main.py
    ├── basic_tools.py → ResilientClientManager
    ├── tone_curves.py → ResilientClientManager
    ├── color_tools.py → ResilientClientManager
    ├── detail_tools.py → ResilientClientManager
    ├── lens_tools.py → ResilientClientManager
    ├── effects_tools.py → ResilientClientManager
    ├── calibration_tools.py → ResilientClientManager
    ├── parameter_management.py → ResilientClientManager
    └── helper_tools.py → ResilientClientManager

shared/
├── base.py (BaseServer)
├── client.py (LightroomClient)
└── resilient_client.py (ResilientClientManager)

lightroom_sdk/
├── client.py → socket_bridge, protocol, exceptions
├── socket_bridge.py → protocol
├── protocol.py (JSON encoding/decoding)
└── exceptions.py (Structured errors)