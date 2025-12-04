# MCP Cloud Server

A Model Context Protocol (MCP) server built with FastMCP that exposes comprehensive weather tools, resources, and prompts via Server-Sent Events (SSE). Designed for deployment on Google Cloud Run.

## Features

- **US Weather (NWS)**: Alerts, forecasts, hourly forecasts, current conditions, radar stations, hurricane tracking
- **Global Weather (Open-Meteo)**: Worldwide forecasts, air quality, UV index, marine conditions
- **Geocoding (Nominatim)**: Convert addresses to coordinates and vice versa
- **Utilities**: Sunrise/sunset times, weather comparison, comprehensive summaries
- **MCP Resources**: Weather glossary, station lists, national alert summaries
- **MCP Prompts**: Travel weather, severe weather analysis, clothing recommendations, outdoor activity suitability
- **SSE Transport**: Uses Server-Sent Events for real-time MCP communication
- **Cloud Run Ready**: Configured for Google Cloud Run deployment

## Quick Start

### Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run server
python server.py
```

The server starts on `http://localhost:8080` by default. Set the `PORT` environment variable to change it.

### Docker Deployment

```bash
# Build image
docker build -t mcp-cloud-server .

# Run container
docker run -p 8080:8080 mcp-cloud-server
```

### Google Cloud Run Deployment

Using the deploy script (recommended):

```bash
# Basic deployment
python gcp_deploy.py --project-id <PROJECT_ID>

# Custom region and service name
python gcp_deploy.py -p <PROJECT_ID> -r europe-west1 -s weather-mcp

# Redeploy without rebuilding
python gcp_deploy.py -p <PROJECT_ID> --skip-build
```

Or manually with gcloud:

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/<PROJECT_ID>/mcp-server

# Deploy to Cloud Run
gcloud run deploy mcp-server \
    --image gcr.io/<PROJECT_ID>/mcp-server \
    --platform managed \
    --region <REGION> \
    --allow-unauthenticated
```

Replace `<PROJECT_ID>` with your GCP project ID and `<REGION>` with your preferred region (e.g., `us-central1`).

### Testing with MCP Inspector

```bash
# Test local server
npx @modelcontextprotocol/inspector \
    npx -y @modelcontextprotocol/server-sse-client \
    --url http://localhost:8080/sse

# Test deployed server
npx @modelcontextprotocol/inspector \
    npx -y @modelcontextprotocol/server-sse-client \
    --url https://<SERVICE_URL>/sse
```

Replace `<SERVICE_URL>` with your Cloud Run service URL (e.g., `mcp-server-xxxxx.us-central1.run.app`).

## MCP Tools

### US Weather (NWS API)
| Tool | Description |
|------|-------------|
| `get_alerts` | Get weather alerts for a US state |
| `get_forecast` | Get multi-day forecast for US location |
| `get_hourly_forecast` | Get hourly forecast (next 24h) |
| `get_current_conditions` | Get current conditions from nearest station |
| `get_radar_stations` | List nearby radar stations |
| `get_active_hurricanes` | Get active tropical storms/hurricanes |

### Global Weather (Open-Meteo)
| Tool | Description |
|------|-------------|
| `get_global_forecast` | 7-day forecast (worldwide) |
| `get_global_hourly` | Hourly forecast (worldwide) |
| `get_air_quality` | Air quality index and pollutants |
| `get_uv_index` | UV index current and forecast |
| `get_marine_forecast` | Wave height, direction, period |

### Geocoding (Nominatim)
| Tool | Description |
|------|-------------|
| `geocode_location` | Convert place name/address to coordinates |
| `reverse_geocode` | Convert coordinates to address |

### Utilities
| Tool | Description |
|------|-------------|
| `get_sunrise_sunset` | Sunrise/sunset times for any date |
| `compare_weather` | Compare weather between two locations |
| `get_weather_summary` | Comprehensive weather summary |

## MCP Resources

| Resource URI | Description |
|--------------|-------------|
| `weather://glossary` | Weather terminology definitions |
| `weather://stations/{state}` | List weather stations in a US state |
| `weather://alerts/national` | Summary of all active US alerts |

## MCP Prompts

| Prompt | Description |
|--------|-------------|
| `travel_weather` | Travel weather briefing between two locations |
| `severe_weather_summary` | Severe weather analysis for a US state |
| `clothing_recommendation` | What to wear based on weather |
| `outdoor_activity` | Is weather suitable for an activity? |

## Usage with MCP Client

```python
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

async with sse_client("http://localhost:8080/sse") as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()

        # List tools
        tools = await session.list_tools()

        # Get global forecast (works anywhere)
        result = await session.call_tool("get_global_forecast", {
            "latitude": 48.8566,
            "longitude": 2.3522
        })

        # Geocode a location
        coords = await session.call_tool("geocode_location", {
            "query": "Eiffel Tower, Paris"
        })
```

## APIs Used

All APIs are free and require no API keys:
- [National Weather Service API](https://www.weather.gov/documentation/services-web-api) - US weather data
- [Open-Meteo](https://open-meteo.com/) - Global weather, air quality, marine data
- [Nominatim](https://nominatim.org/) - Geocoding (OpenStreetMap)
- [Sunrise-Sunset.org](https://sunrise-sunset.org/api) - Sunrise/sunset times

## License

Proprietary - All rights reserved by Datavtar
