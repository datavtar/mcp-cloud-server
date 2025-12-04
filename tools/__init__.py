from .nws_tools import register_nws_tools
from .global_tools import register_global_tools
from .geocoding import register_geocoding_tools
from .utility_tools import register_utility_tools


def register_all_tools(mcp):
    """Register all tools with the MCP server."""
    register_nws_tools(mcp)
    register_global_tools(mcp)
    register_geocoding_tools(mcp)
    register_utility_tools(mcp)
