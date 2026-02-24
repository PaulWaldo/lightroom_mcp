# Product Context

## Problem Statement

### The Challenge
Adobe Lightroom Classic is a powerful RAW photo editing and catalog management tool used by professional photographers and enthusiasts. However, it lacks programmatic access for automation and AI-assisted workflows. Photographers need:

1. **Automated Photo Processing**: Apply consistent edits across large photo collections
2. **AI-Assisted Editing**: Let AI agents analyze photos and suggest/apply adjustments
3. **Batch Operations**: Efficiently process hundreds or thousands of photos
4. **Intelligent Organization**: Use AI to search, categorize, and organize photo libraries
5. **Quality Analysis**: Automatically detect exposure issues, histogram problems, and technical defects

### Current Limitations
- Lightroom's UI requires manual interaction for each operation
- No standard API for external tools to control Lightroom
- Lua plugin SDK exists but requires complex socket programming
- Batch operations require repetitive manual steps
- No integration with modern AI agent frameworks

## Solution

### Lightroom Classic MCP Server
A Model Context Protocol server that bridges AI agents to Lightroom Classic, enabling programmatic control through a clean, well-documented API.

**Architecture**:
```
[AI Agent/LLM] ↔ [MCP Server] ↔ [Lightroom Plugin] ↔ [Lightroom Classic]
```

### Key Capabilities

1. **📚 Catalog Operations**
   - Search photos by metadata, keywords, collections, folders
   - Extract comprehensive EXIF and metadata
   - Manage collections and keywords
   - Control photo selection programmatically
   - Query third-party plugin metadata (e.g., Dominant Color, AI tags)

2. **🎨 Develop Tools**
   - Access all 114 RAW adjustment parameters
   - Apply basic adjustments (exposure, contrast, highlights, shadows, whites, blacks)
   - Fine-tune with advanced controls (clarity, vibrance, saturation, texture, dehaze)
   - Manipulate tone curves for custom contrast
   - Adjust HSL/color for selective color control
   - Apply detail controls (sharpening, noise reduction)
   - Correct lens distortions and chromatic aberration
   - Add effects (vignetting, grain, split toning)
   - Calibrate color for specific cameras

3. **🖼️ Preview Generation**
   - Generate optimized JPEG previews
   - Multiple size options (small, medium, large, full)
   - Automatic resizing with PIL
   - Quality control (1-100)
   - Save to custom locations

4. **📊 Histogram Analysis**
   - RGB channel histograms
   - Luminance histogram
   - Clipping detection (highlights/shadows)
   - Tonal distribution analysis
   - Exposure verification

5. **🔌 Plugin Metadata Access**
   - Query metadata from any third-party Lightroom plugin
   - Single photo metadata retrieval
   - Efficient batch queries (10-20x faster)
   - Search photos by plugin property values
   - Support for color analysis plugins (Dominant Color, etc.)
   - Access AI-generated tags and classifications

6. **⚡ Performance**
   - Batch operations (10-20x faster than individual calls)
   - Efficient chunked transfer for large files
   - Auto-reconnection on connection loss
   - Comprehensive error handling

## User Experience

### For AI Agents
AI agents interact with Lightroom through natural language prompts:

**Basic Adjustments:**
> "Select the first RAW photo and increase exposure by +0.5, add some vibrance, and reduce highlights"

**Batch Processing:**
> "Find all photos from today and apply a warm tone preset: temperature +200K, tint +10, vibrance +20"

**Advanced Editing:**
> "Apply a gentle S-curve to the main tone curve for more contrast, then warm up the highlights using the red channel curve"

**Organization:**
> "Show me all photos in the 'Portraits' collection taken with a 85mm lens"

**Plugin Metadata:**
> "What's the dominant color of the selected photo?" (using Dominant Color plugin)
> "Find all photos with 'red' as their dominant color"

**Quality Analysis:**
> "Analyze the RGB histogram of the current photo and tell me if it's properly exposed"

### For Developers
Developers get a clean Python API with comprehensive type safety:

```python
from lightroom_sdk.client import LightroomClient

client = LightroomClient()
await client.connect()

# Adjust photo
await client.execute_command('develop_set_parameters', {
    'settings': {
        'Exposure2012': 0.5,
        'Vibrance': 20,
        'Highlights2012': -30
    }
})

# Generate preview
preview = await client.execute_command('preview_generate_current')
print(f"Preview saved to: {preview['file_path']}")

# Query plugin metadata
metadata = await client.execute_command('catalog_get_plugin_metadata', {
    'photo_id': '12345',
    'plugin_id': 'com.example.lrdominantcolor',
    'field_ids': ['dominantColor']
})
print(f"Dominant color: {metadata['metadata']['dominantColor']}")
```

### For End Users (Photographers)
Photographers install the Lightroom plugin and run the MCP server:

1. **One-time Setup**:
   - Install plugin in Lightroom
   - Start Python bridge from Lightroom menu
   - Configure MCP server in Claude Desktop

2. **Daily Workflow**:
   - Work in Lightroom as normal
   - Ask Claude to automate repetitive tasks
   - Review AI-suggested adjustments
   - Apply batch operations across collections

## Value Proposition

### For Professional Photographers
- **Time Savings**: Automate repetitive editing tasks
- **Consistency**: Apply identical adjustments across photo sets
- **AI Assistance**: Get intelligent editing suggestions
- **Batch Efficiency**: Process hundreds of photos in seconds

### For Photo Editors
- **Quality Control**: Automated histogram and exposure analysis
- **Style Matching**: Apply consistent look across projects
- **Organization**: AI-powered catalog management
- **Workflow Automation**: Script complex editing sequences

### For Developers
- **Integration**: Connect Lightroom to modern AI workflows
- **Extensibility**: Build custom tools on top of MCP API
- **Reliability**: Robust error handling and auto-reconnection
- **Documentation**: Clear examples and comprehensive reference

## Differentiators

1. **Complete Lightroom Access**: 114 develop parameters, full catalog operations
2. **MCP Protocol**: Standard interface compatible with AI agent frameworks
3. **Batch Performance**: 10-20x faster than individual operations
4. **Resilient Architecture**: Auto-reconnection, chunked transfer, error recovery
5. **Type Safety**: Structured exceptions and comprehensive validation
6. **Active Development**: Modular design for easy extension and improvement