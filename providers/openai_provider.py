"""OpenAI LLM provider implementation."""
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


class OpenAIProvider(LLMProvider):
    """LLM provider for OpenAI models."""

    def __init__(self, model_type: str | None = None, model: str | None = None):
        super().__init__(model_type, model)
        self.client = OpenAI()
        self._model = model or os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)

    @property
    def model_name(self) -> str:
        """Return the model name being used."""
        return self._model

    @property
    def pricing(self) -> dict:
        """Return pricing per million tokens for the current model."""
        # Pricing for gpt-5-mini
        return {"input": 0.25, "output": 2.00}

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """Convert Anthropic-format tools to OpenAI format."""
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("input_schema", {})
                }
            })
        return openai_tools

    async def complete_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system_prompt: str
    ) -> Any:
        """Send messages to OpenAI with tool definitions."""
        # Build messages with system prompt
        openai_messages = self._build_messages(messages, system_prompt)

        # Convert tools to OpenAI format
        openai_tools = self._convert_tools(tools) if tools else None

        # Make the API call
        # gpt-5-mini and gpt-5-nano only support temperature=1
        kwargs = {
            "model": self._model,
            "messages": openai_messages,
            "max_completion_tokens": OPENAI_MAX_TOKENS,
            "temperature": 1 if self._model in ("gpt-5-mini", "gpt-5-nano") else 0.7,
        }

        if openai_tools:
            kwargs["tools"] = openai_tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)

        return response

    def _build_messages(self, messages: list[dict], system_prompt: str) -> list[dict]:
        """Build OpenAI message list from conversation history."""
        openai_messages = []

        # Add system prompt first
        if system_prompt:
            openai_messages.append({
                "role": "system",
                "content": system_prompt
            })

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content")

            if role == "system":
                continue  # Already handled above

            # Handle assistant messages with tool_calls (pass through as-is)
            if role == "assistant" and "tool_calls" in msg:
                assistant_msg = {"role": "assistant"}
                if content:
                    assistant_msg["content"] = content
                assistant_msg["tool_calls"] = msg["tool_calls"]
                openai_messages.append(assistant_msg)
                continue

            # Handle different content types
            if isinstance(content, str):
                openai_messages.append({
                    "role": role,
                    "content": content
                })
            elif isinstance(content, list):
                # Handle tool results from previous iterations
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_result":
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": item.get("tool_use_id", ""),
                            "name": item.get("tool_name", ""),
                            "content": item.get("content", "")
                        })

        return openai_messages

    def parse_tool_calls(self, response: Any) -> list[ToolCall]:
        """Extract tool calls from OpenAI's response."""
        tool_calls = []

        if not response.choices:
            return tool_calls

        message = response.choices[0].message

        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {}

                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    input=args
                ))

        return tool_calls

    def format_tool_result(self, tool_use_id: str, tool_name: str, result: str) -> dict:
        """Format tool result for OpenAI's expected format."""
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "tool_name": tool_name,
            "content": result
        }

    def is_complete(self, response: Any) -> bool:
        """Check if OpenAI is done (no more tool calls needed)."""
        if not response.choices:
            return True

        choice = response.choices[0]
        finish_reason = choice.finish_reason

        # OpenAI returns "stop" when done, "tool_calls" when tools need execution
        if finish_reason == "stop":
            return True

        # If there are tool calls, we're not complete
        if choice.message.tool_calls:
            return False

        return True

    def extract_final_response(self, response: Any) -> str:
        """Extract text content from OpenAI's response."""
        if not response.choices:
            return ""

        message = response.choices[0].message
        return message.content or ""

    def format_assistant_message(self, response: Any) -> dict:
        """Format OpenAI's response as an assistant message."""
        if not response.choices:
            return {"role": "assistant", "content": ""}

        message = response.choices[0].message

        # For OpenAI, we need to preserve tool calls for the conversation
        result = {"role": "assistant"}

        if message.content:
            result["content"] = message.content

        if message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]

        return result

    def get_usage(self, response: Any) -> dict:
        """Extract token usage from OpenAI's response."""
        if hasattr(response, 'usage') and response.usage:
            return {
                "input_tokens": response.usage.prompt_tokens or 0,
                "output_tokens": response.usage.completion_tokens or 0
            }
        return {"input_tokens": 0, "output_tokens": 0}
