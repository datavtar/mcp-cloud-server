from .weather_resources import register_resources


def register_all_resources(mcp):
    """Register all resources with the MCP server."""
    register_resources(mcp)
