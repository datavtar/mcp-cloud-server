"""Google Vertex AI LLM provider implementation."""
import os
from google import genai
from google.genai import types
from typing import Any
from dataclasses import dataclass

from .base import LLMProvider


# Model type to model name mapping
MODEL_MAP = {
    "gemini": "gemini-3-flash-preview",
    # Future model types can be added here
    # "palm": "palm-2-...",
}

# Default configuration
VERTEX_MAX_TOKENS = 8192
DEFAULT_MODEL_TYPE = "gemini"
DEFAULT_VERTEX_MODEL = "gemini-3-flash-preview"


@dataclass
class ToolCall:
    """Represents a tool call from Vertex AI."""
    id: str
    name: str
    input: dict


class VertexProvider(LLMProvider):
    """LLM provider for Google Vertex AI platform."""

    def __init__(self, model_type: str | None = None, model: str | None = None):
        super().__init__(model_type, model)
        api_key = os.environ.get("GOOGLE_CLOUD_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_CLOUD_API_KEY environment variable is required for Vertex provider")

        self.client = genai.Client(api_key=api_key, vertexai=True)

        # Model override takes precedence
        if model:
            self._model = model
            self._effective_type = model_type or DEFAULT_MODEL_TYPE
        else:
            # Use MODEL_MAP based on model_type, or env default
            effective_type = model_type or DEFAULT_MODEL_TYPE
            if effective_type not in MODEL_MAP:
                available = list(MODEL_MAP.keys())
                raise ValueError(f"Unknown model type: {effective_type}. Available: {available}")
            self._model = os.environ.get("VERTEX_MODEL", MODEL_MAP[effective_type])
            self._effective_type = effective_type

    @property
    def model_name(self) -> str:
        """Return the model name being used."""
        return self._model

    def _convert_tools(self, tools: list[dict]) -> list[types.Tool]:
        """Convert Anthropic-format tools to Vertex AI format."""
        function_declarations = []
        for tool in tools:
            declaration = {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool.get("input_schema", {})
            }
            function_declarations.append(declaration)

        return [types.Tool(function_declarations=function_declarations)]

    async def complete_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system_prompt: str
    ) -> Any:
        """Send messages to Vertex AI with tool definitions."""
        contents = self._build_contents(messages)

        vertex_tools = self._convert_tools(tools) if tools else None

        config_dict = {
            "temperature": 0.7,
        }

        if vertex_tools:
            config_dict["tools"] = vertex_tools
            config_dict["tool_config"] = types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode="auto")
            )

        config = types.GenerateContentConfig(**config_dict)
        config.system_instruction = system_prompt

        response = self.client.models.generate_content(
            model=self._model,
            contents=contents,
            config=config,
        )

        return response

    def _build_contents(self, messages: list[dict]) -> list[types.Content]:
        """Build Vertex AI content list from messages."""
        contents = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content")

            if role == "assistant":
                role = "model"
            elif role == "system":
                continue

            if isinstance(content, str):
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=content)]
                    )
                )
            elif isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_result":
                        parts.append(
                            types.Part.from_function_response(
                                name=item.get("tool_name", "unknown"),
                                response={"result": item.get("content", "")}
                            )
                        )
                if parts:
                    contents.append(types.Content(role=role, parts=parts))

        return contents

    def parse_tool_calls(self, response: Any) -> list[ToolCall]:
        """Extract function calls from Vertex AI's response."""
        tool_calls = []

        if not response.candidates:
            return tool_calls

        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            return tool_calls

        for i, part in enumerate(candidate.content.parts):
            if hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                tool_calls.append(ToolCall(
                    id=f"vertex_tool_{i}",
                    name=fc.name,
                    input=dict(fc.args) if fc.args else {}
                ))

        return tool_calls

    def format_tool_result(self, tool_use_id: str, tool_name: str, result: str) -> dict:
        """Format tool result for Vertex AI's expected format."""
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "tool_name": tool_name,
            "content": result
        }

    def is_complete(self, response: Any) -> bool:
        """Check if Vertex AI is done (no more tool calls needed)."""
        if not response.candidates:
            return True

        candidate = response.candidates[0]

        if not candidate.content or not candidate.content.parts:
            return True

        # Check for function calls FIRST - if there are any, we're not complete
        for part in candidate.content.parts:
            if hasattr(part, "function_call") and part.function_call:
                return False

        return True

    def extract_final_response(self, response: Any) -> str:
        """Extract text content from Vertex AI's response."""
        if not response.candidates:
            return ""

        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            return ""

        text_parts = []
        for part in candidate.content.parts:
            if hasattr(part, "text") and part.text:
                text_parts.append(part.text)

        return "".join(text_parts)

    def format_assistant_message(self, response: Any) -> dict:
        """Format Vertex AI's response as an assistant message."""
        if not response.candidates:
            return {"role": "model", "content": ""}

        candidate = response.candidates[0]

        parts = []
        if candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if hasattr(part, "text") and part.text:
                    parts.append({"type": "text", "text": part.text})
                elif hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    parts.append({
                        "type": "function_call",
                        "name": fc.name,
                        "args": dict(fc.args) if fc.args else {}
                    })

        return {"role": "model", "content": parts if parts else ""}

    def get_usage(self, response: Any) -> dict:
        """Extract token usage from Vertex AI's response."""
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            return {
                "input_tokens": getattr(response.usage_metadata, 'prompt_token_count', 0) or 0,
                "output_tokens": getattr(response.usage_metadata, 'candidates_token_count', 0) or 0
            }
        return {"input_tokens": 0, "output_tokens": 0}
