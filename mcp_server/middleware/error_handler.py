"""
Unified error handling for all server modules
"""
from fastmcp import FastMCP
from fastmcp.exceptions import McpError
from lightroom_sdk.exceptions import (
    LightroomSDKError,
    PhotoNotSelectedError,
    ParameterOutOfRangeError,
    ConnectionError as LRConnectionError,
    TimeoutError as LRTimeoutError
)
import logging

logger = logging.getLogger(__name__)

def setup_error_handlers(server: FastMCP):
    """Configure error handlers for any FastMCP server"""

    @server.exception_handler(PhotoNotSelectedError)
    async def handle_photo_not_selected(exc: PhotoNotSelectedError):
        """Handle photo selection errors"""
        logger.warning(f"Photo not selected: {exc}")
        raise McpError(
            "NO_PHOTO_SELECTED",
            "No photo selected in Lightroom. Please select a photo and try again."
        )

    @server.exception_handler(ParameterOutOfRangeError)
    async def handle_parameter_range(exc: ParameterOutOfRangeError):
        """Handle parameter validation errors"""
        logger.warning(f"Parameter out of range: {exc}")
        raise McpError(
            "INVALID_PARAMETER_VALUE",
            str(exc)
        )

    @server.exception_handler(LRConnectionError)
    async def handle_connection_error(exc: LRConnectionError):
        """Handle connection errors"""
        logger.error(f"Connection error: {exc}")
        raise McpError(
            "CONNECTION_FAILED",
            "Failed to connect to Lightroom. Please ensure Lightroom is running with the plugin active."
        )

    @server.exception_handler(LightroomSDKError)
    async def handle_sdk_error(exc: LightroomSDKError):
        """Handle generic SDK errors"""
        logger.error(f"SDK error: {exc}")
        raise McpError(
            exc.code or "SDK_ERROR",
            str(exc)
        )