-- PluginShutdown.lua
-- Handles plugin shutdown when plugin is disabled
-- This file executes directly when shutdown occurs

local LrLogger = import 'LrLogger'
local SimpleSocketBridge = require 'SimpleSocketBridge'

-- Access global plugin state
local bridge = _G.LightroomPythonBridge

-- Create fallback logger if needed
local myLogger = LrLogger('PluginShutdown')
myLogger:enable("logfile")

if bridge then
    local logger = bridge.logger or myLogger
    logger:info("Plugin shutdown initiated")
    
    -- Mark as not running
    bridge.running = false
    
    -- Stop socket server if running
    if SimpleSocketBridge.isRunning() then
        logger:info("Stopping socket server...")
        SimpleSocketBridge.stop()
    end
    
    logger:info("Plugin shutdown complete")
else
    myLogger:warn("Plugin global state not found during shutdown")
end