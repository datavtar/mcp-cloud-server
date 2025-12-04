"""Utility tools - sunrise/sunset, weather comparison, summaries."""
from config import SUNRISE_SUNSET_API_BASE, OPEN_METEO_API_BASE
from utils.http_client import make_request


def register_utility_tools(mcp):
    """Register all utility tools with the MCP server."""

    @mcp.tool()
    async def get_sunrise_sunset(latitude: float, longitude: float, date: str = "today") -> str:
        """Get sunrise and sunset times for a location.
        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
            date: Date in YYYY-MM-DD format or "today" (default: today)
        """
        url = f"{SUNRISE_SUNSET_API_BASE}/json"
        params = {
            "lat": latitude,
            "lng": longitude,
            "formatted": 0,
        }
        if date != "today":
            params["date"] = date

        data = await make_request(url, params=params)

        if not data or data.get("status") != "OK":
            return "Unable to fetch sunrise/sunset data."

        results = data["results"]
        return f"""
Sunrise: {results['sunrise']}
Sunset: {results['sunset']}
Solar Noon: {results['solar_noon']}
Day Length: {results['day_length']} seconds ({int(results['day_length']) // 3600}h {(int(results['day_length']) % 3600) // 60}m)
Civil Twilight Begin: {results['civil_twilight_begin']}
Civil Twilight End: {results['civil_twilight_end']}
"""

    @mcp.tool()
    async def compare_weather(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> str:
        """Compare current weather between two locations.
        Args:
            lat1: Latitude of first location
            lon1: Longitude of first location
            lat2: Latitude of second location
            lon2: Longitude of second location
        """
        url = f"{OPEN_METEO_API_BASE}/forecast"

        async def get_weather(lat, lon):
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,precipitation,weathercode,windspeed_10m",
                "timezone": "auto",
            }
            return await make_request(url, params=params)

        data1 = await get_weather(lat1, lon1)
        data2 = await get_weather(lat2, lon2)

        if not data1 or not data2:
            return "Unable to fetch weather data for comparison."

        def format_current(data, label):
            current = data.get("current", {})
            weather_code = current.get("weathercode", 0)
            weather_desc = _weather_code_to_description(weather_code)
            return f"""
{label}:
  Temperature: {current.get('temperature_2m', 'N/A')}°C
  Humidity: {current.get('relative_humidity_2m', 'N/A')}%
  Conditions: {weather_desc}
  Wind: {current.get('windspeed_10m', 'N/A')} km/h
  Precipitation: {current.get('precipitation', 'N/A')} mm
"""

        result1 = format_current(data1, f"Location 1 ({lat1}, {lon1})")
        result2 = format_current(data2, f"Location 2 ({lat2}, {lon2})")

        temp1 = data1.get("current", {}).get("temperature_2m")
        temp2 = data2.get("current", {}).get("temperature_2m")
        temp_diff = ""
        if temp1 is not None and temp2 is not None:
            diff = temp1 - temp2
            if diff > 0:
                temp_diff = f"\n📊 Location 1 is {abs(diff):.1f}°C warmer than Location 2"
            elif diff < 0:
                temp_diff = f"\n📊 Location 2 is {abs(diff):.1f}°C warmer than Location 1"
            else:
                temp_diff = "\n📊 Both locations have the same temperature"

        return result1 + result2 + temp_diff

    @mcp.tool()
    async def get_weather_summary(latitude: float, longitude: float) -> str:
        """Get comprehensive weather summary including current conditions, forecast, and air quality.
        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
        """
        forecast_url = f"{OPEN_METEO_API_BASE}/forecast"
        forecast_params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,precipitation,weathercode,windspeed_10m,uv_index",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
            "timezone": "auto",
            "forecast_days": 3,
        }
        forecast_data = await make_request(forecast_url, params=forecast_params)

        aqi_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        aqi_params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "us_aqi,pm2_5",
        }
        aqi_data = await make_request(aqi_url, params=aqi_params)

        if not forecast_data:
            return "Unable to fetch weather data."

        result = [f"Weather Summary for ({latitude}, {longitude})", "=" * 40]

        if "current" in forecast_data:
            current = forecast_data["current"]
            weather_code = current.get("weathercode", 0)
            weather_desc = _weather_code_to_description(weather_code)
            result.append("\n🌡️ CURRENT CONDITIONS:")
            result.append(f"  Temperature: {current.get('temperature_2m', 'N/A')}°C")
            result.append(f"  Conditions: {weather_desc}")
            result.append(f"  Humidity: {current.get('relative_humidity_2m', 'N/A')}%")
            result.append(f"  Wind: {current.get('windspeed_10m', 'N/A')} km/h")
            result.append(f"  UV Index: {current.get('uv_index', 'N/A')}")

        if aqi_data and "current" in aqi_data:
            aqi_current = aqi_data["current"]
            aqi = aqi_current.get("us_aqi", "N/A")
            aqi_level = _aqi_to_level(aqi) if isinstance(aqi, (int, float)) else "Unknown"
            result.append(f"\n🌬️ AIR QUALITY:")
            result.append(f"  AQI: {aqi} ({aqi_level})")
            result.append(f"  PM2.5: {aqi_current.get('pm2_5', 'N/A')} μg/m³")

        if "daily" in forecast_data:
            daily = forecast_data["daily"]
            result.append("\n📅 3-DAY FORECAST:")
            for i in range(len(daily["time"])):
                weather_code = daily["weathercode"][i]
                weather_desc = _weather_code_to_description(weather_code)
                result.append(
                    f"  {daily['time'][i]}: {weather_desc}, "
                    f"High: {daily['temperature_2m_max'][i]}°C, "
                    f"Low: {daily['temperature_2m_min'][i]}°C"
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
