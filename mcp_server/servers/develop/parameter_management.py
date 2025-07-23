"""
Parameter management tools for develop server
8 core tools for parameter introspection and batch operations
"""
from typing import Dict, Any, Optional, List, Union
from lightroom_sdk.types.develop import DEVELOP_PARAMETER_RANGES

def setup_parameter_management_tools(server, execute_command):
    """Setup parameter management tools (8 tools)"""
    
    @server.tool
    async def develop_get_range(
        parameter: str
    ) -> Dict[str, Any]:
        """
        Get valid range for a develop parameter.
        
        Note: This tool can work without a photo selected by using fallback ranges.
        
        Args:
            parameter: Parameter name (e.g., "Exposure", "Contrast")
            
        Returns:
            Parameter range information with min/max values
        """
        try:
            # Try to get range from Lightroom first
            result = await execute_command("getRange", {
                "param": parameter
            })
            
            return {
                "success": True,
                "parameter": parameter,
                "min": result.get("min"),
                "max": result.get("max"),
                "type": result.get("type", "number"),
                "source": "lightroom"
            }
        except Exception as e:
            # If there's an error (like missing photo ID), provide fallback ranges
            # from our known parameter ranges - this is still useful for UI validation
            from lightroom_sdk.types.develop import DEVELOP_PARAMETER_RANGES
            
            if parameter in DEVELOP_PARAMETER_RANGES:
                min_val, max_val = DEVELOP_PARAMETER_RANGES[parameter]
                return {
                    "success": True,
                    "parameter": parameter,
                    "min": min_val,
                    "max": max_val,
                    "type": "number",
                    "source": "fallback_ranges",
                    "note": "Using fallback ranges (Lightroom may require photo selection for live ranges)"
                }
            else:
                return {
                    "success": False,
                    "parameter": parameter,
                    "error": f"Unknown parameter '{parameter}' and Lightroom error: {str(e)}"
                }
    
    @server.tool
    async def develop_reset_to_default(
        parameter: str,
        photo_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reset a parameter to its default value.
        
        Args:
            parameter: Parameter name to reset
            photo_id: Photo ID (uses current selection if not provided)
            
        Returns:
            Reset confirmation with new default value
        """
        params = {"param": parameter}
        if photo_id:
            params["photoId"] = photo_id
            
        result = await execute_command("resetToDefault", params)
        
        return {
            "success": True,
            "parameter": parameter,
            "default_value": result.get("value"),
            "photo_id": result.get("photoId")
        }
    
    @server.tool
    async def develop_set_auto_white_balance(
        photo_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply automatic white balance adjustment.
        
        Analyzes the image and sets optimal Temperature and Tint.
        
        Args:
            photo_id: Photo ID (uses current selection if not provided)
            
        Returns:
            Applied white balance settings
        """
        params = {}
        if photo_id:
            params["photoId"] = photo_id
            
        result = await execute_command("setAutoWhiteBalance", params)
        
        return {
            "success": True,
            "message": "Auto white balance applied",
            "temperature": result.get("temperature"),
            "tint": result.get("tint"),
            "photo_id": result.get("photoId")
        }
    
    @server.tool
    async def develop_get_process_version(
        photo_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get current RAW process version for a photo.
        
        Args:
            photo_id: Photo ID (uses current selection if not provided)
            
        Returns:
            Current process version information
        """
        params = {}
        if photo_id:
            params["photoId"] = photo_id
            
        result = await execute_command("getProcessVersion", params)
        
        return {
            "success": True,
            "process_version": result.get("version"),
            "process_name": result.get("name"),
            "photo_id": result.get("photoId")
        }
    
    @server.tool
    async def develop_set_process_version(
        version: Union[int, str],
        photo_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Set RAW process version for a photo.
        
        Args:
            version: Process version (2003, 2010, 2012, 2015, 2018, 2021)
            photo_id: Photo ID (uses current selection if not provided)
            
        Returns:
            Updated process version confirmation
        """
        params = {"version": version}
        if photo_id:
            params["photoId"] = photo_id
            
        result = await execute_command("setProcessVersion", params)
        
        return {
            "success": True,
            "process_version": result.get("version"),
            "process_name": result.get("name"),
            "photo_id": result.get("photoId")
        }
    
    @server.tool
    async def develop_get_available_parameters() -> Dict[str, Any]:
        """
        Get list of all available develop parameters from the known DEVELOP_PARAMETER_RANGES.
        
        Returns:
            Complete list of parameters organized by category
        """
        # Since develop.getAvailableParameters doesn't exist in the Lightroom plugin,
        # we return the known parameters from our validation ranges
        from lightroom_sdk.types.develop import DEVELOP_PARAMETER_RANGES
        
        parameters = list(DEVELOP_PARAMETER_RANGES.keys())
        
        # Organize by basic categories
        categories = {
            "basic": ["Temperature", "Tint", "Exposure", "Contrast", "Highlights", "Shadows", "Whites", "Blacks"],
            "tone": ["Brightness", "Clarity", "Dehaze", "Vibrance", "Saturation"],
            "curves": ["ParametricDarks", "ParametricLights", "ParametricShadows", "ParametricHighlights"],
            "hsl": [p for p in parameters if p.startswith(("HueAdjustment", "SaturationAdjustment", "LuminanceAdjustment"))],
            "effects": [p for p in parameters if p.startswith(("PostCropVignette", "Grain"))],
            "detail": [p for p in parameters if p.startswith(("Sharpness", "LuminanceSmoothing", "ColorNoiseReduction"))],
            "lens": [p for p in parameters if p.startswith(("LensProfile", "Perspective", "Defringe"))],
            "calibration": [p for p in parameters if p.startswith(("ShadowTint", "RedHue", "GreenHue", "BlueHue"))],
            "color_grading": [p for p in parameters if p.startswith(("SplitToning", "ColorGrade"))]
        }
        
        return {
            "success": True,
            "parameter_count": len(parameters),
            "categories": categories,
            "all_parameters": parameters,
            "note": "Parameters from validated DEVELOP_PARAMETER_RANGES (Lightroom plugin doesn't expose getAvailableParameters)"
        }
    
    @server.tool
    async def develop_batch_apply_settings(
        photo_ids: List[str],
        settings: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Apply develop settings to multiple photos efficiently.
        
        Args:
            photo_ids: List of photo IDs to apply settings to
            settings: Dictionary of parameter:value pairs
            
        Returns:
            Batch application results
        """
        # Validate settings first
        for param, value in settings.items():
            if param in DEVELOP_PARAMETER_RANGES:
                min_val, max_val = DEVELOP_PARAMETER_RANGES[param]
                if not min_val <= value <= max_val:
                    raise ValueError(
                        f"{param} value {value} outside range [{min_val}, {max_val}]"
                    )
        
        # Separate Temperature and Tint from other settings (they must be set individually)
        individual_params = {}
        bulk_settings = {}
        
        for param, value in settings.items():
            if param in ["Temperature", "Tint"]:
                individual_params[param] = value
            else:
                bulk_settings[param] = value
        
        # Apply bulk settings first (if any)
        total_processed = 0
        total_errors = []
        processing_time = 0
        
        if bulk_settings:
            result = await execute_command("batchApplySettings", {
                "photoIds": photo_ids,
                "settings": bulk_settings
            })
            total_processed = result.get("processed", len(photo_ids))
            total_errors.extend(result.get("errors", []))
            processing_time += result.get("processingTime", 0)
        
        # Apply Temperature and Tint individually to each photo
        if individual_params:
            for photo_id in photo_ids:
                for param, value in individual_params.items():
                    try:
                        await execute_command("setValue", {
                            "param": param,
                            "value": value,
                            "photoId": photo_id
                        })
                    except Exception as e:
                        total_errors.append({
                            "photoId": photo_id,
                            "parameter": param,
                            "error": str(e)
                        })
            if not bulk_settings:
                total_processed = len(photo_ids)
        
        return {
            "success": True,
            "photos_processed": total_processed,
            "settings_applied": len(settings),
            "processing_time": processing_time,
            "errors": total_errors,
            "bulk_settings_count": len(bulk_settings),
            "individual_settings_count": len(individual_params)
        }
    
    @server.tool
    async def develop_batch_get_settings(
        photo_ids: List[str],
        parameters: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get develop settings from multiple photos efficiently.
        
        Args:
            photo_ids: List of photo IDs to get settings from
            parameters: Specific parameters to retrieve (all if None)
            
        Returns:
            Batch settings retrieval results
        """
        params = {"photoIds": photo_ids}
        if parameters:
            params["parameters"] = parameters
            
        result = await execute_command("batchGetSettings", params)
        
        return {
            "success": True,
            "photos_processed": result.get("processed", len(photo_ids)),
            "settings_per_photo": result.get("settings", {}),
            "processing_time": result.get("processingTime")
        }