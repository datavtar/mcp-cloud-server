from .weather_prompts import register_prompts


def register_all_prompts(mcp):
    """Register all prompts with the MCP server."""
    register_prompts(mcp)
