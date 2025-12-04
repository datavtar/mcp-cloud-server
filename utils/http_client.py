from typing import Any
import httpx
from config import (
    NWS_API_BASE,
    NOMINATIM_API_BASE,
    USER_AGENT,
    DEFAULT_TIMEOUT,
)


async def make_request(
    url: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any] | None:
    """Make an async HTTP GET request with error handling."""
    default_headers = {"User-Agent": USER_AGENT}
    if headers:
        default_headers.update(headers)

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(
                url,
                headers=default_headers,
                params=params,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None


async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper headers."""
    headers = {"Accept": "application/geo+json"}
    return await make_request(url, headers=headers)


async def make_nominatim_request(
    endpoint: str,
    params: dict[str, Any],
) -> dict[str, Any] | list[dict[str, Any]] | None:
    """Make a request to the Nominatim API with proper headers."""
    url = f"{NOMINATIM_API_BASE}/{endpoint}"
    params["format"] = "json"
    return await make_request(url, params=params)
