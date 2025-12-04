"""MCP Prompts for weather-related tasks."""


def register_prompts(mcp):
    """Register all prompts with the MCP server."""

    @mcp.prompt()
    def travel_weather(origin: str, destination: str) -> str:
        """Generate a travel weather briefing prompt.
        Args:
            origin: Starting location (city name or coordinates)
            destination: Destination location (city name or coordinates)
        """
        return f"""Please provide a comprehensive travel weather briefing for a trip from {origin} to {destination}.

Include the following information:
1. Current weather conditions at both locations
2. Weather forecast for the next 3 days at the destination
3. Any weather alerts or warnings that might affect travel
4. Recommended items to pack based on the weather
5. Best time of day to travel considering weather conditions

Use the available weather tools to gather accurate, real-time data for this analysis.
"""

    @mcp.prompt()
    def severe_weather_summary(state: str) -> str:
        """Generate a severe weather analysis prompt for a US state.
        Args:
            state: Two-letter US state code (e.g., CA, NY)
        """
        return f"""Please provide a comprehensive severe weather analysis for {state.upper()}.

Include the following:
1. Current active weather alerts and warnings
2. Detailed breakdown of each alert type and affected areas
3. Expected duration of severe weather conditions
4. Safety recommendations for residents
5. Any hurricane or tropical storm activity if applicable

Use the available NWS tools to get accurate, official weather alert data.
"""

    @mcp.prompt()
    def clothing_recommendation(latitude: float, longitude: float) -> str:
        """Generate clothing recommendations based on weather.
        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
        """
        return f"""Based on the current weather conditions and forecast for location ({latitude}, {longitude}), please provide clothing recommendations.

Consider the following factors:
1. Current temperature and "feels like" temperature
2. Expected precipitation (rain, snow, etc.)
3. Wind conditions
4. UV index and sun exposure
5. Humidity levels

Please provide:
- Recommended clothing layers
- Footwear suggestions
- Accessories needed (umbrella, sunglasses, hat, etc.)
- Any special considerations for outdoor activities

Use the weather tools to get current conditions and forecast data.
"""

    @mcp.prompt()
    def outdoor_activity(latitude: float, longitude: float, activity: str) -> str:
        """Determine if weather is suitable for an outdoor activity.
        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
            activity: The outdoor activity being planned (e.g., hiking, beach, cycling)
        """
        return f"""Please analyze whether the weather is suitable for {activity} at location ({latitude}, {longitude}).

Evaluate the following:
1. Current weather conditions
2. Forecast for the next several hours
3. Temperature and comfort level
4. Precipitation probability
5. Wind conditions
6. UV index and sun exposure
7. Air quality

Provide:
- Overall recommendation (Good/Fair/Poor conditions for {activity})
- Best time window for the activity today
- Any weather-related risks or precautions
- Alternative suggestions if conditions are unfavorable

Use the available weather and air quality tools for accurate data.
"""
