# Active Context

## Current Work Focus

The Lightroom Classic MCP Server is **operational and feature-complete** with 75+ MCP tools covering all major Lightroom catalog and develop operations. Current focus areas include:

1. **Architecture Stability** - New single-socket + HTTP callback architecture (merged from kmanley1/windows-compat)
2. **Catalog Enhancements** - New keyword and metadata batch tools added
3. **Documentation** - Maintaining clear API references and usage examples
4. **Windows Compatibility** - MessageProtocol backslash escaping fix applied

## Recent Changes & Implementations

### April 2026 - Socket Architecture Fix (kmanley1 contribution)

**Critical bug fixed**: The original dual-socket architecture had a fatal flaw — Lightroom's `LrSocket` in `mode="send"` has a **10-second idle timeout**. After Lightroom sent the `connection.established` event, the sender socket would go idle and Lightroom would close it. Python's `_receive_loop` would get EOF and set `_connected = False`. Commands were still sent (write socket stayed alive) but responses never arrived, causing 30-second timeouts on every call.

**Credit**: Fix implemented by **[kmanley1](https://github.com/Kmanley1/lightroom_mcp)** in his `windows-compat` branch (PR #9 on upstream). Merged into our `main` branch April 2026.

**New Architecture**:
- **OLD (broken)**: Dual TCP sockets — Python reads responses from LrSocket `mode="send"` (idle timeout kills it)
- **NEW (working)**: Single `mode="receive"` TCP socket for commands (Python → Lightroom) + HTTP POST callbacks on port 54400 for responses (Lightroom → Python). Python runs a tiny HTTP server. LrHttp.post() is wrapped in async LrTasks to avoid blocking catalog handlers.

**Port file location change**: OLD used `/tmp/lightroom_ports.txt`, NEW uses `~/lightroom_ports.txt` (home dir via `LrPathUtils.getStandardFilePath("home")`).

**Files changed in merge**:
- `SimpleSocketBridge.lua` — New single-socket + HTTP callback architecture
- `socket_bridge.py` — HTTP server on port 54400 to receive LR responses; `loop.call_soon_threadsafe` for thread safety
- `client.py` — Updated for new architecture
- `CatalogModule.lua` — Added 6 new handlers (see below); restored our robust `addPhotoKeywords`
- `catalog.py` — Clean merge: our plugin metadata tools + kmanley1's new tools
- `MessageProtocol.lua` — Backslash escaping fix for Windows file paths
- `Logger.lua` — Removed rogue WTF logger
- `PluginInit.lua` — Updated initialization

### New Catalog Tools from kmanley1 (April 2026)
- ✅ `catalog_get_keyword_photos` — Find all photos with a specific keyword (by ID or name)
- ✅ `catalog_set_photo_metadata` — Set writable metadata fields (artist, caption, copyright, etc.)
- ✅ `catalog_batch_set_metadata_by_keyword` — Stamp metadata on all photos with a keyword (dry-run support)
- ✅ `catalog_delete_keyword` — Delete a keyword from the catalog entirely (dry-run support)
- ✅ `catalog_batch_delete_keywords` — Batch delete keywords by ID list (dry-run support)
- ✅ `catalog_add_keywords` — Restored with our robust version (ErrorUtils wrapping, deduplication tracking)

Also added pagination to `catalog_get_keywords` (limit/offset/include_counts params).

### February 2026 - Plugin Metadata Discovery
- ✅ **Fixed empty metadata bug**: Added discovery tool and enhanced error messages
- ✅ `catalog_discover_plugin_metadata` - NEW! Automatically discovers all plugins and their fields for a photo
- ✅ Enhanced `catalog_get_plugin_metadata` with helpful warnings when metadata is empty
- ✅ Discovery uses Lightroom SDK's `getRawMetadata("customMetadata")` - no hardcoded plugin IDs!
- ✅ LLMs can now self-discover correct plugin IDs and field names dynamically
- ✅ Solution works with ANY plugin installation, completely user-agnostic

### January 2026 - Plugin Metadata Access
- ✅ Implemented four plugin metadata tools for accessing third-party plugin data
- ✅ `catalog_get_plugin_metadata` - Get metadata from a single photo
- ✅ `catalog_batch_get_plugin_metadata` - Efficiently query multiple photos (10-20x faster)
- ✅ `catalog_search_by_plugin_property` - Search catalog by plugin property values
- ✅ Fixed bug in batchGetMetadata: Added fallback when batch API returns nil
- ✅ Fixed bug in findPhotosWithProperty: Removed incorrect version parameter
- ✅ Successfully validated all tools with real plugin metadata

### Core Infrastructure
- ✅ Modular FastMCP server architecture with 5 main servers
- ✅ ResilientClientManager with auto-reconnection (3 retries)
- ✅ Single-socket + HTTP callback bridge (replaces broken dual-socket)
- ✅ Chunked transfer protocol for large data (>10MB)
- ✅ Structured exception hierarchy with ERROR_CODE_MAP
- ✅ Comprehensive error middleware

### MCP Tools Implemented
- ✅ **System** (4 tools): ping, status, reconnect, check_photo_selected
- ✅ **Catalog** (21 tools): Search, metadata, collections, folders, keywords, selection control, plugin metadata (4 tools including discovery), new keyword/metadata batch tools
- ✅ **Develop** (49 tools):
  - Basic adjustments (exposure, contrast, highlights, shadows, whites, blacks)
  - Advanced controls (clarity, vibrance, saturation, texture, dehaze)
  - Tone curves (get/set/modify curves, S-curve presets)
  - HSL/Color (all 8 colors × 3 properties = 24 adjustments)
  - Detail (sharpening, noise reduction)
  - Lens corrections (profile, manual, chromatic aberration)
  - Effects (vignetting, grain, split toning, color grading)
  - Calibration (camera-specific color adjustments)
  - Parameter management (get/set/reset, batch operations)
  - Helper tools (auto tone, styles, suggestions)
- ✅ **Preview** (4 tools): Generate with multiple sizes, comparison previews, batch generation
- ✅ **Histogram** (3 tools): RGB, luminance, full analysis with clipping detection

### Key Optimizations
- ✅ Batch operations provide 10-20x performance improvement
- ✅ PIL-based preview resizing (Lightroom returns full resolution)
- ✅ 100ms command delay prevents race conditions
- ✅ Automatic chunking for large preview files

## Next Steps

### Short-term Priorities
1. **Testing & Validation**
   - Comprehensive testing with various photo types
   - Edge case handling (missing photos, invalid parameters)
   - Performance benchmarking of batch operations

2. **Documentation Enhancement**
   - More example workflows in README
   - Video tutorials for installation
   - Troubleshooting guide expansion

3. **User Feedback**
   - Gather feedback from early adopters
   - Identify common pain points
   - Prioritize feature requests

### Medium-term Goals
1. **Advanced Features**
   - Masking support (AI masks, radial filters, graduated filters)
   - Collection set management
   - Smart collection creation
   - Export operations

2. **Performance Improvements**
   - Connection pooling for parallel operations
   - Preview caching mechanism
   - Lazy loading for large catalogs

3. **Integration Enhancements**
   - Additional AI agent frameworks
   - Workflow automation examples
   - Integration with photo analysis tools

### Long-term Vision
1. **Ecosystem Expansion**
   - Preset management and sharing
   - Style transfer between photos
   - Automated quality control workflows
   - Integration with cloud storage

2. **Community Building**
   - Plugin marketplace
   - Shared presets and styles
   - User-contributed workflows
   - Documentation contributions

## Active Decisions & Considerations

### Design Decisions

**1. Modular Server Architecture**
- **Decision**: Split tools into separate FastMCP servers by category
- **Rationale**: Easier maintenance, independent testing, clear organization
- **Trade-off**: Slightly more complex composition layer
- **Status**: Working well, no plans to change

**2. Single Socket + HTTP Callback Pattern**
- **Decision**: Replace broken dual-socket with single receive socket + HTTP POST callbacks
- **Rationale**: LrSocket `mode="send"` has 10-second idle timeout that kills the receive channel
- **Credit**: kmanley1's windows-compat branch (PR #9)
- **Trade-off**: Python must run HTTP server on port 54400
- **Status**: Working reliably, stable connection confirmed

**3. Photo Selection Requirement**
- **Decision**: Never auto-select photos, require explicit selection
- **Rationale**: Prevent unexpected UX behavior in Lightroom
- **Trade-off**: Users must select photos manually
- **Status**: Correct approach, maintaining this pattern

**4. Temperature/Tint Special Handling**
- **Decision**: Set Temperature and Tint individually, not in batch
- **Rationale**: Compatibility issues with batch parameter setting
- **Trade-off**: Slightly slower for these two parameters
- **Status**: Necessary workaround, acceptable performance

**5. Preview Resizing Strategy**
- **Decision**: Use PIL to resize previews, not Lightroom export
- **Rationale**: Lightroom only exports full resolution
- **Trade-off**: Additional Python dependency
- **Status**: Working efficiently, good performance

### Technical Considerations

**1. Error Handling Philosophy**
- Prefer structured exceptions over generic errors
- Always provide actionable error messages
- Include error codes for programmatic handling
- Specify severity levels (error, warning, info)

**2. Performance Philosophy**
- Batch operations are first-class features
- 100ms delay acceptable for command safety
- Chunked transfer mandatory for large data
- Auto-reconnection for resilience

**3. Documentation Philosophy**
- README for quick start and common tasks
- CLAUDE.md for AI assistant guidance
- API docs for comprehensive reference
- Memory bank for project context

## Important Patterns & Preferences

### Code Patterns

**Python MCP Tools**:
```python
@server.tool
async def tool_name(param: type) -> dict:
    """Clear description for AI agents.

    Args:
        param: Description with valid ranges

    Returns:
        Dictionary with results
    """
    result = await resilient_client_manager.execute_command(
        'lua_command_name',
        {'param': param}
    )
    return result
```

**Lua Command Handlers**:
```lua
CommandRouter.handlers['command_name'] = function(params)
    -- Validate parameters
    if not params.required_param then
        return ErrorUtils.createError("INVALID_PARAM_VALUE", "Message")
    end

    -- Execute with proper catalog access
    local result = catalog:withReadAccessDo(function()
        -- Implementation
        return data
    end)

    return {success = true, data = result}
end
```

**Error Handling**:
```python
# Python
try:
    result = await client.execute_command(cmd, params)
except PhotoNotSelectedError:
    # Provide helpful guidance
    return {"error": "Please select a photo in Lightroom"}
```

```lua
-- Lua
if not photo then
    return ErrorUtils.createError(
        "NO_PHOTO_SELECTED",
        "Please select a photo in Lightroom"
    )
end
```

### File Organization Preferences
- One tool category per file
- Related tools grouped together
- Compose at higher level (main.py)
- Clear imports and dependencies

### Naming Conventions
- **Python**: snake_case for functions/variables
- **Lua**: camelCase for functions, PascalCase for modules
- **MCP Tools**: verb_noun pattern (e.g., `adjust_exposure`, `get_metadata`)
- **Lua Commands**: Same as MCP tool names for consistency

## Learnings & Project Insights

### What Works Well
1. **Modular Architecture**: Easy to extend and maintain
2. **Resilient Client**: Auto-reconnection handles network issues gracefully
3. **Batch Operations**: Dramatic performance improvements
4. **Structured Errors**: Clear error messages guide users effectively
5. **Comprehensive Documentation**: README + CLAUDE.md + API docs cover all needs

### Challenges Overcome
1. **LrSocket Idle Timeout (Critical)**: `mode="send"` times out after 10s idle → solved by kmanley1's single-socket + HTTP callback architecture
2. **Module Caching**: Documented need to restart Lightroom
3. **Catalog Access**: Strict adherence to withReadAccessDo/withWriteAccessDo pattern
4. **Large Preview Files**: Implemented chunked transfer protocol
5. **Temperature/Tint**: Special handling for compatibility
6. **Plugin Metadata Batch API**: Implemented fallback when batchGetPropertyForPlugin returns nil
7. **Plugin Property Search**: Corrected API signature to use 2-3 params (not 4) for findPhotosWithProperty
8. **Windows Path Encoding**: Backslash escaping in MessageProtocol (kmanley1 fix)

### Lessons Learned
1. **Lightroom Constraints**: Work with them, not against them
2. **Error Messages Matter**: Clear guidance reduces support burden
3. **Performance First**: Batch operations should be default pattern
4. **Documentation Clarity**: Multiple formats serve different audiences
5. **Resilience Required**: Network issues are common, handle gracefully
6. **Use SDK Introspection**: `getRawMetadata("customMetadata")` reveals all plugin metadata without hardcoding
7. **Never Assume Plugin Installations**: Each user has different plugins, discover dynamically
8. **LrSocket `mode="send"` has idle timeout**: Never use for persistent receive channel — use LrHttp.post() callbacks instead

### Best Practices Established
1. Always validate parameters before sending to Lightroom
2. Use structured exceptions with error codes
3. Provide actionable error messages with solutions
4. Prefer batch operations over individual calls
5. Document all parameter ranges and constraints
6. Include practical examples in tool descriptions
7. Test with real photos and edge cases
8. Log important operations for debugging
9. Handle connection failures gracefully
10. Keep socket communication stateless

## Current Constraints & Limitations

### Known Limitations
1. **No Auto-selection**: Must select photos manually in Lightroom
2. **Develop Tab Required**: Most develop operations need Develop tab active
3. **Module Caching**: Lightroom restart needed to reload plugin code
4. **Temperature/Tint**: Cannot be set in batch operations
5. **Lua 5.1**: Older Lua version limits some modern features
6. **HTTP Callback Port**: Port 54400 must be free for response callbacks

### Workarounds in Place
1. **LrSocket Idle Timeout**: Single-socket + HTTP callback (kmanley1's fix)
2. **Preview Size**: PIL resizing after generation
3. **Large Transfers**: Chunked transfer protocol
4. **Connection Loss**: Auto-reconnection with retries
5. **Race Conditions**: 100ms delay between commands

## Integration Points

### External Dependencies
- **Lightroom Classic**: Must be running with plugin loaded
- **Python Packages**: fastmcp, Pillow, NumPy, httpx
- **TCP Port**: 53101 (command socket, receive mode)
- **HTTP Port**: 54400 (response callbacks from Lightroom)

### Integration Surfaces
- **MCP Protocol**: Standard interface for AI agents
- **Claude Desktop**: Configuration via JSON
- **Claude Code**: CLI integration support
- **Direct Python**: Can use lightroom_sdk directly

## Current Status Summary

**Operational Status**: ✅ Fully operational
**Test Coverage**: 🟡 Basic tests in place, needs expansion
**Documentation**: ✅ Comprehensive
**Performance**: ✅ Optimized with batch operations
**Error Handling**: ✅ Robust with clear messages
**Stability**: ✅ Stable (new architecture eliminates idle timeout bug)

**Ready for**: Production use by early adopters, feedback collection, feature requests
