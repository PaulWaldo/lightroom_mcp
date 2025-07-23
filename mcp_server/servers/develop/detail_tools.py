"""
Detail and sharpening tools for develop server
8 tools: sharpening controls + noise reduction
"""
from typing import Dict, Any

def setup_detail_tools(server, execute_command):
    """Setup detail and noise reduction tools (8 tools)"""
    
    # Basic detail parameters
    detail_params = [
        ("sharpness", "Sharpness", 0, 150),
        ("sharpen_radius", "SharpenRadius", 0.5, 3.0),
        ("sharpen_detail", "SharpenDetail", 0, 100),
        ("luminance_smoothing", "LuminanceSmoothing", 0, 100),
        ("color_noise_reduction", "ColorNoiseReduction", 0, 100)
    ]
    
    for suffix, param_name, min_val, max_val in detail_params:
        _create_detail_tool(server, execute_command, suffix, param_name, min_val, max_val)
    
    # Advanced detail tools
    @server.tool
    async def develop_adjust_sharpen_edge_masking(value: float) -> Dict[str, Any]:
        """
        Adjust sharpening edge masking.
        
        Controls which edges receive sharpening.
        
        Args:
            value: Edge masking amount (0 to 100)
            
        Returns:
            Updated edge masking value
        """
        if not 0 <= value <= 100:
            raise ValueError("Edge masking must be 0 to 100")
        
        await execute_command("setValue", {
            "param": "SharpenEdgeMasking",
            "value": value
        })
        
        return {
            "success": True,
            "parameter": "SharpenEdgeMasking",
            "value": value
        }
    
    @server.tool
    async def develop_adjust_luminance_noise_detail(value: float) -> Dict[str, Any]:
        """
        Adjust luminance noise reduction detail.
        
        Controls detail preservation in noise reduction.
        
        Args:
            value: Detail preservation (0 to 100)
            
        Returns:
            Updated noise reduction detail value
        """
        if not 0 <= value <= 100:
            raise ValueError("Noise reduction detail must be 0 to 100")
        
        await execute_command("setValue", {
            "param": "LuminanceNoiseReductionDetail",
            "value": value
        })
        
        return {
            "success": True,
            "parameter": "LuminanceNoiseReductionDetail",
            "value": value
        }
    
    @server.tool
    async def develop_adjust_color_noise_detail(value: float) -> Dict[str, Any]:
        """
        Adjust color noise reduction detail.
        
        Controls detail preservation in color noise reduction.
        
        Args:
            value: Detail preservation (0 to 100)
            
        Returns:
            Updated color noise detail value
        """
        if not 0 <= value <= 100:
            raise ValueError("Color noise detail must be 0 to 100")
        
        await execute_command("setValue", {
            "param": "ColorNoiseReductionDetail",
            "value": value
        })
        
        return {
            "success": True,
            "parameter": "ColorNoiseReductionDetail",
            "value": value
        }

def _create_detail_tool(server, execute_command, suffix: str, param_name: str, min_val: float, max_val: float):
    """Helper to create detail adjustment tools"""
    
    async def detail_tool(value: float) -> Dict[str, Any]:
        f"""
        Adjust {param_name.lower()} for sharpening/noise reduction.
        
        Args:
            value: Adjustment value ({min_val} to {max_val})
            
        Returns:
            Updated detail value
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
    
    detail_tool.__name__ = f"develop_adjust_{suffix}"
    server.tool(detail_tool)