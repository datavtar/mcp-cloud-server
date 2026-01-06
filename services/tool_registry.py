"""Registry of tools available to the LLM agent.

This module defines:
1. TOOLS - Tool schemas for the LLM to understand available functions
2. TOOL_FUNCTIONS - Mapping of tool names to async implementation functions
"""
from config import NWS_API_BASE, OPEN_METEO_API_BASE, SUNRISE_SUNSET_API_BASE
from utils.http_client import make_request, make_nws_request, make_nominatim_request


# Tool schemas for Claude (Anthropic format)
TOOLS = [
    {
        "name": "geocode_location",
        "description": "Convert a place name, address, or location to latitude/longitude coordinates. Use this first when you have a location name but need coordinates for other tools.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Place name, address, or location (e.g., 'Paris, France', 'Amsterdam Zuid', '1600 Pennsylvania Ave')"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_global_forecast",
        "description": "Get 7-day weather forecast for any location worldwide. Returns daily high/low temperatures, precipitation, wind speed, and weather conditions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "description": "Latitude of the location"},
                "longitude": {"type": "number", "description": "Longitude of the location"}
            },
            "required": ["latitude", "longitude"]
        }
    },
    {
        "name": "get_global_hourly",
        "description": "Get hourly weather forecast for the next 24 hours at any location worldwide.",
        "input_schema": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "description": "Latitude of the location"},
                "longitude": {"type": "number", "description": "Longitude of the location"}
            },
            "required": ["latitude", "longitude"]
        }
    },
    {
        "name": "get_current_weather",
        "description": "Get current weather conditions including temperature, humidity, wind, and weather description for any location worldwide.",
        "input_schema": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "description": "Latitude of the location"},
                "longitude": {"type": "number", "description": "Longitude of the location"}
            },
            "required": ["latitude", "longitude"]
        }
    },
    {
        "name": "get_air_quality",
        "description": "Get air quality index (AQI) and pollutant levels for any location worldwide.",
        "input_schema": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "description": "Latitude of the location"},
                "longitude": {"type": "number", "description": "Longitude of the location"}
            },
            "required": ["latitude", "longitude"]
        }
    },
    {
        "name": "get_uv_index",
        "description": "Get current and forecast UV index for any location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "description": "Latitude of the location"},
                "longitude": {"type": "number", "description": "Longitude of the location"}
            },
            "required": ["latitude", "longitude"]
        }
    },
    {
        "name": "get_sunrise_sunset",
        "description": "Get sunrise and sunset times for a location on a specific date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "description": "Latitude of the location"},
                "longitude": {"type": "number", "description": "Longitude of the location"},
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format, or 'today' (default)"}
            },
            "required": ["latitude", "longitude"]
        }
    },
    {
        "name": "get_us_alerts",
        "description": "Get weather alerts for a US state. Only works for US locations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "Two-letter US state code (e.g., 'CA', 'NY', 'TX')"
                }
            },
            "required": ["state"]
        }
    }
]


# Weather code descriptions
WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
}


def _weather_code_to_description(code: int) -> str:
    return WEATHER_CODES.get(code, f"Unknown ({code})")


def _aqi_to_level(aqi: float) -> str:
    if aqi <= 50: return "Good"
    elif aqi <= 100: return "Moderate"
    elif aqi <= 150: return "Unhealthy for Sensitive Groups"
    elif aqi <= 200: return "Unhealthy"
    elif aqi <= 300: return "Very Unhealthy"
    else: return "Hazardous"


# Tool implementation functions
async def geocode_location(query: str) -> str:
    """Convert place name to coordinates."""
    data = await make_nominatim_request("search", {"q": query, "limit": 3})

    if not data:
        return "Unable to geocode location. Try a more specific query."

    if isinstance(data, list) and len(data) == 0:
        return f"No results found for '{query}'."

    results = []
    for item in data[:3]:
        lat = item.get("lat", "N/A")
        lon = item.get("lon", "N/A")
        display_name = item.get("display_name", "Unknown")
        results.append(f"Location: {display_name}\nLatitude: {lat}\nLongitude: {lon}")

    return "\n---\n".join(results)


async def get_global_forecast(latitude: float, longitude: float) -> str:
    """Get 7-day weather forecast."""
    url = f"{OPEN_METEO_API_BASE}/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode,windspeed_10m_max",
        "timezone": "auto"
    }
    data = await make_request(url, params=params)

    if not data or "daily" not in data:
        return "Unable to fetch forecast."

    daily = data["daily"]
    forecasts = []
    for i in range(len(daily["time"])):
        weather_desc = _weather_code_to_description(daily["weathercode"][i])
        forecasts.append(
            f"Date: {daily['time'][i]}\n"
            f"Conditions: {weather_desc}\n"
            f"High: {daily['temperature_2m_max'][i]}°C\n"
            f"Low: {daily['temperature_2m_min'][i]}°C\n"
            f"Precipitation: {daily['precipitation_sum'][i]}mm\n"
            f"Max Wind: {daily['windspeed_10m_max'][i]} km/h"
        )
    return "\n---\n".join(forecasts)


async def get_global_hourly(latitude: float, longitude: float) -> str:
    """Get hourly forecast for next 24 hours."""
    url = f"{OPEN_METEO_API_BASE}/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,precipitation,weathercode,windspeed_10m,relative_humidity_2m",
        "timezone": "auto",
        "forecast_hours": 24
    }
    data = await make_request(url, params=params)

    if not data or "hourly" not in data:
        return "Unable to fetch hourly forecast."

    hourly = data["hourly"]
    forecasts = []
    for i in range(min(24, len(hourly["time"]))):
        weather_desc = _weather_code_to_description(hourly["weathercode"][i])
        forecasts.append(
            f"{hourly['time'][i]}: {hourly['temperature_2m'][i]}°C, "
            f"{weather_desc}, "
            f"Humidity: {hourly['relative_humidity_2m'][i]}%, "
            f"Wind: {hourly['windspeed_10m'][i]} km/h"
        )
    return "\n".join(forecasts)


async def get_current_weather(latitude: float, longitude: float) -> str:
    """Get current weather conditions."""
    url = f"{OPEN_METEO_API_BASE}/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,precipitation,weathercode,windspeed_10m,winddirection_10m",
        "timezone": "auto"
    }
    data = await make_request(url, params=params)

    if not data or "current" not in data:
        return "Unable to fetch current weather."

    current = data["current"]
    weather_desc = _weather_code_to_description(current.get("weathercode", 0))

    return (
        f"Temperature: {current.get('temperature_2m', 'N/A')}°C\n"
        f"Conditions: {weather_desc}\n"
        f"Humidity: {current.get('relative_humidity_2m', 'N/A')}%\n"
        f"Wind: {current.get('windspeed_10m', 'N/A')} km/h from {current.get('winddirection_10m', 'N/A')}°\n"
        f"Precipitation: {current.get('precipitation', 'N/A')}mm"
    )


async def get_air_quality(latitude: float, longitude: float) -> str:
    """Get air quality data."""
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone"
    }
    data = await make_request(url, params=params)

    if not data or "current" not in data:
        return "Unable to fetch air quality data."

    current = data["current"]
    aqi = current.get("us_aqi", "N/A")
    aqi_level = _aqi_to_level(aqi) if isinstance(aqi, (int, float)) else "Unknown"

    return (
        f"Air Quality Index (US EPA): {aqi} ({aqi_level})\n"
        f"PM2.5: {current.get('pm2_5', 'N/A')} μg/m³\n"
        f"PM10: {current.get('pm10', 'N/A')} μg/m³\n"
        f"Ozone: {current.get('ozone', 'N/A')} μg/m³\n"
        f"NO2: {current.get('nitrogen_dioxide', 'N/A')} μg/m³\n"
        f"CO: {current.get('carbon_monoxide', 'N/A')} μg/m³"
    )


async def get_uv_index(latitude: float, longitude: float) -> str:
    """Get UV index."""
    url = f"{OPEN_METEO_API_BASE}/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "uv_index_max",
        "current": "uv_index",
        "timezone": "auto",
        "forecast_days": 3
    }
    data = await make_request(url, params=params)

    if not data:
        return "Unable to fetch UV index."

    result = []
    if "current" in data:
        current_uv = data["current"].get("uv_index", "N/A")
        result.append(f"Current UV Index: {current_uv}")

    if "daily" in data:
        daily = data["daily"]
        result.append("\nDaily Max UV Index:")
        for i in range(len(daily["time"])):
            result.append(f"  {daily['time'][i]}: {daily['uv_index_max'][i]}")

    return "\n".join(result)


async def get_sunrise_sunset(latitude: float, longitude: float, date: str = "today") -> str:
    """Get sunrise and sunset times."""
    url = f"{SUNRISE_SUNSET_API_BASE}/json"
    params = {"lat": latitude, "lng": longitude, "formatted": 0}
    if date != "today":
        params["date"] = date

    data = await make_request(url, params=params)

    if not data or data.get("status") != "OK":
        return "Unable to fetch sunrise/sunset data."

    results = data["results"]
    day_length_sec = int(results.get("day_length", 0))
    hours = day_length_sec // 3600
    minutes = (day_length_sec % 3600) // 60

    return (
        f"Sunrise: {results['sunrise']}\n"
        f"Sunset: {results['sunset']}\n"
        f"Solar Noon: {results['solar_noon']}\n"
        f"Day Length: {hours}h {minutes}m"
    )


async def get_us_alerts(state: str) -> str:
    """Get US weather alerts."""
    url = f"{NWS_API_BASE}/alerts/active/area/{state.upper()}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return f"No active alerts for {state.upper()}."

    alerts = []
    for feature in data["features"][:5]:  # Limit to 5 alerts
        props = feature["properties"]
        alerts.append(
            f"Event: {props.get('event', 'Unknown')}\n"
            f"Area: {props.get('areaDesc', 'Unknown')}\n"
            f"Severity: {props.get('severity', 'Unknown')}\n"
            f"Description: {props.get('description', 'N/A')[:500]}..."
        )

    return "\n---\n".join(alerts)


# Map tool names to implementation functions
TOOL_FUNCTIONS = {
    "geocode_location": geocode_location,
    "get_global_forecast": get_global_forecast,
    "get_global_hourly": get_global_hourly,
    "get_current_weather": get_current_weather,
    "get_air_quality": get_air_quality,
    "get_uv_index": get_uv_index,
    "get_sunrise_sunset": get_sunrise_sunset,
    "get_us_alerts": get_us_alerts,
}
