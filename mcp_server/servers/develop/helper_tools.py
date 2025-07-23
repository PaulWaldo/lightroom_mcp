"""
High-level helper tools for develop server
2 tools: style presets + workflow helpers
"""
from typing import Dict, Any

def setup_helper_tools(server, execute_command):
    """Setup high-level helper tools for common workflows (2 tools)"""
    
    @server.tool
    async def develop_apply_style(
        style: str
    ) -> Dict[str, Any]:
        """
        Apply predefined editing styles.
        
        High-level tool for AI agents to quickly apply
        cohesive looks without individual adjustments.
        
        Args:
            style: Style name - "portrait", "landscape", "blackwhite",
                  "vintage", "modern", "film", "dramatic"
                  
        Returns:
            Applied style settings
        """
        styles = {
            "portrait": {
                "Exposure": 0.3,
                "Highlights": -30,
                "Shadows": 20,
                "Clarity": -10,
                "Vibrance": 15,
                "SaturationAdjustmentOrange": 10,
                "LuminanceAdjustmentOrange": 5
            },
            "landscape": {
                "Exposure": 0.2,
                "Highlights": -50,
                "Shadows": 30,
                "Clarity": 20,
                "Vibrance": 30,
                "Dehaze": 15,
                "SaturationAdjustmentBlue": 20,
                "LuminanceAdjustmentBlue": -10
            },
            "blackwhite": {
                "Saturation": -100,
                "Contrast": 20,
                "Clarity": 25,
                "Highlights": -20,
                "Shadows": 15
            },
            "vintage": {
                "Exposure": 0.2,
                "Contrast": -10,
                "Highlights": -20,
                "Shadows": 30,
                "Vibrance": -20,
                "GrainAmount": 30
            },
            "dramatic": {
                "Exposure": 0.1,
                "Contrast": 40,
                "Highlights": -60,
                "Shadows": 40,
                "Clarity": 30,
                "Vibrance": 20,
                "Dehaze": 25
            }
        }
        
        if style not in styles:
            return {
                "success": False,
                "error": f"Unknown style: {style}",
                "available_styles": list(styles.keys())
            }
        
        # Check if a photo is selected first
        from mcp_server.shared.resilient_client import resilient_client_manager
        client = await resilient_client_manager.get_client()
        selection_result = await client.execute_command("catalog.getSelectedPhotos")
        
        if selection_result.get("count", 0) == 0:
            return {
                "success": False,
                "error": {
                    "code": "NO_PHOTO_SELECTED",
                    "message": "No photo is currently selected. Please select a photo in Lightroom to apply styles.",
                    "severity": "error"
                }
            }
        
        # Get the selected photo ID
        photos = selection_result.get("photos", [])
        selected_photo_id = str(photos[0]["id"])
        
        # Apply the style settings
        await execute_command("applySettings", {
            "photoId": selected_photo_id,
            "settings": styles[style]
        })
        
        return {
            "success": True,
            "style": style,
            "settings_applied": len(styles[style])
        }
    
    @server.tool
    async def develop_get_workflow_suggestions(
        photo_metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Get AI-driven workflow suggestions based on photo analysis.
        
        Analyzes photo characteristics and suggests optimal editing workflow.
        
        Args:
            photo_metadata: Optional photo metadata for better suggestions
            
        Returns:
            Suggested workflow steps and parameters
        """
        # Default workflow suggestions
        suggestions = {
            "quick_workflow": [
                {"step": 1, "tool": "develop_auto_tone", "reason": "Good starting point"},
                {"step": 2, "tool": "develop_adjust_exposure", "reason": "Fine-tune brightness"},
                {"step": 3, "tool": "develop_adjust_vibrance", "reason": "Enhance colors naturally"},
                {"step": 4, "tool": "develop_adjust_clarity", "reason": "Add definition"}
            ],
            "portrait_workflow": [
                {"step": 1, "tool": "develop_apply_style", "params": {"style": "portrait"}},
                {"step": 2, "tool": "develop_adjust_orange_luminance", "reason": "Skin tone enhancement"},
                {"step": 3, "tool": "develop_adjust_sharpen_detail", "reason": "Eye sharpening"}
            ],
            "landscape_workflow": [
                {"step": 1, "tool": "develop_apply_style", "params": {"style": "landscape"}},
                {"step": 2, "tool": "develop_adjust_blue_saturation", "reason": "Sky enhancement"},
                {"step": 3, "tool": "develop_adjust_dehaze", "reason": "Atmospheric clarity"}
            ]
        }
        
        # Analyze metadata if provided
        suggested_workflow = "quick_workflow"
        if photo_metadata:
            # Simple heuristics based on metadata
            focal_length = photo_metadata.get("focalLength", 0)
            iso = photo_metadata.get("iso", 0)
            
            if focal_length > 85:  # Likely portrait
                suggested_workflow = "portrait_workflow"
            elif focal_length < 35:  # Likely landscape
                suggested_workflow = "landscape_workflow"
        
        return {
            "success": True,
            "suggested_workflow": suggested_workflow,
            "steps": suggestions[suggested_workflow],
            "all_workflows": list(suggestions.keys()),
            "metadata_analyzed": photo_metadata is not None
        }