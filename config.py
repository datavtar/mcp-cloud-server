# API Base URLs
NWS_API_BASE = "https://api.weather.gov"
OPEN_METEO_API_BASE = "https://api.open-meteo.com/v1"
NOMINATIM_API_BASE = "https://nominatim.openstreetmap.org"
SUNRISE_SUNSET_API_BASE = "https://api.sunrise-sunset.org"

# HTTP Headers
USER_AGENT = "mcp-cloud-server/1.0 (https://github.com/datavtar/mcp-cloud-server)"

# Request Settings
DEFAULT_TIMEOUT = 30.0

# LLM Provider Settings
# Default provider for the intelligent weather service
# Options: "anthropic", "openai" (future), "gemini" (future)
LLM_PROVIDER = "anthropic"

# Anthropic settings
LLM_MODEL = "claude-haiku-4-5"
LLM_MAX_TOKENS = 4096

# Pricing per million tokens (USD)
LLM_PRICING = {
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
    "claude-sonnet-4-5-20250514": {"input": 6.0, "output": 22.5},
    "claude-opus-4-5-20250514": {"input": 15.0, "output": 75.0},
}
