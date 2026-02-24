-- PluginMetadataModule.lua
-- Third-party plugin metadata access API
-- Enables querying custom metadata from plugins like Dominant Color, Jeffrey's Plugins, etc.

local LrApplication = nil
local LrTasks = import 'LrTasks'

-- Get ErrorUtils from global state
local function getErrorUtils()
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.ErrorUtils then
        return _G.LightroomPythonBridge.ErrorUtils
    end
    -- Minimal fallback
    return {
        safeCall = function(func, ...) return LrTasks.pcall(func, ...) end,
        createError = function(code, message) return { error = { code = code or "ERROR", message = message or "An error occurred", severity = "error" } } end,
        createSuccess = function(result) return { result = result or {} } end,
        wrapCallback = function(callback) return callback end,
        CODES = { MISSING_PARAM = "MISSING_PARAM", PHOTO_NOT_FOUND = "PHOTO_NOT_FOUND", CATALOG_ACCESS_FAILED = "CATALOG_ACCESS_FAILED" }
    }
end

local ErrorUtils = getErrorUtils()

-- Lazy load Lightroom modules
local function ensureLrModules()
    if not LrApplication then
        LrApplication = import 'LrApplication'
    end
end

-- Get logger from global state
local function getLogger()
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.logger then
        return _G.LightroomPythonBridge.logger
    end
    local LrLogger = import 'LrLogger'
    local logger = LrLogger('PluginMetadataModule')
    logger:enable("logfile")
    return logger
end

local PluginMetadataModule = {}

-- Get plugin metadata for a single photo
function PluginMetadataModule.getMetadata(params, callback)
    local wrappedCallback = ErrorUtils.wrapCallback(callback, "getMetadata")

    -- Ensure modules are loaded
    local moduleSuccess, moduleError = ErrorUtils.safeCall(ensureLrModules)
    if not moduleSuccess then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.RESOURCE_UNAVAILABLE,
            "Failed to load Lightroom modules: " .. tostring(moduleError)))
        return
    end

    local logger = getLogger()
    local photoId = params and params.photoId
    local pluginId = params and params.pluginId
    local fieldIds = params and params.fieldIds or {}

    -- Validate required parameters
    if not photoId then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.MISSING_PARAM,
            "Photo ID is required"))
        return
    end

    if not pluginId then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.MISSING_PARAM,
            "Plugin ID is required"))
        return
    end

    if type(fieldIds) ~= "table" or #fieldIds == 0 then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.MISSING_PARAM,
            "Field IDs array is required and must not be empty"))
        return
    end

    logger:debug("Getting plugin metadata for photo " .. photoId .. " from plugin " .. pluginId)

    local catalog = LrApplication.activeCatalog()

    catalog:withReadAccessDo(function()
        -- Find photo by localIdentifier
        local findSuccess, photo = ErrorUtils.safeCall(function()
            return catalog:getPhotoByLocalId(tonumber(photoId))
        end)

        if not findSuccess or not photo then
            wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.PHOTO_NOT_FOUND,
                "Photo with ID " .. photoId .. " not found"))
            return
        end

        -- Get metadata for each field
        local metadata = {}
        for _, fieldId in ipairs(fieldIds) do
            local success, value = ErrorUtils.safeCall(function()
                return photo:getPropertyForPlugin(pluginId, fieldId)
            end)

            if success then
                metadata[fieldId] = value
            else
                -- Field not found or error, set to nil
                metadata[fieldId] = nil
                logger:debug("Could not retrieve field '" .. fieldId .. "': " .. tostring(value))
            end
        end

        logger:info("Retrieved " .. #fieldIds .. " plugin metadata fields for photo " .. photoId)

        wrappedCallback(ErrorUtils.createSuccess({
            photoId = photoId,
            pluginId = pluginId,
            metadata = metadata
        }, "Plugin metadata retrieved successfully"))
    end)
end

-- Batch get plugin metadata for multiple photos (EFFICIENT)
function PluginMetadataModule.batchGetMetadata(params, callback)
    local wrappedCallback = ErrorUtils.wrapCallback(callback, "batchGetMetadata")

    -- Ensure modules are loaded
    local moduleSuccess, moduleError = ErrorUtils.safeCall(ensureLrModules)
    if not moduleSuccess then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.RESOURCE_UNAVAILABLE,
            "Failed to load Lightroom modules: " .. tostring(moduleError)))
        return
    end

    local logger = getLogger()
    local photoIds = params and params.photoIds
    local pluginId = params and params.pluginId
    local fieldIds = params and params.fieldIds

    -- Validate parameters
    if not photoIds or type(photoIds) ~= "table" or #photoIds == 0 then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.MISSING_PARAM,
            "Photo IDs array is required and must not be empty"))
        return
    end

    if not pluginId then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.MISSING_PARAM,
            "Plugin ID is required"))
        return
    end

    if not fieldIds or type(fieldIds) ~= "table" or #fieldIds == 0 then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.MISSING_PARAM,
            "Field IDs array is required and must not be empty"))
        return
    end

    logger:debug("Batch getting plugin metadata for " .. #photoIds .. " photos from plugin " .. pluginId)

    local catalog = LrApplication.activeCatalog()

    catalog:withReadAccessDo(function()
        -- Find all photos
        local photos = {}
        local photoIdMap = {}  -- Map photo objects to their IDs

        for _, photoId in ipairs(photoIds) do
            local success, photo = ErrorUtils.safeCall(function()
                return catalog:getPhotoByLocalId(tonumber(photoId))
            end)

            if success and photo then
                table.insert(photos, photo)
                photoIdMap[photo] = photoId
            else
                logger:debug("Photo " .. photoId .. " not found, skipping")
            end
        end

        if #photos == 0 then
            wrappedCallback(ErrorUtils.createSuccess({
                pluginId = pluginId,
                fieldIds = fieldIds,
                metadata = {},
                requested = #photoIds,
                found = 0
            }, "No photos found"))
            return
        end

        -- Use efficient batch API
        local batchSuccess, results = ErrorUtils.safeCall(function()
            return catalog:batchGetPropertyForPlugin(photos, pluginId, fieldIds)
        end)

        if not batchSuccess or not results then
            -- Fallback to individual queries if batch API fails
            logger:debug("Batch API failed or returned nil, falling back to individual queries")
            local output = {}

            for _, photo in ipairs(photos) do
                local photoId = photoIdMap[photo]
                local photoMetadata = {}

                for _, fieldId in ipairs(fieldIds) do
                    local success, value = ErrorUtils.safeCall(function()
                        return photo:getPropertyForPlugin(pluginId, fieldId)
                    end)

                    if success then
                        photoMetadata[fieldId] = value
                    else
                        photoMetadata[fieldId] = nil
                    end
                end

                if photoId then
                    output[tostring(photoId)] = photoMetadata
                end
            end

            wrappedCallback(ErrorUtils.createSuccess({
                pluginId = pluginId,
                fieldIds = fieldIds,
                metadata = output,
                requested = #photoIds,
                found = #photos,
                fallback = true
            }, "Batch plugin metadata retrieved successfully (fallback mode)"))
            return
        end

        -- Convert to JSON-friendly format (photo ID as key)
        local output = {}
        for photo, metadata in pairs(results) do
            local photoId = photoIdMap[photo]
            if photoId then
                output[tostring(photoId)] = metadata
            end
        end

        logger:info("Retrieved plugin metadata for " .. #photos .. " photos")

        wrappedCallback(ErrorUtils.createSuccess({
            pluginId = pluginId,
            fieldIds = fieldIds,
            metadata = output,
            requested = #photoIds,
            found = #photos
        }, "Batch plugin metadata retrieved successfully"))
    end)
end

-- Search for photos by plugin property
function PluginMetadataModule.findPhotosWithProperty(params, callback)
    local wrappedCallback = ErrorUtils.wrapCallback(callback, "findPhotosWithProperty")

    -- Ensure modules are loaded
    local moduleSuccess, moduleError = ErrorUtils.safeCall(ensureLrModules)
    if not moduleSuccess then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.RESOURCE_UNAVAILABLE,
            "Failed to load Lightroom modules: " .. tostring(moduleError)))
        return
    end

    local logger = getLogger()
    local pluginId = params and params.pluginId
    local fieldId = params and params.fieldId
    local value = params and params.value  -- Optional

    -- Validate parameters
    if not pluginId then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.MISSING_PARAM,
            "Plugin ID is required"))
        return
    end

    if not fieldId then
        wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.MISSING_PARAM,
            "Field ID is required"))
        return
    end

    logger:debug("Searching for photos with plugin property: " .. pluginId .. "." .. fieldId)

    local catalog = LrApplication.activeCatalog()

    catalog:withReadAccessDo(function()
        -- Search for photos with this property
        -- Note: findPhotosWithProperty signature is (pluginId, fieldId, [searchValue])
        local searchSuccess, photos = ErrorUtils.safeCall(function()
            if value ~= nil then
                -- When searching for specific value, pass 3 parameters
                return catalog:findPhotosWithProperty(pluginId, fieldId, value)
            else
                -- When searching for any value, pass 2 parameters
                return catalog:findPhotosWithProperty(pluginId, fieldId)
            end
        end)

        if not searchSuccess then
            wrappedCallback(ErrorUtils.createError(ErrorUtils.CODES.CATALOG_ACCESS_FAILED,
                "Failed to search for photos with plugin property: " .. tostring(photos)))
            return
        end

        -- Convert to response format
        local results = {}
        for _, photo in ipairs(photos) do
            local photoData = {
                id = photo.localIdentifier
            }

            -- Safely get filename
            ErrorUtils.safeCall(function()
                photoData.filename = photo:getFormattedMetadata("fileName")
                photoData.path = photo:getRawMetadata("path")
            end)

            table.insert(results, photoData)
        end

        logger:info("Found " .. #results .. " photos with plugin property " .. pluginId .. "." .. fieldId)

        wrappedCallback(ErrorUtils.createSuccess({
            pluginId = pluginId,
            fieldId = fieldId,
            searchValue = value,
            photos = results,
            count = #results
        }, "Photos with plugin property found successfully"))
    end)
end

return PluginMetadataModule