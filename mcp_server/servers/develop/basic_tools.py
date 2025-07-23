"""
Basic develop adjustment tools
15 core tools for essential photo editing
"""
from typing import Dict, Any, Optional
from lightroom_sdk.types.develop import DEVELOP_PARAMETER_RANGES

def setup_basic_tools(server, execute_command):
    """Setup basic adjustment tools (15 tools)"""

    @server.tool
    async def develop_adjust_exposure(
        value: float,
        photo_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Adjust exposure for a photo.

        This is one of the most important tools for AI photo editing.
        Affects overall image brightness.

        Args:
            value: Exposure adjustment (-5 to +5)
            photo_id: Photo ID (uses current selection if not provided)

        Returns:
            Updated exposure value and photo ID
        """
        if not -5 <= value <= 5:
            raise ValueError(f"Exposure must be between -5 and 5, got {value}")

        params = {"param": "Exposure", "value": value}
        if photo_id:
            params["photoId"] = photo_id

        result = await execute_command("setValue", params)

        return {
            "success": True,
            "parameter": "Exposure",
            "value": value,
            "photo_id": result.get("photoId")
        }

    async def _check_photo_selection() -> Dict[str, Any]:
        """Helper to check if a photo is selected and provide proper error"""
        try:
            # Check if any photo is selected using catalog command
            from mcp_server.shared.resilient_client import resilient_client_manager
            client = await resilient_client_manager.get_client()
            result = await client.execute_command("catalog.getSelectedPhotos")

            if result.get("count", 0) == 0:
                return {
                    "success": False,
                    "error": {
                        "code": "NO_PHOTO_SELECTED",
                        "message": "No photo is currently selected. Please select a photo in Lightroom to access develop parameters.",
                        "severity": "error"
                    }
                }

            return {
                "success": True,
                "selected_count": result.get("count", 0),
                "photos": result.get("photos", [])
            }
        except Exception as e:
            return {
                "success": False,
                "error": {
                    "code": "PHOTO_SELECTION_CHECK_FAILED",
                    "message": f"Could not check photo selection: {str(e)}",
                    "severity": "error"
                }
            }

    @server.tool
    async def develop_get_current_settings(
        photo_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get all current develop settings for the currently selected photo.

        Note: Requires a photo to be selected in Lightroom.

        Essential for AI agents to understand current photo state
        before making adjustments.

        Args:
            photo_id: Photo ID (ignored - uses current selection)

        Returns:
            All develop parameters with current values or error if no photo selected
        """
        # Check if a photo is selected first
        selection_check = await _check_photo_selection()
        if not selection_check.get("success"):
            return selection_check

        # Get the selected photo ID
        photos = selection_check.get("photos", [])
        if not photos:
            return {
                "success": False,
                "error": {
                    "code": "NO_PHOTO_SELECTED",
                    "message": "No photo is currently selected. Please select a photo in Lightroom to get develop settings.",
                    "severity": "error"
                }
            }

        selected_photo_id = str(photos[0]["id"])

        try:
            result = await execute_command("getSettings", {"photoId": selected_photo_id})
            settings = result.get("settings", {})

            return {
                "success": True,
                "photo_id": result.get("photoId"),
                "settings": {
                    "basic": {
                        k: v for k, v in settings.items()
                        if k in ["Exposure", "Contrast", "Highlights", "Shadows",
                                "Whites", "Blacks", "Clarity", "Vibrance", "Saturation"]
                    },
                    "tone": {
                        k: v for k, v in settings.items()
                        if k.startswith("Parametric") or "Tone" in k
                    },
                    "color": {
                        k: v for k, v in settings.items()
                        if "Adjustment" in k or "ColorGrade" in k
                    },
                    "detail": {
                        k: v for k, v in settings.items()
                        if k.startswith("Sharpen") or "Noise" in k
                    },
                    "all": settings
                }
            }
        except Exception as e:
            # Check if this is a structured Lightroom error
            if hasattr(e, 'code') and hasattr(e, 'details'):
                # Extract the structured error details from Lightroom
                error_details = e.details
                return {
                    "success": False,
                    "error": {
                        "code": error_details.get('code', 'LIGHTROOM_ERROR'),
                        "message": error_details.get('message', str(e)),
                        "severity": error_details.get('severity', 'error')
                    }
                }
            else:
                # Return generic error format for other failures
                return {
                    "success": False,
                    "error": {
                        "code": "DEVELOP_SETTINGS_FAILED",
                        "message": f"Could not retrieve develop settings: {str(e)}",
                        "severity": "error"
                    }
                }

    @server.tool
    async def develop_set_parameters(
        settings: Dict[str, float],
        photo_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply multiple develop settings at once.

        Key tool for AI agents to apply comprehensive edits
        efficiently in a single operation. Requires a photo to be selected.

        Args:
            settings: Dictionary of parameter:value pairs
            photo_id: Photo ID (ignored - uses current selection)

        Returns:
            Applied settings confirmation or error if no photo selected
        """
        # Check if a photo is selected first
        selection_check = await _check_photo_selection()
        if not selection_check.get("success"):
            return selection_check

        # Get the selected photo ID
        photos = selection_check.get("photos", [])
        if not photos:
            return {
                "success": False,
                "error": {
                    "code": "NO_PHOTO_SELECTED",
                    "message": "No photo is currently selected. Please select a photo in Lightroom to apply develop settings.",
                    "severity": "error"
                }
            }

        selected_photo_id = str(photos[0]["id"])

        # Validate settings
        for param, value in settings.items():
            if param in DEVELOP_PARAMETER_RANGES:
                min_val, max_val = DEVELOP_PARAMETER_RANGES[param]
                if not min_val <= value <= max_val:
                    return {
                        "success": False,
                        "error": {
                            "code": "INVALID_PARAM_VALUE",
                            "message": f"Parameter '{param}' value {value} outside valid range [{min_val}, {max_val}]",
                            "severity": "error"
                        }
                    }

        # Separate Temperature and Tint from other settings (they must be set individually)
        individual_params = {}
        bulk_settings = {}
        
        for param, value in settings.items():
            if param in ["Temperature", "Tint"]:
                individual_params[param] = value
            else:
                bulk_settings[param] = value

        try:
            applied_count = 0
            
            # Apply bulk settings first (if any)
            if bulk_settings:
                params = {
                    "photoId": selected_photo_id,
                    "settings": bulk_settings
                }
                result = await execute_command("applySettings", params)
                applied_count += len(bulk_settings)
            
            # Apply Temperature and Tint individually
            for param, value in individual_params.items():
                params = {
                    "param": param,
                    "value": value,
                    "photoId": selected_photo_id
                }
                await execute_command("setValue", params)
                applied_count += 1

            return {
                "success": True,
                "applied_count": len(settings),
                "photo_id": result.get("photoId", selected_photo_id),
                "settings": settings
            }
        except Exception as e:
            # Check if this is a structured Lightroom error
            if hasattr(e, 'code') and hasattr(e, 'details'):
                # Extract the structured error details from Lightroom
                error_details = e.details
                return {
                    "success": False,
                    "error": {
                        "code": error_details.get('code', 'LIGHTROOM_ERROR'),
                        "message": error_details.get('message', str(e)),
                        "severity": error_details.get('severity', 'error')
                    }
                }
            else:
                # Return generic error format for other failures
                return {
                    "success": False,
                    "error": {
                        "code": "DEVELOP_APPLY_FAILED",
                        "message": f"Could not apply develop settings: {str(e)}",
                        "severity": "error"
                    }
                }

    @server.tool
    async def develop_auto_tone() -> Dict[str, Any]:
        """
        Apply Lightroom's automatic tone adjustments.

        Good starting point for AI agents before fine-tuning.
        Analyzes the image and sets optimal exposure, highlights,
        shadows, whites, and blacks.

        Returns:
            Applied auto settings
        """
        result = await execute_command("setAutoTone")

        # Get new settings after auto tone
        new_settings_result = await execute_command("getSettings")
        settings = new_settings_result.get("settings", {})
        basic_settings = {
            k: v for k, v in settings.items()
            if k in ["Exposure", "Contrast", "Highlights", "Shadows",
                    "Whites", "Blacks", "Clarity", "Vibrance", "Saturation"]
        }

        return {
            "success": True,
            "message": "Auto tone applied",
            "new_settings": basic_settings
        }

    @server.tool
    async def develop_reset_all() -> Dict[str, Any]:
        """
        Reset all develop adjustments to default.

        Useful for AI agents to start fresh or undo all changes.

        Returns:
            Reset confirmation
        """
        await execute_command("resetAllDevelopAdjustments")

        return {
            "success": True,
            "message": "All develop adjustments reset to default"
        }

    @server.tool
    async def develop_set_parameter(
        parameter: str,
        value: float,
        photo_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Set any develop parameter by name.

        Generic tool for parameters without dedicated tools.
        See API_DEVELOP_REFERENCE.md for all 114 parameters.
        Requires a photo to be selected in Lightroom.

        Args:
            parameter: Parameter name (e.g., "Texture", "Dehaze")
            value: New value (check ranges in documentation)
            photo_id: Photo ID (ignored - uses current selection)

        Returns:
            Updated parameter confirmation or error if no photo selected
        """
        # Check if a photo is selected first
        selection_check = await _check_photo_selection()
        if not selection_check.get("success"):
            return selection_check

        # Get the selected photo ID
        photos = selection_check.get("photos", [])
        if not photos:
            return {
                "success": False,
                "error": {
                    "code": "NO_PHOTO_SELECTED",
                    "message": "No photo is currently selected. Please select a photo in Lightroom to set develop parameters.",
                    "severity": "error"
                }
            }

        selected_photo_id = str(photos[0]["id"])

        # Validate parameter range
        if parameter in DEVELOP_PARAMETER_RANGES:
            min_val, max_val = DEVELOP_PARAMETER_RANGES[parameter]
            if not min_val <= value <= max_val:
                return {
                    "success": False,
                    "error": {
                        "code": "INVALID_PARAM_VALUE",
                        "message": f"Parameter '{parameter}' value {value} outside valid range [{min_val}, {max_val}]",
                        "severity": "error"
                    }
                }

        # Prepare parameters with required photoId
        params = {
            "param": parameter,
            "value": value,
            "photoId": selected_photo_id
        }

        try:
            result = await execute_command("setValue", params)

            return {
                "success": True,
                "parameter": parameter,
                "value": value,
                "photo_id": result.get("photoId", selected_photo_id)
            }
        except Exception as e:
            # Check if this is a structured Lightroom error
            if hasattr(e, 'code') and hasattr(e, 'details'):
                # Extract the structured error details from Lightroom
                error_details = e.details
                return {
                    "success": False,
                    "error": {
                        "code": error_details.get('code', 'LIGHTROOM_ERROR'),
                        "message": error_details.get('message', str(e)),
                        "severity": error_details.get('severity', 'error')
                    }
                }
            else:
                # Return generic error format for other failures
                return {
                    "success": False,
                    "error": {
                        "code": "DEVELOP_SET_PARAM_FAILED",
                        "message": f"Could not set develop parameter: {str(e)}",
                        "severity": "error"
                    }
                }

    # Create individual tools for common parameters
    basic_params = [
        ("contrast", "Contrast", -100, 100),
        ("highlights", "Highlights", -100, 100),
        ("shadows", "Shadows", -100, 100),
        ("whites", "Whites", -100, 100),
        ("blacks", "Blacks", -100, 100),
        ("clarity", "Clarity", -100, 100),
        ("vibrance", "Vibrance", -100, 100),
        ("saturation", "Saturation", -100, 100),
        ("temperature", "Temperature", 2000, 50000),
        ("tint", "Tint", -150, 150),
        ("texture", "Texture", -100, 100),
        ("dehaze", "Dehaze", -100, 100)
    ]

    for param_suffix, param_name, min_val, max_val in basic_params:
        _create_basic_adjustment_tool(server, execute_command, param_suffix, param_name, min_val, max_val)

def _create_basic_adjustment_tool(server, execute_command, suffix: str, param_name: str, min_val: float, max_val: float):
    """Helper to create basic adjustment tools"""

    # Use factory function to avoid closure issues
    def make_adjustment_tool(param_fixed: str, min_fixed: float, max_fixed: float):
        async def adjustment_tool(
            value: float,
            photo_id: Optional[str] = None
        ) -> Dict[str, Any]:
            f"""
            Adjust {param_fixed.lower()} for a photo.

            Args:
                value: {param_fixed} adjustment ({min_fixed} to {max_fixed})
                photo_id: Photo ID (uses current selection if not provided)

            Returns:
                Updated {param_fixed.lower()} value and photo ID
            """
            if not min_fixed <= value <= max_fixed:
                raise ValueError(f"{param_fixed} must be between {min_fixed} and {max_fixed}, got {value}")

            params = {"param": param_fixed, "value": value}
            if photo_id:
                params["photoId"] = photo_id

            result = await execute_command("setValue", params)

            return {
                "success": True,
                "parameter": param_fixed,
                "value": value,
                "photo_id": result.get("photoId")
            }
        return adjustment_tool

    tool_func = make_adjustment_tool(param_name, min_val, max_val)
    tool_func.__name__ = f"develop_adjust_{suffix}"
    server.tool(tool_func)