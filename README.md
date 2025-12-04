# MCP Cloud Server

A Model Context Protocol (MCP) server built with FastMCP that exposes weather-related tools via Server-Sent Events (SSE). Designed for deployment on Google Cloud Run.

## Features

- **Weather Alerts**: Get active weather alerts for any US state
- **Weather Forecast**: Get multi-day forecasts for any location (latitude/longitude)
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

## MCP Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_alerts` | Get weather alerts for a US state | `state`: Two-letter state code (e.g., CA, NY) |
| `get_forecast` | Get weather forecast for a location | `latitude`, `longitude`: Coordinates |

## Usage with MCP Client

```python
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

async with sse_client("http://localhost:8080/sse") as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()

        # List tools
        tools = await session.list_tools()

        # Get forecast
        result = await session.call_tool("get_forecast", {
            "latitude": 40.7128,
            "longitude": -74.0060
        })
```

## API

This server uses the [National Weather Service API](https://www.weather.gov/documentation/services-web-api) for weather data. No API key required.

## License

Proprietary - All rights reserved by Datavtar
