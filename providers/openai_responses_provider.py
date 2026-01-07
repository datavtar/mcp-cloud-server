"""OpenAI LLM provider implementation using Responses API."""
import os
import json
from openai import OpenAI
from typing import Any
from dataclasses import dataclass

from .base import LLMProvider


# Default model configuration
OPENAI_MAX_TOKENS = 4096
DEFAULT_OPENAI_MODEL = "gpt-5-mini"


@dataclass
class ToolCall:
    """Represents a tool call from OpenAI."""
    id: str
    name: str
    input: dict


class OpenAIResponsesProvider(LLMProvider):
    """LLM provider for OpenAI models using Responses API."""

    def __init__(self, model_type: str | None = None, model: str | None = None):
        super().__init__(model_type, model)
        self.client = OpenAI()
        self._model = model or os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)

    @property
    def model_name(self) -> str:
        """Return the model name being used."""
        return self._model

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """Convert Anthropic-format tools to OpenAI Responses API format."""
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool.get("input_schema", {})
            })
        return openai_tools

    async def complete_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system_prompt: str
    ) -> Any:
        """Send messages to OpenAI Responses API with tool definitions."""
        # Build input from messages
        input_items = self._build_input(messages)

        # Convert tools to Responses API format
        openai_tools = self._convert_tools(tools) if tools else None

        # gpt-5-mini and gpt-5-nano only support temperature=1
        kwargs = {
            "model": self._model,
            "input": input_items,
            "instructions": system_prompt,
            "max_output_tokens": OPENAI_MAX_TOKENS,
            "temperature": 1 if self._model in ("gpt-5-mini", "gpt-5-nano") else 0.7,
            "store": False,  # Don't store responses server-side
        }

        if openai_tools:
            kwargs["tools"] = openai_tools
            kwargs["tool_choice"] = "auto"

        return self.client.responses.create(**kwargs)

    def _build_input(self, messages: list[dict]) -> list[dict]:
        """Build OpenAI Responses API input from conversation history."""
        input_items = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content")

            if role == "system":
                continue  # Handled via instructions parameter

            # Handle user messages
            if role == "user" and isinstance(content, str):
                input_items.append({
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": content}]
                })

            # Handle assistant messages with function calls
            elif role == "assistant" and "function_calls" in msg:
                for fc in msg["function_calls"]:
                    input_items.append({
                        "type": "function_call",
                        "call_id": fc["call_id"],
                        "name": fc["name"],
                        "arguments": fc["arguments"]
                    })

            # Handle function call outputs (tool results)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_result":
                        input_items.append({
                            "type": "function_call_output",
                            "call_id": item.get("tool_use_id"),
                            "output": item.get("content", "")
                        })

        return input_items

    def parse_tool_calls(self, response: Any) -> list[ToolCall]:
        """Extract function calls from OpenAI Responses API response."""
        tool_calls = []

        for item in response.output:
            if item.type == "function_call":
                try:
                    args = json.loads(item.arguments) if item.arguments else {}
                except json.JSONDecodeError:
                    args = {}

                tool_calls.append(ToolCall(
                    id=item.call_id,
                    name=item.name,
                    input=args
                ))

        return tool_calls

    def format_tool_result(self, tool_use_id: str, tool_name: str, result: str) -> dict:
        """Format tool result for OpenAI Responses API format."""
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,  # This is call_id in Responses API
            "tool_name": tool_name,
            "content": result
        }

    def is_complete(self, response: Any) -> bool:
        """Check if OpenAI is done (no more function calls needed)."""
        # Check status first
        if response.status != "completed":
            return False

        # Check for function calls - if any exist, not complete
        for item in response.output:
            if item.type == "function_call":
                return False

        return True

    def extract_final_response(self, response: Any) -> str:
        """Extract text content from OpenAI Responses API response."""
        text_parts = []

        for item in response.output:
            if item.type == "message" and item.role == "assistant":
                for content in item.content:
                    if content.type == "output_text":
                        text_parts.append(content.text)

        return "".join(text_parts)

    def format_assistant_message(self, response: Any) -> dict:
        """Format OpenAI's response as an assistant message."""
        result = {"role": "assistant"}

        text_parts = []
        function_calls = []

        for item in response.output:
            if item.type == "message" and item.role == "assistant":
                for content in item.content:
                    if content.type == "output_text":
                        text_parts.append(content.text)
            elif item.type == "function_call":
                function_calls.append({
                    "call_id": item.call_id,
                    "name": item.name,
                    "arguments": item.arguments
                })

        if text_parts:
            result["content"] = "".join(text_parts)
        if function_calls:
            result["function_calls"] = function_calls

        return result

    def get_usage(self, response: Any) -> dict:
        """Extract token usage from OpenAI Responses API response."""
        if hasattr(response, 'usage') and response.usage:
            return {
                "input_tokens": response.usage.input_tokens or 0,
                "output_tokens": response.usage.output_tokens or 0
            }
        return {"input_tokens": 0, "output_tokens": 0}
