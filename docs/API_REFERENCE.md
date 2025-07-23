# Lightroom Python Bridge - API Reference

## Overview

The Lightroom Python Bridge provides JSON-RPC over TCP sockets for controlling Lightroom Classic programmatically. All commands follow the request/response pattern:

**Request:**
```json
{
  "id": "unique-request-id",
  "command": "catalog.getAllPhotos",  
  "params": { "limit": 10 }
}
```

**Response:**
```json
{
  "id": "unique-request-id",
  "success": true,
  "result": { ... }
}
```

## System Commands

| Command | Description | Parameters |
|---------|-------------|------------|
| `system.ping` | Test connectivity | None |
| `system.status` | Get bridge status and statistics | None |

## Catalog Commands (11 total)

| Command | Description | Parameters |
|---------|-------------|------------|
| `catalog.getAllPhotos` | Get all photos with pagination | `limit`, `offset` |
| `catalog.searchPhotos` | Search photos with flexible criteria | `criteria`, `limit`, `offset` |
| `catalog.findPhotoByPath` | Find photo by exact file path | `path` |
| `catalog.findPhotos` | Advanced search with LR search descriptors | `searchDesc`, `limit` |
| `catalog.getPhotoMetadata` | Get comprehensive photo metadata | `photoId` |
| `catalog.getSelectedPhotos` | Get currently selected photos in LR | None |
| `catalog.setSelectedPhotos` | Set photo selection in LR | `photoIds[]` |
| `catalog.getCollections` | Get all collections in catalog | None |
| `catalog.getKeywords` | Get all keywords with photo counts | None |
| `catalog.getFolders` | Get folder hierarchy | `includeSubfolders` (bool) |
| `catalog.batchGetFormattedMetadata` | Bulk metadata retrieval (26.8x faster) | `photoIds[]`, `keys[]` |

### Response Formats

#### catalog.getSelectedPhotos
```json
// Response
{
  "success": true,
  "result": {
    "count": 1,
    "photos": [
      {
        "id": 1735,
        "filename": "SacredMonkeyForest-226.ARW",
        "path": "/Volumes/photo/Bali/SacredMonkeyForest/SacredMonkeyForest-226.ARW",
        "fileFormat": "RAW",
        "folderPath": "SacredMonkeyForest", 
        "captureTime": "4/27/19 11:13:07 PM",
        "isVirtualCopy": false
      }
    ]
  }
}
```

**Photo Object Fields:**
- `id`: Unique photo identifier (number)
- `filename`: File name with extension (string)
- `path`: Full file system path (string)
- `fileFormat`: "RAW", "JPEG", "TIFF", etc. (string)
- `folderPath`: Parent folder name (string)
- `captureTime`: Formatted capture timestamp (string)
- `isVirtualCopy`: Virtual copy flag (boolean)

#### catalog.getFolders
```json
// Request
{
  "command": "catalog.getFolders",
  "params": { "includeSubfolders": true }
}

// Response
{
  "success": true,
  "result": {
    "count": 15,
    "folders": [
      {
        "name": "Travel",
        "path": "/Photos/Travel",
        "photoCount": 342,
        "subfolders": [
          {
            "name": "Bali",
            "path": "/Photos/Travel/Bali",
            "photoCount": 156
          }
        ]
      }
    ]
  }
}
```

## Develop Commands (49 total)

### Basic Develop Commands
| Command | Description | Parameters |
|---------|-------------|------------|
| `develop.getSettings` | Get all develop settings for a photo | `photoId` |
| `develop.applySettings` | Apply multiple develop settings | `photoId`, `settings{}` |
| `develop.batchApplySettings` | Apply settings to multiple photos | `photoIds[]`, `settings{}` |
| `develop.getValue` | Get single parameter value | `param` |
| `develop.setValue` | Set single parameter value | `param`, `value` |
| `develop.getRange` | Get valid range for parameter | `param` |
| `develop.resetToDefault` | Reset parameter to default | `param` |
| `develop.setAutoTone` | Apply automatic tone adjustments | None |
| `develop.setAutoWhiteBalance` | Apply automatic white balance | None |
| `develop.getProcessVersion` | Get current RAW process version | None |
| `develop.setProcessVersion` | Set RAW process version | `version` |
| `develop.resetAllDevelopAdjustments` | Reset all develop settings | None |

### ToneCurve Manipulation Commands ✨ **NEW**
| Command | Description | Parameters |
|---------|-------------|------------|
| `develop.getCurvePoints` | Get curve as coordinate points | `param` |
| `develop.setCurvePoints` | Set curve from coordinate points | `param`, `points[]` |
| `develop.setCurveLinear` | Set linear curve (reset) | `param` |
| `develop.setCurveSCurve` | Apply S-curve preset | `param`, `strength` |
| `develop.addCurvePoint` | Add single point to curve | `param`, `x`, `y` |
| `develop.removeCurvePoint` | Remove curve point by index | `param`, `index` |

### PointColors Helper APIs ✨ **NEW**
| Command | Description | Parameters |
|---------|-------------|------------|
| `develop.createGreenSwatch` | Create green color enhancement swatch | `saturationBoost`, `luminanceAdjust`, `hueShift`, `rangeWidth` |
| `develop.createCyanSwatch` | Create cyan color correction swatch | `saturationBoost`, `luminanceAdjust`, `hueShift`, `rangeWidth` |
| `develop.enhanceColors` | Apply color grading presets | `preset`, `preserveExisting` |

### Develop Parameters (114 supported - 98% coverage)

✅ **Complete Parameter Coverage** - 114 develop parameters supported across 49 commands with comprehensive error handling and validation.

**Basic Panel:** Temperature (2000-50000), Tint (-150-150), Exposure (-5-5), Contrast, Highlights, Shadows, Whites, Blacks, Brightness, Clarity, Vibrance, Saturation, Texture, Dehaze

**Tone Curve:** ParametricDarks, ParametricLights, ParametricShadows, ParametricHighlights, ParametricShadowSplit, ParametricMidtoneSplit, ParametricHighlightSplit

**Point Curves:** ToneCurvePV2012 (luminance), ToneCurvePV2012Red/Green/Blue (RGB channels), CurveRefineSaturation

**HSL/Color (25 params):** HueAdjustment[Color], SaturationAdjustment[Color], LuminanceAdjustment[Color] where Color = Red, Orange, Yellow, Green, Aqua, Blue, Purple, Magenta + PointColors (advanced color selection)

**Detail:** Sharpness, SharpenRadius, SharpenDetail, SharpenEdgeMasking, LuminanceSmoothing, LuminanceNoiseReductionDetail, ColorNoiseReduction

**Lens Corrections:** LensProfileEnable, AutoLateralCA, PerspectiveVertical, PerspectiveHorizontal, PerspectiveRotate, PerspectiveScale

**Lens Blur (LR 14.4+):** LensBlurActive, LensBlurAmount, LensBlurCatEye, LensBlurHighlightsBoost

**Effects:** PostCropVignetteAmount, GrainAmount, GrainSize, GrainFrequency

**Calibration:** ShadowTint, RedHue, RedSaturation, GreenHue, GreenSaturation, BlueHue, BlueSaturation

### Example: Get Parameter Range
```json
// Request
{ "command": "develop.getRange", "params": { "param": "Exposure" } }

// Response
{ "success": true, "result": { "param": "Exposure", "min": -5, "max": 5 } }
```

**Note:** Some parameters return numeric values that are converted to min/max ranges. Temperature uses 2000-50000, most others use -100 to +100.

## Preview Commands (4 total)

| Command | Description | Parameters |
|---------|-------------|------------|
| `preview.generatePreview` | Generate JPEG thumbnail | `photoId`, `size`, `quality`, `base64` |
| `preview.generateBatchPreviews` | Generate multiple previews | `photoIds[]`, `size`, `quality` |
| `preview.getPreviewInfo` | Get preview generation info | `photoId` |
| `preview.getPreviewChunk` | Get chunked preview data | `previewId`, `chunkIndex` |

### Preview Sizes
- `small`: ~240px
- `medium`: ~640px
- `large`: ~1440px
- `full`: Original size

**Note:** Large previews (>10MB) automatically use chunked transfer.

## Error Codes

All errors include standardized severity levels (`error`, `warning`, `info`) and detailed context.

| Code | Severity | Description |
|------|----------|-------------|
| `MISSING_PHOTO_ID` | error | Photo ID parameter required |
| `NO_PHOTO_SELECTED` | error | No photo currently selected for develop operations |
| `PHOTO_NOT_FOUND` | error | Photo with given ID not found |
| `INVALID_PARAM` | error | Unknown develop parameter name |
| `INVALID_PARAM_VALUE` | error | Parameter value outside valid range |
| `INVALID_PARAM_TYPE` | error | Parameter value wrong type (string/number/boolean) |
| `HANDLER_ERROR` | error | Lua execution error |
| `CONNECTION_FAILED` | error | Socket connection lost |
| `CATALOG_ACCESS_FAILED` | error | Failed to access Lightroom catalog |
| `WRITE_ACCESS_BLOCKED` | warning | Lightroom write operation blocked |
| `RESOURCE_UNAVAILABLE` | warning | Required Lightroom module unavailable |

## Quick Start Examples

### Connect and Get Photos
```python
# Ports are written to /tmp/lightroom_ports.txt
sender_port, receiver_port = read_ports()
send_socket = connect(receiver_port)  # Send TO Lightroom
recv_socket = connect(sender_port)   # Receive FROM Lightroom

# Get first 10 photos
request = {
  "id": "123",
  "command": "catalog.getAllPhotos",
  "params": {"limit": 10, "offset": 0}
}
```

### Apply Develop Settings
```python
request = {
  "id": "456",
  "command": "develop.applySettings",
  "params": {
    "photoId": "12345",
    "settings": {
      "Exposure": 0.5,
      "Contrast": 10,
      "Vibrance": 20
    }
  }
}
```

### Manipulate ToneCurves ✨ **NEW**
```python
# Get curve points
request = {
  "id": "curve1",
  "command": "develop.getCurvePoints",
  "params": {"param": "ToneCurvePV2012"}
}

# Set custom S-curve  
request = {
  "id": "curve2",
  "command": "develop.setCurvePoints",
  "params": {
    "param": "ToneCurvePV2012",
    "points": [
      {"x": 0, "y": 0}, {"x": 64, "y": 48}, 
      {"x": 128, "y": 128}, {"x": 192, "y": 208}, {"x": 255, "y": 255}
    ]
  }
}

# Apply S-curve preset
request = {
  "id": "curve3", 
  "command": "develop.setCurveSCurve",
  "params": {"param": "ToneCurvePV2012", "strength": 30}
}
```

### PointColors Helper APIs ✨ **NEW**
```python
# Create green color enhancement
request = {
  "id": "pc1",
  "command": "develop.createGreenSwatch",
  "params": {
    "saturationBoost": 0.2,
    "luminanceAdjust": 0.1,
    "rangeWidth": "normal"
  }
}

# Create cyan color correction
request = {
  "id": "pc2", 
  "command": "develop.createCyanSwatch",
  "params": {
    "saturationBoost": 0.3,
    "rangeWidth": "tight"
  }
}

# Apply color grading presets
request = {
  "id": "pc3",
  "command": "develop.enhanceColors", 
  "params": {
    "preset": "vibrant",
    "preserveExisting": false
  }
}
```

**PointColors Parameters:**
- `saturationBoost`: -1.0 to 1.0 (saturation adjustment)
- `luminanceAdjust`: -1.0 to 1.0 (brightness adjustment)  
- `hueShift`: -1.0 to 1.0 (hue shift)
- `rangeWidth`: "tight", "normal", "wide" (selection precision)
- `preset`: "natural", "vibrant", "muted", "autumn"
- `preserveExisting`: true/false (keep existing swatches)

### Generate Preview
```python
request = {
  "id": "789",
  "command": "preview.generatePreview",
  "params": {
    "photoId": "12345",
    "size": "medium",
    "quality": 90,
    "base64": true
  }
}
```

## Architecture Notes

- **Plugin**: Lua-based Lightroom Classic plugin
- **Protocol**: JSON-RPC 2.0-like over TCP
- **Sockets**: Dual unidirectional sockets (LrSocket limitation)
- **Commands**: Routed through CommandRouter.lua
- **Modules**: CatalogModule, DevelopModule, PreviewModule
- **Bridge**: SimpleSocketBridge.lua manages connections

## Advanced Features ✨ **NEW**

### Local Adjustments & Masking (28 commands)
Complete masking system with AI-powered selections, range masks, and local parameter support:

#### Masking Navigation & State (3 commands)
| Command | Description | Parameters |
|---------|-------------|------------|
| `develop.goToMasking` | Open masking panel | None |
| `develop.toggleOverlay` | Toggle mask overlay visualization | None |
| `develop.selectTool` | Select develop tool | `tool` |

#### Mask Management (5 commands)
| Command | Description | Parameters |
|---------|-------------|------------|
| `develop.getAllMasks` | Get all masks for current photo | None |
| `develop.getSelectedMask` | Get currently selected mask | None |
| `develop.createNewMask` | Create new mask | `maskType`, `maskSubtype` |
| `develop.selectMask` | Select specific mask | `maskId`, `param` |
| `develop.deleteMask` | Delete mask | `maskId`, `param` |

#### Mask Tool Management (3 commands)
| Command | Description | Parameters |
|---------|-------------|------------|
| `develop.getSelectedMaskTool` | Get selected mask tool | None |
| `develop.selectMaskTool` | Select mask tool | `toolType` |
| `develop.deleteMaskTool` | Delete mask tool | `toolId` |

#### Boolean Mask Operations (4 commands)
| Command | Description | Parameters |
|---------|-------------|------------|
| `develop.addToCurrentMask` | Add tool to current mask | `maskType`, `maskSubtype` |
| `develop.intersectWithCurrentMask` | Intersect with current mask | `maskType`, `maskSubtype` |
| `develop.subtractFromCurrentMask` | Subtract from current mask | `maskType`, `maskSubtype` |
| `develop.invertMask` | Invert mask | `maskId`, `param` |

#### Helper Functions (6 commands)
| Command | Description | Parameters |
|---------|-------------|------------|
| `develop.createGraduatedFilter` | Create graduated filter mask | None |
| `develop.createRadialFilter` | Create radial filter mask | None |
| `develop.createAdjustmentBrush` | Create adjustment brush mask | None |
| `develop.createAISelectionMask` | Create AI selection mask | `selectionType` |
| `develop.createRangeMask` | Create range mask | `rangeType` |
| `develop.createComplexMask` | Create complex mask workflow | `workflow` |

#### Local Parameter Access (6 commands)
| Command | Description | Parameters |
|---------|-------------|------------|
| `develop.activateMaskingMode` | Activate masking mode for local parameters | None |
| `develop.getLocalValue` | Get local parameter value for specific mask | `param`, `maskId` |
| `develop.setLocalValue` | Set local parameter value for specific mask | `param`, `value`, `maskId` |
| `develop.applyLocalSettings` | Apply multiple local settings to mask | `settings{}`, `maskId` |
| `develop.getAvailableLocalParameters` | Get all available local parameters | None |
| `develop.createMaskWithLocalAdjustments` | Create mask with initial local settings | `maskType`, `maskSubtype`, `localSettings{}` |

#### Reset Operations (4 commands)
| Command | Description | Parameters |
|---------|-------------|------------|
| `develop.resetGradient` | Reset all gradient filters | None |
| `develop.resetCircularGradient` | Reset all radial filters | None |
| `develop.resetBrushing` | Reset all brush adjustments | None |
| `develop.resetMasking` | Reset all masks from photo | None |

**Supported Mask Types:**
- **AI Selections**: Subject, sky, background, objects, people, landscape
- **Range Masks**: Luminance, color, depth-based selections  
- **Manual Tools**: Graduated filter, radial filter, adjustment brush
- **Local Parameters**: 23 parameters (temperature, exposure, clarity, etc.)

### Error Handling & Validation
- **Parameter Validation**: Type checking and range validation for all parameters
- **Photo Selection Awareness**: Clear error messages when no photo selected
- **Graceful Degradation**: Continues operation even with partial failures
- **Comprehensive Logging**: Detailed error context and severity levels

### Performance Optimizations
- **Batch Operations**: Up to 26.8x faster metadata retrieval
- **Connection Resilience**: Automatic reconnection and timeout handling
- **Memory Management**: Pagination and chunked transfer for large data

## Version
- Current: 2.0.0 (Major Error Handling & Masking Release)
- Lightroom SDK: 5.0+
- Tested with: Lightroom Classic 12.x, 13.x, 14.x
- **Total Commands**: 66 registered handlers (2 system + 49 develop + 11 catalog + 4 preview)