-- StopMenuAction.lua  
-- Handles "Stop Python Bridge" menu action

local LrLogger = import 'LrLogger'
local LrDialogs = import 'LrDialogs'
local SimpleSocketBridge = require 'SimpleSocketBridge'

-- Access global plugin state
local bridge = _G.LightroomPythonBridge

-- Create logger directly for menu action
local myLogger = LrLogger('StopMenuAction')
myLogger:enable("logfile")

-- This code executes when the menu item is selected
myLogger:info("Stop Python Bridge menu item selected")

-- Check if plugin is initialized
if not bridge or not bridge.initialized then
    LrDialogs.message("Python Bridge", "Plugin not properly initialized. Please restart Lightroom.", "critical")
    return
end

-- Use global logger if available
local logger = bridge.logger or myLogger

-- Check if socket server is running
if not SimpleSocketBridge.isRunning() then
    logger:info("Socket server not running")
    LrDialogs.message("Python Bridge", "Bridge is not currently running.", "info")
    return
end

logger:info("Stopping Python Bridge")

-- Stop the socket server
SimpleSocketBridge.stop()

-- Give it a moment to clean up
local LrTasks = import 'LrTasks'
LrTasks.startAsyncTask(function()
    LrTasks.sleep(2)  -- Wait 2 seconds for cleanup
    
    if not SimpleSocketBridge.isRunning() then
        logger:info("Python Bridge stopped successfully")
        LrDialogs.showBezel("Python Bridge Stopped", 2)
    else
        logger:warn("Python Bridge may still be shutting down")
        LrDialogs.showBezel("Python Bridge Stopping...", 3)
    end
end)

logger:info("Socket server stop requested")