"""
Tone curve tools for develop server
12 tools total: 6 basic + 6 advanced curve manipulation
"""
from typing import Dict, Any, List

def setup_tone_curve_tools(server, execute_command):
    """Setup basic tone curve tools (6 tools)"""
    
    @server.tool
    async def develop_get_tone_curve(
        curve_type: str = "ToneCurvePV2012"
    ) -> Dict[str, Any]:
        """
        Get current tone curve points.
        
        Args:
            curve_type: Curve to get - "ToneCurvePV2012" (main),
                       "ToneCurvePV2012Red", "ToneCurvePV2012Green", 
                       "ToneCurvePV2012Blue"
                       
        Returns:
            Curve points as x,y coordinates (0-255 range)
        """
        result = await execute_command("getCurvePoints", {
            "param": curve_type
        })
        
        return {
            "success": True,
            "curve_type": curve_type,
            "points": result.get("points", []),
            "point_count": result.get("pointCount", 0)
        }
    
    @server.tool
    async def develop_set_tone_curve(
        points: List[Dict[str, float]],
        curve_type: str = "ToneCurvePV2012"
    ) -> Dict[str, Any]:
        """
        Set custom tone curve from points.
        
        Powerful tool for AI agents to create custom contrast curves.
        
        Args:
            points: List of {"x": 0-255, "y": 0-255} coordinates
            curve_type: Which curve to modify
            
        Returns:
            Updated curve confirmation
        """
        for point in points:
            if not (0 <= point["x"] <= 255 and 0 <= point["y"] <= 255):
                raise ValueError(f"Point coordinates must be 0-255")
        
        await execute_command("setCurvePoints", {
            "param": curve_type,
            "points": points
        })
        
        return {
            "success": True,
            "curve_type": curve_type,
            "point_count": len(points)
        }
    
    @server.tool
    async def develop_apply_s_curve(
        strength: int = 30,
        curve_type: str = "ToneCurvePV2012"
    ) -> Dict[str, Any]:
        """
        Apply S-curve preset for enhanced contrast.
        
        Common adjustment that AI agents can use for
        more dramatic, contrasty looks.
        
        Args:
            strength: S-curve strength (0-100)
            curve_type: Which curve to modify
            
        Returns:
            Applied curve confirmation
        """
        await execute_command("setCurveSCurve", {
            "param": curve_type,
            "strength": strength
        })
        
        return {
            "success": True,
            "curve_type": curve_type,
            "preset": "s-curve",
            "strength": strength
        }
    
    # Add parametric tone curve tools
    parametric_params = [
        ("darks", "ParametricDarks"),
        ("lights", "ParametricLights"),
        ("shadows", "ParametricShadows"),
        ("highlights", "ParametricHighlights")
    ]
    
    for suffix, param_name in parametric_params:
        _create_parametric_tool(server, execute_command, suffix, param_name)

def setup_advanced_tone_curve_tools(server, execute_command):
    """Setup advanced tone curve manipulation tools (6 tools)"""
    
    @server.tool
    async def develop_get_curve_points(
        curve_type: str = "ToneCurvePV2012"
    ) -> Dict[str, Any]:
        """
        Get curve points as coordinate array.
        
        Enhanced version with detailed point information.
        
        Args:
            curve_type: Curve to get points from
            
        Returns:
            Detailed curve point data
        """
        result = await execute_command("getCurvePoints", {
            "param": curve_type
        })
        
        return {
            "success": True,
            "curve_type": curve_type,
            "points": result.get("points", []),
            "point_count": len(result.get("points", [])),
            "curve_bounds": result.get("bounds", {"min": 0, "max": 255})
        }
    
    @server.tool
    async def develop_set_curve_points(
        curve_type: str,
        points: List[Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        Set curve from coordinate points array.
        
        Args:
            curve_type: Which curve to modify
            points: Array of {"x": 0-255, "y": 0-255} coordinates
            
        Returns:
            Curve update confirmation
        """
        # Validate points
        for i, point in enumerate(points):
            if not isinstance(point, dict) or "x" not in point or "y" not in point:
                raise ValueError(f"Point {i} must have 'x' and 'y' coordinates")
            if not (0 <= point["x"] <= 255 and 0 <= point["y"] <= 255):
                raise ValueError(f"Point {i} coordinates must be 0-255")
        
        result = await execute_command("setCurvePoints", {
            "param": curve_type,
            "points": points
        })
        
        return {
            "success": True,
            "curve_type": curve_type,
            "points_set": len(points),
            "curve_id": result.get("curveId")
        }
    
    @server.tool
    async def develop_set_curve_linear(
        curve_type: str = "ToneCurvePV2012"
    ) -> Dict[str, Any]:
        """
        Reset curve to linear (no adjustment).
        
        Args:
            curve_type: Which curve to reset
            
        Returns:
            Linear curve confirmation
        """
        result = await execute_command("setCurveLinear", {
            "param": curve_type
        })
        
        return {
            "success": True,
            "curve_type": curve_type,
            "message": "Curve reset to linear"
        }
    
    @server.tool
    async def develop_add_curve_point(
        curve_type: str,
        x: float,
        y: float
    ) -> Dict[str, Any]:
        """
        Add a single point to existing curve.
        
        Args:
            curve_type: Which curve to modify
            x: X coordinate (0-255)
            y: Y coordinate (0-255)
            
        Returns:
            Point addition confirmation
        """
        if not (0 <= x <= 255 and 0 <= y <= 255):
            raise ValueError("Coordinates must be 0-255")
        
        result = await execute_command("addCurvePoint", {
            "param": curve_type,
            "x": x,
            "y": y
        })
        
        return {
            "success": True,
            "curve_type": curve_type,
            "point_added": {"x": x, "y": y},
            "point_index": result.get("index")
        }
    
    @server.tool
    async def develop_remove_curve_point(
        curve_type: str,
        index: int
    ) -> Dict[str, Any]:
        """
        Remove a point from curve by index.
        
        Args:
            curve_type: Which curve to modify
            index: Point index to remove (0-based)
            
        Returns:
            Point removal confirmation
        """
        result = await execute_command("removeCurvePoint", {
            "param": curve_type,
            "index": index
        })
        
        return {
            "success": True,
            "curve_type": curve_type,
            "point_removed_index": index,
            "remaining_points": result.get("remainingPoints")
        }
    
    @server.tool
    async def develop_set_curve_s_curve(
        curve_type: str,
        strength: int = 30
    ) -> Dict[str, Any]:
        """
        Apply S-curve preset with specified strength.
        
        Args:
            curve_type: Which curve to modify
            strength: S-curve strength (0-100)
            
        Returns:
            S-curve application confirmation
        """
        if not 0 <= strength <= 100:
            raise ValueError("Strength must be 0-100")
        
        result = await execute_command("setCurveSCurve", {
            "param": curve_type,
            "strength": strength
        })
        
        return {
            "success": True,
            "curve_type": curve_type,
            "preset": "s-curve",
            "strength": strength,
            "points_created": result.get("pointsCreated")
        }

def _create_parametric_tool(server, execute_command, suffix: str, param_name: str):
    """Helper to create parametric tone curve tools"""
    
    async def parametric_tool(value: float) -> Dict[str, Any]:
        f"""
        Adjust {suffix} using parametric tone curve.
        
        Args:
            value: Adjustment value (-100 to +100)
            
        Returns:
            Updated parametric value
        """
        if not -100 <= value <= 100:
            raise ValueError(f"Parametric adjustments must be -100 to +100")
        
        await execute_command("setValue", {
            "param": param_name,
            "value": value
        })
        
        return {
            "success": True,
            "parameter": param_name,
            "value": value
        }
    
    parametric_tool.__name__ = f"develop_adjust_tone_{suffix}"
    server.tool(parametric_tool)