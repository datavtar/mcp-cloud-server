from .nws_tools import register_nws_tools
from .global_tools import register_global_tools
from .geocoding import register_geocoding_tools
from .utility_tools import register_utility_tools
from .intelligent_weather import register_intelligent_weather_tool


def register_all_tools(mcp):
    """Register all tools with the MCP server."""
    register_nws_tools(mcp)
    register_global_tools(mcp)
    register_geocoding_tools(mcp)
    register_utility_tools(mcp)
    register_intelligent_weather_tool(mcp)
