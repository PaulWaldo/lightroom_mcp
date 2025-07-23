"""
Color adjustment tools for develop server
34 tools total: 25 HSL + 9 color grading/split toning
"""
from typing import Dict, Any

def setup_hsl_tools(server, execute_command):
    """Setup HSL/Color adjustment tools (25 tools)"""
    
    colors = ["Red", "Orange", "Yellow", "Green", "Aqua", "Blue", "Purple", "Magenta"]
    adjustments = ["Hue", "Saturation", "Luminance"]
    
    for color in colors:
        for adjustment in adjustments:
            param_name = f"{adjustment}Adjustment{color}"
            tool_name = f"develop_adjust_{color.lower()}_{adjustment.lower()}"
            
            _create_hsl_tool(server, execute_command, tool_name, param_name, color, adjustment)
    
    @server.tool
    async def develop_enhance_colors(
        preset: str = "vibrant",
        preserve_existing: bool = False
    ) -> Dict[str, Any]:
        """
        Apply color enhancement presets using PointColors.
        
        High-level tool for AI agents to enhance specific colors
        without dealing with complex PointColors syntax.
        
        Args:
            preset: "natural", "vibrant", "muted", "autumn"
            preserve_existing: Keep existing color adjustments
            
        Returns:
            Applied color enhancement
        """
        result = await execute_command("enhanceColors", {
            "preset": preset,
            "preserveExisting": preserve_existing
        })
        
        return {
            "success": True,
            "preset": preset,
            "message": f"Applied {preset} color enhancement"
        }

def setup_color_grading_tools(server, execute_command):
    """Setup color grading and split toning tools (9 tools)"""
    
    # Split Toning parameters
    split_toning_params = [
        ("split_toning_shadow_hue", "SplitToningShadowHue", 0, 360),
        ("split_toning_shadow_saturation", "SplitToningShadowSaturation", 0, 100),
        ("split_toning_highlight_hue", "SplitToningHighlightHue", 0, 360),
        ("split_toning_highlight_saturation", "SplitToningHighlightSaturation", 0, 100),
        ("split_toning_balance", "SplitToningBalance", -100, 100)
    ]
    
    for suffix, param_name, min_val, max_val in split_toning_params:
        _create_color_grading_tool(server, execute_command, suffix, param_name, min_val, max_val)
    
    # Color Grading parameters (LR 2020+)
    color_grade_params = [
        ("color_grade_shadow_lum", "ColorGradeShadowLum", -100, 100),
        ("color_grade_highlight_lum", "ColorGradeHighlightLum", -100, 100),
        ("color_grade_midtone_hue", "ColorGradeMidtoneHue", 0, 360),
        ("color_grade_global_sat", "ColorGradeGlobalSat", -100, 100)
    ]
    
    for suffix, param_name, min_val, max_val in color_grade_params:
        _create_color_grading_tool(server, execute_command, suffix, param_name, min_val, max_val)

def _create_hsl_tool(server, execute_command, tool_name: str, param_name: str, 
                     color: str, adjustment: str):
    """Helper to create HSL adjustment tools"""
    
    # Use a factory function to avoid closure issues
    def make_hsl_tool(param_name_fixed: str, color_fixed: str, adjustment_fixed: str):
        async def hsl_tool(value: float) -> Dict[str, Any]:
            f"""
            Adjust {adjustment_fixed.lower()} for {color_fixed.lower()} colors.
            
            Args:
                value: Adjustment value (-100 to +100)
                
            Returns:
                Updated HSL value
            """
            if not -100 <= value <= 100:
                raise ValueError(f"HSL adjustments must be -100 to +100")
            
            await execute_command("setValue", {
                "param": param_name_fixed,
                "value": value
            })
            
            return {
                "success": True,
                "color": color_fixed,
                "adjustment": adjustment_fixed,
                "value": value
            }
        return hsl_tool
    
    # Create the tool with fixed parameters
    tool_func = make_hsl_tool(param_name, color, adjustment)
    tool_func.__name__ = tool_name
    
    # Register with FastMCP using the decorator pattern
    server.tool(tool_func)

def _create_color_grading_tool(server, execute_command, suffix: str, param_name: str, min_val: float, max_val: float):
    """Helper to create color grading tools"""
    
    async def color_grading_tool(value: float) -> Dict[str, Any]:
        f"""
        Adjust {param_name.lower()} for color grading.
        
        Args:
            value: Adjustment value ({min_val} to {max_val})
            
        Returns:
            Updated color grading value
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
    
    color_grading_tool.__name__ = f"develop_adjust_{suffix}"
    server.tool(color_grading_tool)