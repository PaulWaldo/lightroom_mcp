# Project Brief

## Project Name
Lightroom Classic MCP Server

## Core Purpose
Enable AI agents and Large Language Models (LLMs) to programmatically control Adobe Lightroom Classic through the Model Context Protocol (MCP), providing comprehensive access to catalog operations, RAW photo development, preview generation, and histogram analysis.

## Primary Goals

### 1. Comprehensive Lightroom Automation
- Provide AI agents with full access to Lightroom's catalog and development capabilities
- Enable batch processing and automated photo editing workflows
- Support complex RAW image adjustments through 114 parameters across 49 commands

### 2. Efficient Preview & Analysis
- Generate optimized JPEG previews with automatic resizing
- Provide histogram analysis (RGB and luminance) for image quality assessment
- Handle large preview files efficiently with chunked transfer protocol

### 3. Reliable Integration
- Maintain stable connection between Python MCP server and Lightroom plugin
- Implement auto-reconnection and comprehensive error handling
- Ensure type-safe operations with structured exceptions

### 4. Developer-Friendly Architecture
- Modular FastMCP server design for easy extension
- Clear separation of concerns across layers
- Well-documented API with practical examples

## Key Requirements

### Functional Requirements
- **Catalog Operations**: Search photos, manage collections, extract metadata, control selection
- **Develop Tools**: All basic adjustments (exposure, contrast, highlights, shadows, etc.)
- **Advanced Editing**: Tone curves, HSL/color adjustments, detail controls, lens corrections, effects, calibration
- **Batch Operations**: 10-20x performance improvement over individual calls
- **Preview Generation**: Multiple size options with quality control
- **Histogram Analysis**: RGB, luminance, and full spectrum analysis

### Technical Requirements
- Python 3.8+ compatibility
- Lightroom Classic 12.x or newer support
- Dual TCP socket communication (LrSocket limitation)
- JSON-RPC protocol with chunked transfer for large data (>10MB)
- Comprehensive error handling with structured exceptions
- Auto-reconnection capability with timeout handling

### Performance Requirements
- Efficient batch operations for multiple photo adjustments
- Automatic PIL-based resizing for previews
- 100ms delay between commands to prevent race conditions
- Support for large data transfers without blocking

## Project Scope

### In Scope
- All Lightroom Classic catalog operations accessible via Lua API
- Complete develop module parameters (114 parameters)
- Preview generation with resizing and optimization
- Histogram analysis from preview data
- System status and health monitoring
- Error handling and validation

### Out of Scope
- Lightroom Cloud/Mobile integration
- Print module operations
- Web module operations
- Direct file system manipulation
- Image format conversion beyond JPEG preview generation
- Video editing capabilities

## Success Criteria
1. AI agents can successfully execute all common Lightroom workflows
2. Batch operations perform 10-20x faster than individual calls
3. Connection remains stable with automatic recovery from failures
4. All develop parameters work correctly with proper validation
5. Preview generation handles files of any size efficiently
6. Comprehensive error messages guide users to solutions