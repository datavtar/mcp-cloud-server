"""Factory for creating LLM provider instances."""
import os
from .base import LLMProvider
from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider
from .vertex_provider import VertexProvider
from .openai_provider import OpenAIProvider
from .openai_responses_provider import OpenAIResponsesProvider
from config import LLM_PROVIDER, MODELS


def get_provider(provider_name: str | None = None, model_type: str | None = None, model: str | None = None) -> LLMProvider:
    """Factory to get LLM provider instance.

    Args:
        provider_name: Name of the provider to use. If None, infers from model
                      or uses default from config.LLM_PROVIDER
        model_type: Optional model type for providers that support multiple
                   model families (e.g., 'gemini' for Vertex AI)
        model: Optional model name. If provider not specified, infers provider
              from model name using MODELS config.

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If unknown provider name is specified
    """
    # Infer provider from model if not specified
    if provider_name is None and model:
        provider_name = MODELS.get(model, {}).get("provider")

    name = provider_name or LLM_PROVIDER

    providers = {
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,      # Gemini Developer API
        "vertex": VertexProvider,      # Vertex AI platform
        "openai": OpenAIProvider,      # Chat Completions API (default)
    }

    if name not in providers:
        available = list(providers.keys())
        raise ValueError(f"Unknown provider: {name}. Available: {available}")

    # For OpenAI, check if Responses API is requested via env
    if name == "openai":
        api_mode = os.environ.get("OPENAI_API_MODE", "completions")
        if api_mode == "responses":
            return OpenAIResponsesProvider(model_type=model_type, model=model)

    return providers[name](model_type=model_type, model=model)
