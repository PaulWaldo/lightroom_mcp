"""
Base classes for modular server components
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from fastmcp import FastMCP
from mcp_server.shared.resilient_client import resilient_client_manager
import logging

logger = logging.getLogger(__name__)

class LightroomServerModule(ABC):
    """Base class for Lightroom server modules"""

    def __init__(self):
        self.server = FastMCP(self.name)
        self._setup_tools()

    @property
    @abstractmethod
    def name(self) -> str:
        """Module name"""
        pass

    @property
    @abstractmethod
    def prefix(self) -> str:
        """Tool prefix for this module"""
        pass

    @abstractmethod
    def _setup_tools(self) -> None:
        """Register all tools for this module"""
        pass

    async def execute_command(
        self,
        command: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a Lightroom command with proper error handling"""
        try:
            # Add module prefix if not present and not a cross-module command
            if not command.startswith(f"{self.prefix}.") and not "." in command:
                command = f"{self.prefix}.{command}"

            logger.debug(f"Executing: {command} with params: {params}")
            
            # Use resilient execution with automatic retry
            result = await resilient_client_manager.execute_with_retry(command, params)
            logger.debug(f"Result: {result}")

            return result
        except Exception as e:
            # Convert Lightroom SDK errors to structured error responses
            logger.error(f"Lightroom command failed: {command} - {e}")
            
            # Check if it's a Lightroom SDK error with structured data
            if hasattr(e, 'code') and hasattr(e, 'details'):
                # This is a structured Lightroom error - preserve the original structure
                error_details = e.details
                error_code = e.code
                error_message = str(e)
                
                # Create a LightroomSDKError-like exception that preserves the structure
                from lightroom_sdk.exceptions import LightroomSDKError
                raise LightroomSDKError(error_message, code=error_code, details=error_details)
            else:
                # This is some other error - wrap it
                error_message = str(e)
                logger.error(f"Non-Lightroom error: {error_message}")
                raise Exception(f"Command execution failed: {error_message}")

class ToolDecorator:
    """Helper for consistent tool decoration across modules"""

    def __init__(self, server: FastMCP, category: str):
        self.server = server
        self.category = category

    def tool(self, func):
        """Decorate a function as a tool with proper naming"""
        # Extract function name and create tool name
        tool_name = f"{self.category}_{func.__name__}"

        # Update function metadata
        func.__name__ = tool_name

        # Register with FastMCP
        return self.server.tool(func)