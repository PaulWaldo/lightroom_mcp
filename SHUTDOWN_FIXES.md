# Lightroom Plugin Shutdown Performance Fixes

## Problem Summary
Plugin was taking 10-28 seconds to shutdown when Lightroom exits, causing poor user experience.

## Root Causes Identified
1. Cleanup task sleeping for 10 seconds with no early exit
2. Socket restart triggered during shutdown (2-second delay)
3. No shutdown notification sent to Python client before closing sockets
4. Main loop checking shutdown flag only every 500ms
5. StopMenuAction waiting 2 seconds for verification
6. Socket `onClosed` handlers triggering restarts during shutdown

## Fixes Applied

### Fix #1: Interruptible Cleanup Task
**File**: `CommandRouter.lua:468-486`

**Change**: Split 10-second sleep into 20x 0.5-second increments with shutdown checks

**Before**:
```lua
while _G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning do
    self:_cleanupExpiredRequests()
    LrTasks.sleep(10)  -- Check every 10 seconds
end
```

**After**:
```lua
while _G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning do
    self:_cleanupExpiredRequests()
    -- Sleep in small increments for faster shutdown response
    -- 20 x 0.5s = 10 seconds total, but can exit within 500ms during shutdown
    for i = 1, 20 do
        if not (_G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning) then
            break
        end
        LrTasks.sleep(0.5)
    end
end
```

**Impact**: Reduces shutdown delay from 10 seconds to maximum 500ms (avg 250ms)

---

### Fix #2: Prevent Restart During Shutdown (Triple-Check)
**File**: `SimpleSocketBridge.lua:322-370`

**Change**: Added three shutdown checks in restart function

**Before**:
```lua
restartSocketServer = function()
    if isRestarting then
        return
    end
    if not (_G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning) then
        return
    end
    isRestarting = true
    LrTasks.startAsyncTask(function()
        -- Reset state
        LrTasks.sleep(2)
        startSocketServer()
        isRestarting = false
    end)
end
```

**After**:
```lua
restartSocketServer = function()
    -- FIRST CHECK: Before spawning async task
    if not (_G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning) then
        logger:info("Shutdown in progress - not restarting socket server")
        return
    end

    if isRestarting then
        return
    end

    isRestarting = true
    LrTasks.startAsyncTask(function()
        -- SECOND CHECK: Inside async task
        if not (_G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning) then
            isRestarting = false
            return
        end

        -- Reset state
        LrTasks.sleep(2)

        -- THIRD CHECK: After sleep
        if not (_G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning) then
            isRestarting = false
            return
        end

        startSocketServer()
        isRestarting = false
    end)
end
```

**Impact**: Prevents 2-second restart task from running during shutdown

---

### Fix #2b: Guard Socket onClosed Handlers
**File**: `SimpleSocketBridge.lua:201-209, 273-281`

**Change**: Prevent restart when sockets close during shutdown

**Before**:
```lua
onClosed = function(socket)
    logger:info("Sender socket closed - client disconnected")
    restartSocketServer()
end,
```

**After**:
```lua
onClosed = function(socket)
    logger:info("Sender socket closed - client disconnected")
    -- Don't restart if shutting down
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning then
        restartSocketServer()
    else
        logger:info("Socket closed during shutdown - not restarting")
    end
end,
```

**Impact**: Prevents restart task spawn when sockets naturally close during shutdown

---

### Fix #3: Shutdown Notification to Python Client
**File**: `SimpleSocketBridge.lua:392-400`

**Change**: Send shutdown event to Python client before closing sockets

**Before**:
```lua
local function stopSocketServer()
    if _G.LightroomPythonBridge then
        _G.LightroomPythonBridge.socketServerRunning = false
    end
    -- Immediately proceed to cleanup
end
```

**After**:
```lua
local function stopSocketServer()
    if _G.LightroomPythonBridge then
        _G.LightroomPythonBridge.socketServerRunning = false
    end

    -- Send shutdown notification to Python client before closing sockets
    if commandRouter and commandRouter.socketBridge then
        logger:info("Sending shutdown notification to Python client")
        pcall(function()
            commandRouter:sendEvent("server.shutdown", { reason = "Lightroom closing" })
        end)
        -- Give Python client 500ms to disconnect gracefully
        LrTasks.sleep(0.5)
    end

    -- Continue with cleanup
end
```

**Impact**: Allows Python client to disconnect gracefully, reducing socket close timeout delays (2-10 seconds → 500ms)

---

### Fix #4: Faster Main Loop Shutdown Check
**File**: `SimpleSocketBridge.lua:303-305`

**Change**: Reduced loop sleep from 500ms to 200ms

**Before**:
```lua
while _G.LightroomPythonBridge.socketServerRunning do
    LrTasks.sleep(1/2)  -- 500ms
end
```

**After**:
```lua
while _G.LightroomPythonBridge.socketServerRunning do
    LrTasks.sleep(0.2)  -- 200ms - faster shutdown response
end
```

**Impact**: Reduces shutdown check delay from 500ms to 200ms (avg 300ms improvement)

---

### Fix #5: Reduced StopMenuAction Verification Delay
**File**: `StopMenuAction.lua:41-51`

**Change**: Reduced verification wait from 2 seconds to 500ms

**Before**:
```lua
LrTasks.startAsyncTask(function()
    LrTasks.sleep(2)  -- Wait 2 seconds for cleanup

    if not SimpleSocketBridge.isRunning() then
        LrDialogs.showBezel("Python Bridge Stopped", 2)
    else
        LrDialogs.showBezel("Python Bridge Stopping...", 3)
    end
end)
```

**After**:
```lua
LrTasks.startAsyncTask(function()
    LrTasks.sleep(0.5)  -- Wait 500ms for cleanup

    if not SimpleSocketBridge.isRunning() then
        LrDialogs.showBezel("Python Bridge Stopped", 1.5)
    else
        LrDialogs.showBezel("Bridge Stopping...", 2)
    end
end)
```

**Impact**: Faster user feedback when manually stopping bridge (1.5 seconds saved)

---

## Expected Improvements

### Before Fixes
- **Worst case**: 28 seconds
- **Typical case**: 10-15 seconds
- **Best case**: 7 seconds

### After Fixes
- **Worst case**: 2-3 seconds
- **Typical case**: 1-2 seconds
- **Best case**: <1 second

### Breakdown of Improvements
| Component | Before | After | Improvement |
|-----------|--------|-------|-------------|
| Cleanup task | 0-10s | 0-0.5s | ~9.5s |
| Restart task | 2s | 0s | 2s |
| Socket close timeout | 2-10s | 0.5-1s | 5-9s |
| Main loop check | 0-0.5s | 0-0.2s | 0.3s |
| Manual stop UX | 2s | 0.5s | 1.5s |
| **TOTAL** | **10-15s** | **1-2s** | **~10-13s** |

## Testing Recommendations

1. **Normal shutdown**: Close Lightroom with plugin running → should exit within 1-2 seconds
2. **Manual stop**: Use "Stop Python Bridge" menu → should show bezel within 1 second
3. **Client disconnect**: Kill Python client → should auto-restart (not during shutdown)
4. **Verify logs**: Check `LightroomPythonBridge.log` for shutdown messages

## Python Client Considerations

The Python MCP client should listen for the `server.shutdown` event and disconnect gracefully:

```python
# In lightroom_sdk/client.py or socket_bridge.py
# Add handler for shutdown event
def on_shutdown_event(self, event_data):
    logger.info("Received shutdown notification from Lightroom")
    self.disconnect()
```

This will further improve socket close times and prevent connection errors.

## Rollback Instructions

If issues occur, revert these files:
- `lightroom-python-bridge.lrdevplugin/CommandRouter.lua`
- `lightroom-python-bridge.lrdevplugin/SimpleSocketBridge.lua`
- `lightroom-python-bridge.lrdevplugin/StopMenuAction.lua`

Then restart Lightroom to reload the plugin.
