"""
Camera calibration tools for develop server
7 tools: shadow tint + RGB calibration adjustments
"""
from typing import Dict, Any

def setup_calibration_tools(server, execute_command):
    """Setup color calibration tools (7 tools)"""
    
    calibration_params = [
        ("shadow_tint", "ShadowTint"),
        ("calibration_red_hue", "RedHue"),
        ("calibration_red_saturation", "RedSaturation"),
        ("calibration_green_hue", "GreenHue"),
        ("calibration_green_saturation", "GreenSaturation"),
        ("calibration_blue_hue", "BlueHue"),
        ("calibration_blue_saturation", "BlueSaturation")
    ]
    
    for suffix, param_name in calibration_params:
        _create_calibration_tool(server, execute_command, suffix, param_name)

def _create_calibration_tool(server, execute_command, suffix: str, param_name: str):
    """Helper to create calibration tools"""
    
    async def calibration_tool(value: float) -> Dict[str, Any]:
        f"""
        Adjust {param_name.lower()} for color calibration.
        
        Args:
            value: Adjustment value (-100 to +100)
            
        Returns:
            Updated calibration value
        """
        if not -100 <= value <= 100:
            raise ValueError(f"Calibration adjustments must be -100 to +100")
        
        await execute_command("setValue", {
            "param": param_name,
            "value": value
        })
        
        return {
            "success": True,
            "parameter": param_name,
            "value": value
        }
    
    calibration_tool.__name__ = f"develop_adjust_{suffix}"
    server.tool(calibration_tool)