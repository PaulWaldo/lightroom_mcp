-- SimpleSocketBridge.lua
-- Single-socket bridge for Windows compatibility.
-- Uses ONE receive-mode socket for bidirectional JSON communication.
-- The receive socket's onMessage handler processes commands and sends
-- responses back via socket:send() on the same connection.

local LrSocket = import 'LrSocket'
local LrTasks = import 'LrTasks'
local LrFunctionContext = import 'LrFunctionContext'
local LrDialogs = import 'LrDialogs'
local LrPathUtils = import 'LrPathUtils'

-- Port file in user's home directory (cross-platform)
local portFilePath = LrPathUtils.child(LrPathUtils.getStandardFilePath("home"), "lightroom_ports.txt")

-- Module-level state
local commandRouter = nil
local responseSocket = nil  -- Store socket ref for sending responses
local isRestarting = false

-- Get Phase 3 modules from global state
local function getPhase3Modules()
    local bridge = _G.LightroomPythonBridge
    if not bridge or not bridge.phase3Loaded then
        return nil, nil
    end
    return bridge.MessageProtocol, bridge.CommandRouter
end

-- Get logger from global state
local function getLogger()
    local bridge = _G.LightroomPythonBridge
    if bridge and bridge.logger then
        return bridge.logger
    end
    local LrLogger = import 'LrLogger'
    local logger = LrLogger('SimpleSocketBridge')
    logger:enable("logfile")
    return logger
end

-- Forward declaration
local restartSocketServer

-- Write port info for Python client (single port)
local function writePortFile(port)
    local logger = getLogger()
    local success, err = LrTasks.pcall(function()
        local file = io.open(portFilePath, "w")
        if file then
            -- Write same port twice for backward compat with Python reader
            file:write(string.format("%d,%d", port, port))
            file:close()
            logger:info("Port file written: port=" .. port)
        else
            logger:error("Failed to create port file at " .. portFilePath)
        end
    end)
    if not success then
        logger:error("Error writing port file: " .. tostring(err))
    end
end

-- Single-socket server
local function startSocketServer()
    local logger = getLogger()
    logger:info("Starting single-socket bridge (Windows-compatible)")

    -- Initialize command router
    local MessageProtocol, CommandRouter = getPhase3Modules()
    if CommandRouter then
        commandRouter = CommandRouter
        commandRouter:init()
        _G.LightroomPythonBridge.commandRouter = commandRouter
        logger:info("Command router initialized")

        local bridge = _G.LightroomPythonBridge
        if bridge.registerSystemCommands then
            bridge.registerSystemCommands()
        end
        if bridge.registerApiCommands and bridge.phase4Loaded then
            bridge.registerApiCommands()
        end
    else
        logger:error("Phase 3 modules not available")
    end

    LrTasks.startAsyncTask(function()
        LrFunctionContext.callWithContext('lightroom_python_bridge', function(context)
            logger:info("Socket context created")

            local bridgePort
            local bridgeSocket

            -- Single receive-mode socket for bidirectional communication
            bridgeSocket = LrSocket.bind {
                functionContext = context,
                address = "localhost",
                port = 0,  -- Auto-assign
                mode = "receive",
                plugin = _PLUGIN,

                onConnecting = function(socket, port)
                    logger:info("Bridge socket listening on port " .. port)
                    bridgePort = port
                    writePortFile(port)
                end,

                onConnected = function(socket, port)
                    logger:info("Python connected to bridge socket")
                    responseSocket = socket

                    local LrHttp = import 'LrHttp'

                    -- Set up command router to send responses via HTTP POST
                    -- LrSocket receive mode cannot send data back through the socket.
                    -- Instead, POST responses to Python's HTTP callback server.
                    -- CRITICAL: LrHttp.post() yields, so it CANNOT be called from
                    -- inside withReadAccessDo/withWriteAccessDo. We wrap every send
                    -- in its own async task to avoid blocking sync catalog handlers.
                    if commandRouter then
                        commandRouter:setSocketBridge({
                            send = function(jsonData)
                                if not jsonData then
                                    logger:error("Cannot send - data is nil")
                                    return false
                                end
                                if type(jsonData) ~= "string" then
                                    logger:error("jsonData is not a string: " .. type(jsonData))
                                    return false
                                end

                                -- Fire-and-forget async task for HTTP POST
                                -- This allows send() to return immediately even when
                                -- called from inside withReadAccessDo
                                LrTasks.startAsyncTask(function()
                                    local LrHttp = import 'LrHttp'
                                    local url = "http://localhost:54400/response"
                                    local headers = {
                                        { field = "Content-Type", value = "application/json" }
                                    }
                                    local body, respHeaders = LrHttp.post(url, jsonData, headers, "POST", 5)

                                    if body then
                                        logger:debug("HTTP response sent successfully")
                                    else
                                        logger:error("HTTP response send failed")
                                    end
                                end)

                                return true  -- Return immediately
                            end
                        })

                        -- Send connection event via HTTP
                        commandRouter:sendEvent("connection.established", {
                            port = bridgePort
                        })
                    end
                end,

                onMessage = function(socket, message)
                    logger:info("Message received: " .. tostring(message):sub(1, 200))

                    -- Store socket ref for responses (may update on reconnect)
                    responseSocket = socket

                    local MessageProtocol, _ = getPhase3Modules()
                    if MessageProtocol and commandRouter then
                        local decoded = MessageProtocol:decode(tostring(message))
                        if decoded then
                            logger:info("Dispatching command: " .. (decoded.command or "unknown"))
                            commandRouter:dispatch(decoded)
                        else
                            logger:error("Failed to decode message: " .. tostring(message):sub(1, 100))
                        end
                    end
                end,

                onClosed = function(socket)
                    logger:info("Bridge socket closed")
                    responseSocket = nil
                    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning then
                        restartSocketServer()
                    end
                end,

                onError = function(socket, err)
                    logger:error("Bridge socket error: " .. err)
                    if err == "timeout" and _G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning then
                        socket:reconnect()
                    end
                end
            }

            logger:info("Bridge socket created - entering keep-alive loop")

            if commandRouter then
                commandRouter:startCleanupTask()
            end

            _G.LightroomPythonBridge.socketServerRunning = true

            while _G.LightroomPythonBridge.socketServerRunning do
                LrTasks.sleep(0.2)
            end

            logger:info("Socket server loop ended - cleaning up")

            if bridgeSocket then
                bridgeSocket:close()
            end

            pcall(function()
                local LrFileUtils = import 'LrFileUtils'
                if LrFileUtils.exists(portFilePath) then
                    LrFileUtils.delete(portFilePath)
                end
            end)

            logger:info("Socket server stopped")
            LrDialogs.showBezel("Python Bridge Disconnected", 2)
        end)
    end)
end

-- Restart after disconnect
restartSocketServer = function()
    local logger = getLogger()

    if not (_G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning) then
        return
    end

    if isRestarting then
        return
    end

    isRestarting = true
    logger:info("Restarting socket server...")

    LrTasks.startAsyncTask(function()
        if not (_G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning) then
            isRestarting = false
            return
        end

        responseSocket = nil
        LrTasks.sleep(2)

        if not (_G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning) then
            isRestarting = false
            return
        end

        startSocketServer()
        isRestarting = false
    end)
end

-- Stop
local function stopSocketServer()
    local logger = getLogger()
    logger:info("Stopping socket server")

    if _G.LightroomPythonBridge then
        _G.LightroomPythonBridge.socketServerRunning = false
    end

    if commandRouter and commandRouter.socketBridge then
        pcall(function()
            commandRouter:sendEvent("server.shutdown", { reason = "Lightroom closing" })
        end)
    end

    responseSocket = nil
    isRestarting = false

    if commandRouter then
        commandRouter = nil
    end

    pcall(function()
        local LrFileUtils = import 'LrFileUtils'
        if LrFileUtils.exists(portFilePath) then
            LrFileUtils.delete(portFilePath)
        end
    end)

    logger:info("Socket server stop initiated")
end

local function isRunning()
    return _G.LightroomPythonBridge and _G.LightroomPythonBridge.socketServerRunning
end

return {
    start = startSocketServer,
    stop = stopSocketServer,
    isRunning = isRunning,
    getRouter = function() return commandRouter end,
    send = function(msg) if responseSocket then responseSocket:send(msg) return true end return false end
}
