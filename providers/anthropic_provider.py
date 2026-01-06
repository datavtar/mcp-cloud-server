"""Anthropic Claude LLM provider implementation."""
import anthropic
from typing import Any

from .base import LLMProvider
from config import LLM_MODEL, LLM_MAX_TOKENS


class AnthropicProvider(LLMProvider):
    """LLM provider for Anthropic Claude models."""

    def __init__(self):
        self.client = anthropic.Anthropic()
        self._model = LLM_MODEL

    @property
    def model_name(self) -> str:
        """Return the model name being used."""
        return self._model

    @property
    def pricing(self) -> dict:
        """Return pricing per million tokens for the current model."""
        # Pricing for claude-haiku-4-5
        return {"input": 1.0, "output": 5.0}

    async def complete_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system_prompt: str
    ) -> Any:
        """Send messages to Claude with tool definitions."""
        return self.client.messages.create(
            model=LLM_MODEL,
            max_tokens=LLM_MAX_TOKENS,
            system=system_prompt,
            tools=tools,
            messages=messages
        )

    def parse_tool_calls(self, response: Any) -> list[Any]:
        """Extract tool_use blocks from Claude's response."""
        return [block for block in response.content if block.type == "tool_use"]

    def format_tool_result(self, tool_use_id: str, tool_name: str, result: str) -> dict:
        """Format tool result for Claude's expected format."""
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": result
        }

    def is_complete(self, response: Any) -> bool:
        """Check if Claude is done (stop_reason is end_turn)."""
        return response.stop_reason == "end_turn"

    def extract_final_response(self, response: Any) -> str:
        """Extract text content from Claude's response."""
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""

    def format_assistant_message(self, response: Any) -> dict:
        """Format Claude's response as an assistant message."""
        return {"role": "assistant", "content": response.content}

    def get_usage(self, response: Any) -> dict:
        """Extract token usage from Claude's response."""
        return {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens
        }
