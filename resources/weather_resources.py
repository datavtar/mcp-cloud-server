"""MCP Resources for weather data."""
from config import NWS_API_BASE
from utils.http_client import make_nws_request


WEATHER_GLOSSARY = """
# Weather Terminology Glossary

## Temperature Terms
- **Heat Index**: The apparent temperature when humidity is factored in with air temperature.
- **Wind Chill**: The apparent temperature when wind is factored in with air temperature.
- **Dew Point**: The temperature at which air becomes saturated and dew forms.

## Precipitation Types
- **Drizzle**: Light rain with drops less than 0.5mm in diameter.
- **Freezing Rain**: Rain that freezes on contact with surfaces.
- **Sleet**: Ice pellets formed when rain freezes before reaching the ground.
- **Hail**: Balls of ice formed in thunderstorms.

## Cloud Types
- **Cumulus**: Puffy, white clouds with flat bases.
- **Stratus**: Flat, gray clouds that often cover the sky.
- **Cirrus**: Thin, wispy clouds at high altitudes.
- **Cumulonimbus**: Large thunderstorm clouds.

## Pressure Systems
- **High Pressure**: Associated with fair weather and clockwise winds (Northern Hemisphere).
- **Low Pressure**: Associated with clouds, precipitation, and counterclockwise winds.
- **Cold Front**: Leading edge of a cooler air mass.
- **Warm Front**: Leading edge of a warmer air mass.

## Severe Weather
- **Tornado Watch**: Conditions are favorable for tornadoes.
- **Tornado Warning**: A tornado has been sighted or indicated by radar.
- **Hurricane Watch**: Hurricane conditions possible within 48 hours.
- **Hurricane Warning**: Hurricane conditions expected within 36 hours.

## Air Quality
- **AQI**: Air Quality Index, a scale from 0-500 measuring air pollution.
- **PM2.5**: Fine particulate matter less than 2.5 micrometers.
- **PM10**: Particulate matter less than 10 micrometers.
- **Ozone**: A gas that can cause respiratory issues at ground level.

## UV Index Scale
- **0-2**: Low - Minimal protection needed
- **3-5**: Moderate - Protection recommended
- **6-7**: High - Protection essential
- **8-10**: Very High - Extra protection needed
- **11+**: Extreme - Avoid sun exposure
"""


def register_resources(mcp):
    """Register all resources with the MCP server."""

    @mcp.resource("weather://glossary")
    async def get_glossary() -> str:
        """Weather terminology definitions and glossary."""
        return WEATHER_GLOSSARY

    @mcp.resource("weather://stations/{state}")
    async def get_stations(state: str) -> str:
        """List weather observation stations in a US state.
        Args:
            state: Two-letter US state code (e.g., CA, NY)
        """
        url = f"{NWS_API_BASE}/stations?state={state}"
        data = await make_nws_request(url)

        if not data or "features" not in data:
            return f"Unable to fetch stations for state: {state}"

        if not data["features"]:
            return f"No stations found for state: {state}"

        stations = []
        for feature in data["features"][:50]:
            props = feature["properties"]
            coords = feature["geometry"]["coordinates"]
            stations.append(
                f"- {props['stationIdentifier']}: {props['name']} "
                f"({coords[1]:.4f}, {coords[0]:.4f})"
            )

        return f"Weather Stations in {state.upper()}:\n\n" + "\n".join(stations)

    @mcp.resource("weather://alerts/national")
    async def get_national_alerts() -> str:
        """Summary of all active weather alerts in the US."""
        url = f"{NWS_API_BASE}/alerts/active?status=actual&message_type=alert"
        data = await make_nws_request(url)

        if not data or "features" not in data:
            return "Unable to fetch national alerts."

        if not data["features"]:
            return "No active weather alerts nationwide."

        alert_counts = {}
        for feature in data["features"]:
            event = feature["properties"].get("event", "Unknown")
            alert_counts[event] = alert_counts.get(event, 0) + 1

        result = [
            f"National Weather Alert Summary",
            f"Total Active Alerts: {len(data['features'])}",
            "",
            "Alerts by Type:",
        ]

        for event, count in sorted(alert_counts.items(), key=lambda x: -x[1]):
            result.append(f"  - {event}: {count}")

        return "\n".join(result)
