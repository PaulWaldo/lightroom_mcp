"""
Lens correction tools for develop server
14 tools: lens profiles, perspective, distortion, defringing
"""
from typing import Dict, Any

def setup_lens_corrections_tools(server, execute_command):
    """Setup lens corrections tools (14 tools)"""
    
    @server.tool
    async def develop_adjust_lens_profile_enable(
        enabled: bool
    ) -> Dict[str, Any]:
        """
        Enable or disable lens profile corrections.
        
        Args:
            enabled: Whether to enable lens profile corrections
            
        Returns:
            Lens profile enable status
        """
        await execute_command("setValue", {
            "param": "LensProfileEnable",
            "value": 1 if enabled else 0
        })
        
        return {
            "success": True,
            "parameter": "LensProfileEnable",
            "enabled": enabled
        }
    
    @server.tool
    async def develop_adjust_auto_lateral_ca(
        enabled: bool
    ) -> Dict[str, Any]:
        """
        Enable or disable automatic lateral chromatic aberration correction.
        
        Args:
            enabled: Whether to enable auto lateral CA correction
            
        Returns:
            Auto lateral CA status
        """
        await execute_command("setValue", {
            "param": "AutoLateralCA",
            "value": 1 if enabled else 0
        })
        
        return {
            "success": True,
            "parameter": "AutoLateralCA",
            "enabled": enabled
        }
    
    # Lens profile scaling tools
    lens_profile_params = [
        ("lens_profile_distortion_scale", "LensProfileDistortionScale", 0, 200),
        ("lens_profile_vignetting_scale", "LensProfileVignettingScale", 0, 200)
    ]
    
    for suffix, param_name, min_val, max_val in lens_profile_params:
        _create_lens_tool(server, execute_command, suffix, param_name, min_val, max_val)
    
    # Manual lens corrections
    manual_lens_params = [
        ("lens_manual_distortion", "LensManualDistortion", -100, 100),
        ("defringe_purple_amount", "DefringePurpleAmount", 0, 20),
        ("defringe_green_amount", "DefringeGreenAmount", 0, 20),
        ("lens_vignette_amount", "VignetteAmount", -100, 100),
        ("lens_vignette_midpoint", "VignetteMidpoint", 0, 100)
    ]
    
    for suffix, param_name, min_val, max_val in manual_lens_params:
        _create_lens_tool(server, execute_command, suffix, param_name, min_val, max_val)
    
    # Perspective corrections
    perspective_params = [
        ("perspective_vertical", "PerspectiveVertical", -100, 100),
        ("perspective_horizontal", "PerspectiveHorizontal", -100, 100),
        ("perspective_rotate", "PerspectiveRotate", -10, 10),
        ("perspective_scale", "PerspectiveScale", 50, 150),
        ("straighten_angle", "StraightenAngle", -45, 45)
    ]
    
    for suffix, param_name, min_val, max_val in perspective_params:
        _create_lens_tool(server, execute_command, suffix, param_name, min_val, max_val)

def _create_lens_tool(server, execute_command, suffix: str, param_name: str, min_val: float, max_val: float):
    """Helper to create lens correction tools"""
    
    async def lens_tool(value: float) -> Dict[str, Any]:
        f"""
        Adjust {param_name.lower()} for lens corrections.
        
        Args:
            value: Adjustment value ({min_val} to {max_val})
            
        Returns:
            Updated lens correction value
        """
        if not min_val <= value <= max_val:
            raise ValueError(f"{param_name} must be between {min_val} and {max_val}")
        
        await execute_command("setValue", {
            "param": param_name,
            "value": value
        })
        
        return {
            "success": True,
            "parameter": param_name,
            "value": value
        }
    
    lens_tool.__name__ = f"develop_adjust_{suffix}"
    server.tool(lens_tool)