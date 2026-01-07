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
# Default provider for the intelligent service
# Options: "anthropic", "openai", "gemini", "vertex"
LLM_PROVIDER = "anthropic"

# Note: Model defaults are configured in .env (e.g., ANTHROPIC_MODEL, OPENAI_MODEL)

# Unified model configuration (provider + pricing)
MODELS = {
    # Anthropic
    "claude-haiku-4-5": {"provider": "anthropic", "pricing": {"input": 1.00, "output": 5.00}},
    "claude-sonnet-4": {"provider": "anthropic", "pricing": {"input": 3.00, "output": 15.00}},
    "claude-opus-4": {"provider": "anthropic", "pricing": {"input": 15.00, "output": 75.00}},

    # OpenAI
    "gpt-5-mini": {"provider": "openai", "pricing": {"input": 0.25, "output": 2.00}},
    "gpt-5-nano": {"provider": "openai", "pricing": {"input": 0.05, "output": 0.40}},

    # Gemini (Developer API)
    "gemini-3-flash-preview": {"provider": "gemini", "pricing": {"input": 0.50, "output": 3.00}},
}

# Default pricing if model not found
DEFAULT_PRICING = {"input": 1.00, "output": 5.00}
