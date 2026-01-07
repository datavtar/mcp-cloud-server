"""Abstract base class for LLM providers."""
from abc import ABC, abstractmethod
from typing import Any

from config import MODELS, DEFAULT_PRICING


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    Implement this class to add support for new LLM providers
    (OpenAI, Gemini, etc.).
    """

    def __init__(self, model_type: str | None = None, model: str | None = None):
        """Initialize provider with optional model type and model override.

        Args:
            model_type: Optional model type/family (e.g., 'gemini', 'palm').
                       Used by providers that support multiple model families.
            model: Optional model name override. If provided, uses this model
                  instead of the default from environment.
        """
        self._model_type = model_type
        self._requested_model = model

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name being used."""
        pass

    @property
    def pricing(self) -> dict:
        """Return pricing per million tokens from centralized config.

        Returns:
            Dict with 'input' and 'output' keys containing USD cost per million tokens
        """
        return MODELS.get(self.model_name, {}).get("pricing", DEFAULT_PRICING)

    @abstractmethod
    async def complete_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system_prompt: str
    ) -> Any:
        """Send messages to LLM with tool definitions.

        Args:
            messages: Conversation history
            tools: Tool definitions in provider-specific format
            system_prompt: System instructions for the LLM

        Returns:
            Provider-specific response object
        """
        pass

    @abstractmethod
    def parse_tool_calls(self, response: Any) -> list[Any]:
        """Extract tool calls from provider-specific response.

        Args:
            response: Provider-specific response object

        Returns:
            List of tool call objects
        """
        pass

    @abstractmethod
    def format_tool_result(self, tool_use_id: str, tool_name: str, result: str) -> dict:
        """Format tool result for provider-specific message format.

        Args:
            tool_use_id: Unique identifier for the tool call
            tool_name: Name of the tool that was called
            result: String result from tool execution

        Returns:
            Formatted tool result dict
        """
        pass

    @abstractmethod
    def is_complete(self, response: Any) -> bool:
        """Check if LLM is done (no more tool calls needed).

        Args:
            response: Provider-specific response object

        Returns:
            True if LLM has finished, False if more tool calls needed
        """
        pass

    @abstractmethod
    def extract_final_response(self, response: Any) -> str:
        """Extract final text response from LLM.

        Args:
            response: Provider-specific response object

        Returns:
            Final text content from the LLM
        """
        pass

    @abstractmethod
    def format_assistant_message(self, response: Any) -> dict:
        """Format the assistant's response as a message for conversation history.

        Args:
            response: Provider-specific response object

        Returns:
            Message dict suitable for appending to messages list
        """
        pass

    @abstractmethod
    def get_usage(self, response: Any) -> dict:
        """Extract token usage from response.

        Args:
            response: Provider-specific response object

        Returns:
            Dict with 'input_tokens' and 'output_tokens'
        """
        pass
