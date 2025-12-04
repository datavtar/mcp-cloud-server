"""Global weather tools using Open-Meteo API - works worldwide."""
from config import OPEN_METEO_API_BASE
from utils.http_client import make_request


def register_global_tools(mcp):
    """Register all global weather tools with the MCP server."""

    @mcp.tool()
    async def get_global_forecast(latitude: float, longitude: float) -> str:
        """Get 7-day weather forecast for any location worldwide.
        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
        """
        url = f"{OPEN_METEO_API_BASE}/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode,windspeed_10m_max",
            "timezone": "auto",
        }
        data = await make_request(url, params=params)

        if not data or "daily" not in data:
            return "Unable to fetch global forecast."

        daily = data["daily"]
        forecasts = []
        for i in range(len(daily["time"])):
            weather_code = daily["weathercode"][i]
            weather_desc = _weather_code_to_description(weather_code)
            forecasts.append(
                f"{daily['time'][i]}: {weather_desc}, "
                f"High: {daily['temperature_2m_max'][i]}°C, "
                f"Low: {daily['temperature_2m_min'][i]}°C, "
                f"Precip: {daily['precipitation_sum'][i]}mm, "
                f"Wind: {daily['windspeed_10m_max'][i]} km/h"
            )
        return "\n".join(forecasts)

    @mcp.tool()
    async def get_global_hourly(latitude: float, longitude: float) -> str:
        """Get hourly weather forecast for any location worldwide (next 24 hours).
        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
        """
        url = f"{OPEN_METEO_API_BASE}/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,precipitation,weathercode,windspeed_10m",
            "timezone": "auto",
            "forecast_hours": 24,
        }
        data = await make_request(url, params=params)

        if not data or "hourly" not in data:
            return "Unable to fetch hourly forecast."

        hourly = data["hourly"]
        forecasts = []
        for i in range(min(24, len(hourly["time"]))):
            weather_code = hourly["weathercode"][i]
            weather_desc = _weather_code_to_description(weather_code)
            forecasts.append(
                f"{hourly['time'][i]}: {hourly['temperature_2m'][i]}°C, "
                f"{weather_desc}, "
                f"Precip: {hourly['precipitation'][i]}mm, "
                f"Wind: {hourly['windspeed_10m'][i]} km/h"
            )
        return "\n".join(forecasts)

    @mcp.tool()
    async def get_air_quality(latitude: float, longitude: float) -> str:
        """Get air quality data for any location worldwide.
        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
        """
        url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone",
        }
        data = await make_request(url, params=params)

        if not data or "current" not in data:
            return "Unable to fetch air quality data."

        current = data["current"]
        aqi = current.get("us_aqi", "N/A")
        aqi_level = _aqi_to_level(aqi) if isinstance(aqi, (int, float)) else "Unknown"

        return f"""
Air Quality Index (US EPA): {aqi} ({aqi_level})
PM2.5: {current.get('pm2_5', 'N/A')} μg/m³
PM10: {current.get('pm10', 'N/A')} μg/m³
Ozone: {current.get('ozone', 'N/A')} μg/m³
Nitrogen Dioxide: {current.get('nitrogen_dioxide', 'N/A')} μg/m³
Carbon Monoxide: {current.get('carbon_monoxide', 'N/A')} μg/m³
"""

    @mcp.tool()
    async def get_uv_index(latitude: float, longitude: float) -> str:
        """Get UV index for any location worldwide.
        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
        """
        url = f"{OPEN_METEO_API_BASE}/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "uv_index_max,uv_index_clear_sky_max",
            "current": "uv_index",
            "timezone": "auto",
            "forecast_days": 3,
        }
        data = await make_request(url, params=params)

        if not data:
            return "Unable to fetch UV index data."

        result = []
        if "current" in data:
            current_uv = data["current"].get("uv_index", "N/A")
            uv_level = _uv_to_level(current_uv) if isinstance(current_uv, (int, float)) else "Unknown"
            result.append(f"Current UV Index: {current_uv} ({uv_level})")

        if "daily" in data:
            daily = data["daily"]
            result.append("\nDaily Max UV Index:")
            for i in range(len(daily["time"])):
                uv_max = daily["uv_index_max"][i]
                uv_level = _uv_to_level(uv_max) if isinstance(uv_max, (int, float)) else "Unknown"
                result.append(f"  {daily['time'][i]}: {uv_max} ({uv_level})")

        return "\n".join(result)

    @mcp.tool()
    async def get_marine_forecast(latitude: float, longitude: float) -> str:
        """Get marine/ocean forecast for coastal locations worldwide.
        Args:
            latitude: Latitude of the location (should be near coast)
            longitude: Longitude of the location (should be near coast)
        """
        url = "https://marine-api.open-meteo.com/v1/marine"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "wave_height_max,wave_direction_dominant,wave_period_max,wind_wave_height_max,swell_wave_height_max",
            "current": "wave_height,wave_direction,wave_period",
            "timezone": "auto",
        }
        data = await make_request(url, params=params)

        if not data:
            return "Unable to fetch marine forecast. Ensure location is near coast."

        result = []
        if "current" in data:
            current = data["current"]
            result.append("Current Conditions:")
            result.append(f"  Wave Height: {current.get('wave_height', 'N/A')} m")
            result.append(f"  Wave Direction: {current.get('wave_direction', 'N/A')}°")
            result.append(f"  Wave Period: {current.get('wave_period', 'N/A')} s")

        if "daily" in data:
            daily = data["daily"]
            result.append("\nDaily Forecast:")
            for i in range(len(daily["time"])):
                result.append(
                    f"  {daily['time'][i]}: "
                    f"Max Wave: {daily['wave_height_max'][i]}m, "
                    f"Direction: {daily['wave_direction_dominant'][i]}°, "
                    f"Period: {daily['wave_period_max'][i]}s"
                )

        return "\n".join(result)


def _weather_code_to_description(code: int) -> str:
    """Convert WMO weather code to description."""
    codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return codes.get(code, f"Unknown ({code})")


def _aqi_to_level(aqi: float) -> str:
    """Convert AQI to level description."""
    if aqi <= 50:
        return "Good"
    elif aqi <= 100:
        return "Moderate"
    elif aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    elif aqi <= 200:
        return "Unhealthy"
    elif aqi <= 300:
        return "Very Unhealthy"
    else:
        return "Hazardous"


def _uv_to_level(uv: float) -> str:
    """Convert UV index to level description."""
    if uv < 3:
        return "Low"
    elif uv < 6:
        return "Moderate"
    elif uv < 8:
        return "High"
    elif uv < 11:
        return "Very High"
    else:
        return "Extreme"
