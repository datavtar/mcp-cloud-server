from typing import Any
import httpx
import uvicorn
import os
from fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware

# Initialize FastMCP server
mcp = FastMCP("weather")

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

# --- Helper Functions ---

async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None

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

# --- Tool Definitions ---

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
    """Get weather forecast for a location.
    Args:
        latitude: Latitude of the location (recommended: up to 4 decimal places)
        longitude: Longitude of the location (recommended: up to 4 decimal places)
    """
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)
    
    if not points_data:
        return "Unable to fetch forecast data for this location."
        
    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)
    
    if not forecast_data:
        return "Unable to fetch detailed forecast."
        
    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)
    return "\n---\n".join(forecasts)

# --- Server Entry Point (The Cloud Run Fix) ---

# Get the internal Starlette app
app = mcp.sse_app()

# Add CORS middleware to allow requests from localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specific domains like ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    # Get the port from Google Cloud, defaulting to 8080
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting MCP server on 0.0.0.0:{port}...")
    
    # Run the server using uvicorn, binding to 0.0.0.0 (required for Cloud Run)
    #uvicorn.run(mcp.sse_app(), host="0.0.0.0", port=port)
    uvicorn.run(app, host="0.0.0.0", port=port)
