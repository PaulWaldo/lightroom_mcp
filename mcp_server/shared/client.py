"""
Shared Lightroom client management
Single instance shared across all servers
"""
import logging
import sys
from typing import Optional
from lightroom_sdk import LightroomClient
from lightroom_sdk.exceptions import ConnectionError as LRConnectionError

# Log to stderr for STDIO compatibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

class ClientManager:
    """Manages the shared Lightroom client instance"""

    def __init__(self):
        self._client: Optional[LightroomClient] = None

    async def get_client(self) -> LightroomClient:
        """Get or create the Lightroom client"""
        if not self._client:
            self._client = LightroomClient()

        # Ensure connection
        try:
            await self._client.ping()
        except Exception:
            logger.info("Reconnecting to Lightroom...")
            await self._client.connect()

        return self._client

    async def connect(self) -> None:
        """Initialize connection to Lightroom"""
        try:
            self._client = LightroomClient()
            await self._client.connect()
            logger.info("Connected to Lightroom bridge")
        except Exception as e:
            logger.error(f"Failed to connect to Lightroom: {e}")
            # Don't fail - allow reconnection attempts later

    async def disconnect(self) -> None:
        """Disconnect from Lightroom"""
        if self._client:
            try:
                await self._client.disconnect()
                logger.info("Disconnected from Lightroom bridge")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
            finally:
                self._client = None

# Global client manager instance
client_manager = ClientManager()