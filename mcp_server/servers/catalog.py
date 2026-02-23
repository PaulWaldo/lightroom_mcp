"""
Catalog server module for photo management
Essential for photo selection and metadata access
"""
from typing import Dict, Any, Optional, List, Union
from mcp_server.shared.base import LightroomServerModule
import logging

logger = logging.getLogger(__name__)

class CatalogServer(LightroomServerModule):
    """Photo catalog operations"""

    @property
    def name(self) -> str:
        return "Lightroom Catalog Tools"

    @property
    def prefix(self) -> str:
        return "catalog"

    def _setup_tools(self):
        """Register catalog tools"""

        @self.server.tool
        async def catalog_get_selected_photos() -> Dict[str, Any]:
            """
            Get currently selected photos in Lightroom.

            Essential for AI agents to know which photo(s) they're working on.

            Returns:
                Selected photos with metadata
            """
            result = await self.execute_command("getSelectedPhotos")

            return {
                "success": True,
                "count": result.get("count", 0),
                "photos": result.get("photos", []),
                "has_selection": result.get("count", 0) > 0
            }

        @self.server.tool
        async def catalog_select_photo(
            photo_id: Union[str, int]
        ) -> Dict[str, Any]:
            """
            Select a specific photo in Lightroom.

            Allows AI agents to change which photo they're editing.

            Args:
                photo_id: Photo ID to select

            Returns:
                Selection confirmation
            """
            await self.execute_command("setSelectedPhotos", {
                "photoIds": [str(photo_id)]
            })

            return {
                "success": True,
                "selected_photo_id": str(photo_id),
                "message": "Photo selected"
            }

        @self.server.tool
        async def catalog_get_all_photos(
            limit: int = 100,
            offset: int = 0
        ) -> Dict[str, Any]:
            """
            Get all photos in the catalog with pagination.

            For AI agents to browse available photos.

            Args:
                limit: Maximum photos to return (default 100)
                offset: Starting position for pagination

            Returns:
                List of photos with metadata
            """
            result = await self.execute_command("getAllPhotos", {
                "limit": limit,
                "offset": offset
            })

            return {
                "success": True,
                "total_count": result.get("totalCount", 0),
                "returned_count": len(result.get("photos", [])),
                "photos": result.get("photos", []),
                "limit": limit,
                "offset": offset,
                "has_more": result.get("totalCount", 0) > offset + limit
            }

        @self.server.tool
        async def catalog_search_photos(
            criteria: Dict[str, Any],
            limit: int = 100
        ) -> Dict[str, Any]:
            """
            Search photos with flexible criteria.

            Powerful search for AI agents to find specific photos.

            Args:
                criteria: Search criteria dict with fields like:
                    - rating: {"min": 3, "max": 5}
                    - captureDate: {"after": "2023-01-01"}
                    - keywords: ["landscape", "sunset"]
                    - fileFormat: "RAW"
                limit: Maximum results

            Returns:
                Matching photos
            """
            result = await self.execute_command("searchPhotos", {
                "criteria": criteria,
                "limit": limit
            })

            return {
                "success": True,
                "count": len(result.get("photos", [])),
                "photos": result.get("photos", []),
                "criteria": criteria
            }

        @self.server.tool
        async def catalog_get_photo_metadata(
            photo_id: Union[str, int]
        ) -> Dict[str, Any]:
            """
            Get comprehensive metadata for a photo.

            Detailed information for AI analysis.

            Args:
                photo_id: Photo ID

            Returns:
                Complete photo metadata including EXIF data
            """
            result = await self.execute_command("getPhotoMetadata", {
                "photoId": str(photo_id)
            })

            return {
                "success": True,
                "photo_id": str(photo_id),
                "metadata": result
            }

        @self.server.tool
        async def catalog_get_collections() -> Dict[str, Any]:
            """
            Get all collections in the catalog.

            For AI agents to understand photo organization.

            Returns:
                List of collections with photo counts
            """
            result = await self.execute_command("getCollections")

            return {
                "success": True,
                "count": len(result.get("collections", [])),
                "collections": result.get("collections", [])
            }

        @self.server.tool
        async def catalog_get_keywords() -> Dict[str, Any]:
            """
            Get all keywords used in the catalog.

            Helps AI agents understand photo categorization.

            Returns:
                Keywords with usage counts
            """
            result = await self.execute_command("getKeywords")

            return {
                "success": True,
                "count": len(result.get("keywords", [])),
                "keywords": result.get("keywords", [])
            }

        @self.server.tool
        async def catalog_get_folders() -> Dict[str, Any]:
            """
            Get all folders in the catalog.

            For AI agents to understand folder organization.

            Returns:
                Folder hierarchy with photo counts
            """
            result = await self.execute_command("getFolders")

            return {
                "success": True,
                "count": len(result.get("folders", [])),
                "folders": result.get("folders", [])
            }

        @self.server.tool
        async def catalog_set_rating(
            photo_id: Union[str, int],
            rating: int
        ) -> Dict[str, Any]:
            """
            Set rating for a photo.

            Allows AI agents to rate photos based on analysis.

            Args:
                photo_id: Photo ID
                rating: Rating (0-5 stars)

            Returns:
                Rating confirmation
            """
            if not 0 <= rating <= 5:
                raise ValueError(f"Rating must be 0-5, got {rating}")

            await self.execute_command("setPhotoRating", {
                "photoId": str(photo_id),
                "rating": rating
            })

            return {
                "success": True,
                "photo_id": str(photo_id),
                "rating": rating,
                "message": f"Photo rated {rating} stars"
            }

        @self.server.tool
        async def catalog_add_keywords(
            photo_id: Union[str, int],
            keywords: List[str]
        ) -> Dict[str, Any]:
            """
            Add keywords to a photo.

            Allows AI agents to tag photos based on content analysis.

            Args:
                photo_id: Photo ID
                keywords: List of keywords to add

            Returns:
                Keywords confirmation
            """
            await self.execute_command("addPhotoKeywords", {
                "photoId": str(photo_id),
                "keywords": keywords
            })

            return {
                "success": True,
                "photo_id": str(photo_id),
                "keywords_added": keywords,
                "count": len(keywords)
            }

        @self.server.tool
        async def catalog_get_photo_info(
            photo_id: Union[str, int]
        ) -> Dict[str, Any]:
            """
            Get basic photo information.

            Quick access to essential photo details.

            Args:
                photo_id: Photo ID

            Returns:
                Basic photo information
            """
            result = await self.execute_command("getPhotoInfo", {
                "photoId": str(photo_id)
            })

            return {
                "success": True,
                "photo_id": str(photo_id),
                "info": result
            }

        @self.server.tool
        async def catalog_get_plugin_metadata(
            photo_id: Union[str, int],
            plugin_id: str,
            field_ids: List[str]
        ) -> Dict[str, Any]:
            """
            Get third-party plugin metadata for a photo.

            Access custom metadata from plugins like Dominant Color,
            Jeffrey's Plugins, LensTagger, etc. This allows AI agents
            to read metadata fields defined by other Lightroom plugins.

            Args:
                photo_id: Photo ID to get metadata from
                plugin_id: Plugin identifier (e.g., 'com.frostcat.dominantcolor')
                field_ids: List of metadata field IDs to retrieve

            Returns:
                Plugin metadata values for each requested field

            Example:
                # Get dominant color from Dominant Color plugin
                result = await catalog_get_plugin_metadata(
                    photo_id='12345',
                    plugin_id='com.frostcat.dominantcolor',
                    field_ids=['dominantColor', 'colorPalette']
                )
            """
            result = await self.execute_command("plugin.getMetadata", {
                "photoId": str(photo_id),
                "pluginId": plugin_id,
                "fieldIds": field_ids
            })

            metadata = result.get("metadata", {})

            # Detect empty metadata and provide helpful guidance
            response = {
                "success": True,
                "photo_id": result.get("photoId"),
                "plugin_id": result.get("pluginId"),
                "metadata": metadata
            }

            if not metadata or all(v is None for v in metadata.values()):
                response["warning"] = {
                    "message": "No metadata found. This may indicate incorrect plugin_id or field_ids.",
                    "suggestions": [
                        "Verify the plugin ID is correct (case-sensitive)",
                        "Check that field_ids match the internal plugin field names (not display labels)",
                        "Use catalog_discover_plugin_metadata to find available plugins and fields",
                        "Example: field name might be 'color' not 'Color', 'dominantColor' not 'Dominant Color'"
                    ],
                    "next_steps": [
                        f"Try: catalog_discover_plugin_metadata(photo_id='{photo_id}')"
                    ]
                }

            return response

        @self.server.tool
        async def catalog_discover_plugin_metadata(
            photo_id: Union[str, int]
        ) -> Dict[str, Any]:
            """
            Discover available plugin metadata for a photo.

            Inspects a photo to find all plugins that have metadata
            and lists their available field IDs with sample values.
            Essential for LLMs to discover correct plugin IDs and field names.

            Args:
                photo_id: Photo ID to inspect

            Returns:
                Dictionary of plugins with their available fields and values

            Example:
                # Discover what plugins have metadata for this photo
                result = await catalog_discover_plugin_metadata(photo_id='12345')
                # Returns:
                # {
                #   "plugins": {
                #     "com.frostcat.dominantcolor": {
                #       "fields": {
                #         "color": "Black",
                #         "treatment": "Color",
                #         "brightness": "Dark"
                #       }
                #     }
                #   }
                # }
            """
            result = await self.execute_command("plugin.discoverMetadata", {
                "photoId": str(photo_id)
            })

            plugins = result.get("plugins", {})

            return {
                "success": True,
                "photo_id": str(photo_id),
                "plugins": plugins,
                "plugin_count": len(plugins),
                "message": f"Found metadata from {len(plugins)} plugin(s)",
                "usage_tip": "Use the plugin IDs and field names from this result with catalog_get_plugin_metadata"
            }

        @self.server.tool
        async def catalog_batch_get_plugin_metadata(
            photo_ids: List[Union[str, int]],
            plugin_id: str,
            field_ids: List[str]
        ) -> Dict[str, Any]:
            """
            Batch get plugin metadata for multiple photos.

            Efficient way to retrieve third-party plugin metadata
            for many photos at once (10-20x faster than individual calls).
            Essential for AI agents working with large photo collections.

            Args:
                photo_ids: List of photo IDs
                plugin_id: Plugin identifier (e.g., 'com.example.plugin')
                field_ids: List of metadata field IDs to retrieve

            Returns:
                Metadata organized by photo ID

            Example:
                # Batch get dominant colors for 100 photos
                result = await catalog_batch_get_plugin_metadata(
                    photo_ids=photo_ids[:100],
                    plugin_id='com.frostcat.dominantcolor',
                    field_ids=['dominantColor']
                )
            """
            result = await self.execute_command("plugin.batchGetMetadata", {
                "photoIds": [str(pid) for pid in photo_ids],
                "pluginId": plugin_id,
                "fieldIds": field_ids
            })

            return {
                "success": True,
                "plugin_id": result.get("pluginId"),
                "field_ids": result.get("fieldIds", []),
                "metadata": result.get("metadata", {}),
                "requested": result.get("requested", 0),
                "found": result.get("found", 0)
            }

        @self.server.tool
        async def catalog_search_by_plugin_property(
            plugin_id: str,
            field_id: str,
            value: Optional[Any] = None
        ) -> Dict[str, Any]:
            """
            Search for photos by third-party plugin property.

            Find photos that have specific plugin metadata values.
            Useful for content-based organization and filtering.

            Args:
                plugin_id: Plugin identifier
                field_id: Metadata field ID to search
                value: Optional specific value to search for (if None, finds any photo with this field)

            Returns:
                Matching photos with basic info

            Example:
                # Find all photos with blue dominant color
                result = await catalog_search_by_plugin_property(
                    plugin_id='com.frostcat.dominantcolor',
                    field_id='dominantColor',
                    value='blue'
                )

                # Find all photos that have been tagged by a plugin
                result = await catalog_search_by_plugin_property(
                    plugin_id='com.example.tagger',
                    field_id='tagged'
                )
            """
            result = await self.execute_command("plugin.findPhotosWithProperty", {
                "pluginId": plugin_id,
                "fieldId": field_id,
                "value": value
            })

            return {
                "success": True,
                "plugin_id": result.get("pluginId"),
                "field_id": result.get("fieldId"),
                "search_value": result.get("searchValue"),
                "photos": result.get("photos", []),
                "count": result.get("count", 0)
            }

# Create server instance
catalog_server = CatalogServer()
