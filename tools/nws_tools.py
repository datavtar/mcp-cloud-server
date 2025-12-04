"""NWS (National Weather Service) tools - US only."""
from config import NWS_API_BASE
from utils.http_client import make_nws_request


def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""


def register_nws_tools(mcp):
    """Register all NWS tools with the MCP server."""

    @mcp.tool()
    async def get_alerts(state: str) -> str:
        """Get weather alerts for a US state.
        Args:
            state: Two-letter US state code (e.g. CA, NY)
        """
        url = f"{NWS_API_BASE}/alerts/active/area/{state}"
        data = await make_nws_request(url)
        if not data or "features" not in data:
            return "Unable to fetch alerts or no alerts found."
        if not data["features"]:
            return "No active alerts for this state."

        alerts = [format_alert(feature) for feature in data["features"]]
        return "\n---\n".join(alerts)

    @mcp.tool()
    async def get_forecast(latitude: float, longitude: float) -> str:
        """Get weather forecast for a US location.
        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
        """
        points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
        points_data = await make_nws_request(points_url)

        if not points_data:
            return "Unable to fetch forecast data for this location. Note: NWS only covers US locations."

        forecast_url = points_data["properties"]["forecast"]
        forecast_data = await make_nws_request(forecast_url)

        if not forecast_data:
            return "Unable to fetch detailed forecast."

        periods = forecast_data["properties"]["periods"]
        forecasts = []
        for period in periods[:5]:
            forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
            forecasts.append(forecast)
        return "\n---\n".join(forecasts)

    @mcp.tool()
    async def get_hourly_forecast(latitude: float, longitude: float) -> str:
        """Get hourly weather forecast for a US location (next 24 hours).
        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
        """
        points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
        points_data = await make_nws_request(points_url)

        if not points_data:
            return "Unable to fetch forecast data. Note: NWS only covers US locations."

        hourly_url = points_data["properties"]["forecastHourly"]
        hourly_data = await make_nws_request(hourly_url)

        if not hourly_data:
            return "Unable to fetch hourly forecast."

        periods = hourly_data["properties"]["periods"]
        forecasts = []
        for period in periods[:24]:
            forecast = f"{period['startTime'][:16]}: {period['temperature']}°{period['temperatureUnit']}, {period['shortForecast']}, Wind: {period['windSpeed']} {period['windDirection']}"
            forecasts.append(forecast)
        return "\n".join(forecasts)

    @mcp.tool()
    async def get_current_conditions(latitude: float, longitude: float) -> str:
        """Get current weather conditions from nearest observation station (US only).
        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
        """
        points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
        points_data = await make_nws_request(points_url)

        if not points_data:
            return "Unable to fetch location data. Note: NWS only covers US locations."

        stations_url = points_data["properties"]["observationStations"]
        stations_data = await make_nws_request(stations_url)

        if not stations_data or not stations_data.get("features"):
            return "No observation stations found nearby."

        station_id = stations_data["features"][0]["properties"]["stationIdentifier"]
        obs_url = f"{NWS_API_BASE}/stations/{station_id}/observations/latest"
        obs_data = await make_nws_request(obs_url)

        if not obs_data:
            return "Unable to fetch current observations."

        props = obs_data["properties"]
        temp_c = props.get("temperature", {}).get("value")
        temp_f = round(temp_c * 9 / 5 + 32, 1) if temp_c is not None else "N/A"
        humidity = props.get("relativeHumidity", {}).get("value")
        wind_speed = props.get("windSpeed", {}).get("value")
        wind_dir = props.get("windDirection", {}).get("value")
        description = props.get("textDescription", "N/A")

        return f"""
Station: {station_id}
Conditions: {description}
Temperature: {temp_f}°F ({temp_c}°C)
Humidity: {round(humidity, 1) if humidity else 'N/A'}%
Wind: {round(wind_speed * 2.237, 1) if wind_speed else 'N/A'} mph from {wind_dir}°
"""

    @mcp.tool()
    async def get_radar_stations(latitude: float, longitude: float) -> str:
        """Get nearby radar stations for a US location.
        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
        """
        url = f"{NWS_API_BASE}/radar/stations"
        data = await make_nws_request(url)

        if not data or "features" not in data:
            return "Unable to fetch radar stations."

        stations = []
        for feature in data["features"][:10]:
            props = feature["properties"]
            coords = feature["geometry"]["coordinates"]
            stations.append(
                f"{props['id']}: {props['name']} ({coords[1]:.2f}, {coords[0]:.2f})"
            )
        return "Radar Stations:\n" + "\n".join(stations)

    @mcp.tool()
    async def get_active_hurricanes() -> str:
        """Get active tropical storms and hurricanes in the US."""
        url = f"{NWS_API_BASE}/alerts/active?event=Hurricane,Tropical%20Storm"
        data = await make_nws_request(url)

        if not data or "features" not in data:
            return "Unable to fetch hurricane alerts."

        if not data["features"]:
            return "No active hurricane or tropical storm alerts."

        alerts = [format_alert(feature) for feature in data["features"]]
        return "\n---\n".join(alerts)
