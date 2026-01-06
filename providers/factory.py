"""Factory for creating LLM provider instances."""
from .base import LLMProvider
from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider
from config import LLM_PROVIDER


def get_provider(provider_name: str | None = None) -> LLMProvider:
    """Factory to get LLM provider instance.

    Args:
        provider_name: Name of the provider to use. If None, uses default
                      from config.LLM_PROVIDER

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If unknown provider name is specified
    """
    name = provider_name or LLM_PROVIDER

    providers = {
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,
        "openai": OpenAIProvider,
    }

    if name not in providers:
        available = list(providers.keys())
        raise ValueError(f"Unknown provider: {name}. Available: {available}")

    return providers[name]()
