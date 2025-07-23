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

# Create server instance
catalog_server = CatalogServer()