"""
Resilient client management that handles connection resets gracefully
"""
import logging
import sys
from typing import Optional, Dict, Any
from lightroom_sdk import LightroomClient
import asyncio

# Log to stderr for STDIO compatibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

class ResilientClientManager:
    """Manages the shared Lightroom client with automatic reconnection"""

    def __init__(self):
        self._client: Optional[LightroomClient] = None
        self._last_command_time = 0
        self._reconnect_lock = asyncio.Lock()

    async def get_client(self) -> LightroomClient:
        """Get or create the Lightroom client with automatic reconnection"""
        async with self._reconnect_lock:
            if not self._client:
                logger.info("Creating new Lightroom client...")
                self._client = LightroomClient()
                await self._client.connect()
                return self._client

            # Don't ping - just return the client
            # If it's disconnected, we'll handle it when executing commands
            return self._client

    async def execute_with_retry(
        self,
        command: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """Execute command with automatic reconnection on failure"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                client = await self.get_client()
                return await client.execute_command(command, params)
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # Check if it's a connection error
                if any(err in error_str for err in [
                    'connection reset', 'broken pipe', 'connection lost',
                    'connection closed', 'errno 54', 'errno 32', 'not connected'
                ]):
                    logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
                    
                    # Force reconnection
                    async with self._reconnect_lock:
                        if self._client:
                            try:
                                await self._client.disconnect()
                            except:
                                pass
                        self._client = None
                    
                    if attempt < max_retries - 1:
                        logger.info("Reconnecting...")
                        await asyncio.sleep(0.1)  # Brief delay
                        continue
                
                # Not a connection error, propagate immediately
                raise
        
        # All retries failed
        raise last_error

    async def connect(self) -> None:
        """Initialize connection to Lightroom"""
        try:
            async with self._reconnect_lock:
                if not self._client:
                    self._client = LightroomClient()
                await self._client.connect()
                logger.info("Connected to Lightroom bridge")
        except Exception as e:
            logger.error(f"Failed to connect to Lightroom: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Lightroom"""
        async with self._reconnect_lock:
            if self._client:
                try:
                    await self._client.disconnect()
                    logger.info("Disconnected from Lightroom bridge")
                except Exception as e:
                    logger.error(f"Error during disconnect: {e}")
                finally:
                    self._client = None

# Global resilient client manager instance
resilient_client_manager = ResilientClientManager()