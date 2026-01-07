"""Factory for creating LLM provider instances."""
from .base import LLMProvider
from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider
from .vertex_provider import VertexProvider
from .openai_provider import OpenAIProvider
from config import LLM_PROVIDER


def get_provider(provider_name: str | None = None, model_type: str | None = None, model: str | None = None) -> LLMProvider:
    """Factory to get LLM provider instance.

    Args:
        provider_name: Name of the provider to use. If None, uses default
                      from config.LLM_PROVIDER
        model_type: Optional model type for providers that support multiple
                   model families (e.g., 'gemini' for Vertex AI)
        model: Optional model name override. If provided, uses this model
              instead of the default from environment.

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If unknown provider name is specified
    """
    name = provider_name or LLM_PROVIDER

    providers = {
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,      # Gemini Developer API
        "vertex": VertexProvider,      # Vertex AI platform
        "openai": OpenAIProvider,
    }

    if name not in providers:
        available = list(providers.keys())
        raise ValueError(f"Unknown provider: {name}. Available: {available}")

    return providers[name](model_type=model_type, model=model)
