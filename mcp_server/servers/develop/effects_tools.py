"""
Effects tools for develop server
8 tools: vignetting controls + grain effects
"""
from typing import Dict, Any

def setup_effects_tools(server, execute_command):
    """Setup effects tools (8 tools)"""
    
    @server.tool
    async def develop_adjust_vignette(amount: float) -> Dict[str, Any]:
        """
        Adjust post-crop vignette amount.
        
        Args:
            amount: Vignette amount (-100 to +100)
            
        Returns:
            Updated vignette value
        """
        if not -100 <= amount <= 100:
            raise ValueError(f"Vignette amount must be -100 to +100")
        
        await execute_command("setValue", {
            "param": "PostCropVignetteAmount",
            "value": amount
        })
        
        return {
            "success": True,
            "parameter": "PostCropVignetteAmount",
            "value": amount
        }
    
    @server.tool
    async def develop_adjust_vignette_midpoint(
        value: float
    ) -> Dict[str, Any]:
        """
        Adjust vignette midpoint.
        
        Controls the size of the vignette effect.
        
        Args:
            value: Midpoint adjustment (0 to 100)
            
        Returns:
            Updated vignette midpoint
        """
        if not 0 <= value <= 100:
            raise ValueError("Vignette midpoint must be 0 to 100")
        
        await execute_command("setValue", {
            "param": "PostCropVignetteMidpoint",
            "value": value
        })
        
        return {
            "success": True,
            "parameter": "PostCropVignetteMidpoint",
            "value": value
        }
    
    @server.tool
    async def develop_adjust_vignette_feather(
        value: float
    ) -> Dict[str, Any]:
        """
        Adjust vignette feathering.
        
        Controls the softness of the vignette edge.
        
        Args:
            value: Feather amount (0 to 100)
            
        Returns:
            Updated vignette feather
        """
        if not 0 <= value <= 100:
            raise ValueError("Vignette feather must be 0 to 100")
        
        await execute_command("setValue", {
            "param": "PostCropVignetteFeather",
            "value": value
        })
        
        return {
            "success": True,
            "parameter": "PostCropVignetteFeather",
            "value": value
        }
    
    @server.tool
    async def develop_adjust_vignette_roundness(
        value: float
    ) -> Dict[str, Any]:
        """
        Adjust vignette roundness.
        
        Controls the shape of the vignette.
        
        Args:
            value: Roundness (-100 to +100)
            
        Returns:
            Updated vignette roundness
        """
        if not -100 <= value <= 100:
            raise ValueError("Vignette roundness must be -100 to +100")
        
        await execute_command("setValue", {
            "param": "PostCropVignetteRoundness",
            "value": value
        })
        
        return {
            "success": True,
            "parameter": "PostCropVignetteRoundness",
            "value": value
        }
    
    @server.tool
    async def develop_adjust_vignette_style(
        style: int
    ) -> Dict[str, Any]:
        """
        Set vignette style.
        
        Args:
            style: Vignette style (1=Highlight Priority, 2=Color Priority, 3=Paint Overlay)
            
        Returns:
            Updated vignette style
        """
        if style not in [1, 2, 3]:
            raise ValueError("Vignette style must be 1, 2, or 3")
        
        await execute_command("setValue", {
            "param": "PostCropVignetteStyle",
            "value": style
        })
        
        style_names = {1: "Highlight Priority", 2: "Color Priority", 3: "Paint Overlay"}
        
        return {
            "success": True,
            "parameter": "PostCropVignetteStyle",
            "style_value": style,
            "style_name": style_names[style]
        }
    
    @server.tool
    async def develop_adjust_vignette_highlight_contrast(
        value: float
    ) -> Dict[str, Any]:
        """
        Adjust vignette highlight contrast.
        
        Controls highlight preservation in vignette.
        
        Args:
            value: Highlight contrast (0 to 100)
            
        Returns:
            Updated vignette highlight contrast
        """
        if not 0 <= value <= 100:
            raise ValueError("Vignette highlight contrast must be 0 to 100")
        
        await execute_command("setValue", {
            "param": "PostCropVignetteHighlightContrast",
            "value": value
        })
        
        return {
            "success": True,
            "parameter": "PostCropVignetteHighlightContrast",
            "value": value
        }
    
    @server.tool
    async def develop_adjust_grain(
        amount: float,
        size: float = 25,
        frequency: float = 50
    ) -> Dict[str, Any]:
        """
        Adjust film grain effect.
        
        Args:
            amount: Grain amount (0 to 100)
            size: Grain size (0 to 100)
            frequency: Grain frequency (0 to 100)
            
        Returns:
            Updated grain settings
        """
        grain_settings = {
            "GrainAmount": amount,
            "GrainSize": size,
            "GrainFrequency": frequency
        }
        
        for param, value in grain_settings.items():
            if not 0 <= value <= 100:
                raise ValueError(f"{param} must be 0 to 100")
        
        # Apply each grain setting
        for param, value in grain_settings.items():
            await execute_command("setValue", {
                "param": param,
                "value": value
            })
        
        return {
            "success": True,
            "grain_settings": grain_settings
        }