"""Geocoding tools using Nominatim (OpenStreetMap) - works worldwide."""
from utils.http_client import make_nominatim_request


def register_geocoding_tools(mcp):
    """Register all geocoding tools with the MCP server."""

    @mcp.tool()
    async def geocode_location(query: str) -> str:
        """Convert a place name or address to coordinates.
        Args:
            query: Place name, address, or location to search for (e.g., "Paris, France" or "1600 Pennsylvania Ave, Washington DC")
        """
        data = await make_nominatim_request("search", {"q": query, "limit": 5})

        if not data:
            return "Unable to geocode location. Try a more specific query."

        if isinstance(data, list) and len(data) == 0:
            return f"No results found for '{query}'. Try a more specific query."

        results = []
        for item in data[:5]:
            lat = item.get("lat", "N/A")
            lon = item.get("lon", "N/A")
            display_name = item.get("display_name", "Unknown")
            location_type = item.get("type", "unknown")
            results.append(
                f"📍 {display_name}\n"
                f"   Coordinates: {lat}, {lon}\n"
                f"   Type: {location_type}"
            )

        return "\n\n".join(results)

    @mcp.tool()
    async def reverse_geocode(latitude: float, longitude: float) -> str:
        """Convert coordinates to a place name/address.
        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
        """
        data = await make_nominatim_request(
            "reverse",
            {"lat": latitude, "lon": longitude},
        )

        if not data:
            return "Unable to reverse geocode coordinates."

        if "error" in data:
            return f"Error: {data['error']}"

        display_name = data.get("display_name", "Unknown location")
        address = data.get("address", {})

        result = [f"📍 {display_name}", ""]

        if address:
            result.append("Address components:")
            for key, value in address.items():
                if key not in ["ISO3166-2-lvl4", "ISO3166-2-lvl6", "ISO3166-2-lvl15"]:
                    result.append(f"  {key.replace('_', ' ').title()}: {value}")

        return "\n".join(result)
