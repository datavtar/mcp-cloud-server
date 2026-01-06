"""Intelligent Service MCP Tool - LLM-powered blanket service."""
import json


def register_intelligent_weather_tool(mcp):
    """Register the intelligent service tool with the MCP server."""

    @mcp.tool()
    async def ask(
        request: str,
        context: str = "",
        output_format: dict | None = None
    ) -> str:
        """
        Intelligent service agent. Send any request and get a structured JSON response.
        The LLM interprets your request and uses available tools to fulfill it.

        Currently supports weather-related queries (forecasts, current conditions,
        air quality, UV index, sunrise/sunset, etc.) with more capabilities coming.

        Args:
            request: Your request in natural language (e.g., "Weather in Paris",
                     "Compare temperatures in Tokyo and London",
                     "Air quality in Beijing with UV index")
            context: Optional context to help interpret the request
                    (e.g., "Planning a trip next week", "Need info for outdoor event")
            output_format: Optional dict specifying output preferences:
                          - keys: List of specific key names for the response
                          - units: Preferred units (e.g., "fahrenheit", "metric")

        Returns:
            JSON string with structured response data
        """
        from services.agent import ServiceAgent

        agent = ServiceAgent()
        result = await agent.process_request({
            "request": request,
            "context": context,
            "output_format": output_format
        })

        return json.dumps(result, indent=2)
