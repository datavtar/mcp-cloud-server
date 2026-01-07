"""Service Agent - LLM-powered intelligent service layer."""
import json
import re
import logging
import time
from typing import Any

from providers import get_provider
from services.tool_registry import TOOLS, TOOL_FUNCTIONS
from config import MODELS

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)


SYSTEM_PROMPT = """You are an automated service agent in an agentic workflow. Your job is to:

1. Interpret the user's request
2. Use the available tools to fulfill the request
3. Return a clean JSON response with the results

## CRITICAL RULES

- NEVER ask questions or request clarification - this is an automated API, not a conversation
- ALWAYS make reasonable assumptions when requests are ambiguous
- ALWAYS execute the task and return data, never return error messages about needing more info
- If something looks like a postal/zip code (e.g., "2020, BE"), treat it as a location code
- Default to CURRENT weather unless explicitly asked for historical or forecast data

## Available Tools

- geocode_location: Convert place names/postal codes to coordinates
- get_current_weather: Current weather conditions (DEFAULT - use this unless asked otherwise)
- get_global_forecast: Multi-day weather forecast
- get_global_hourly: Hourly weather forecast
- get_air_quality: Air quality index and pollutants
- get_uv_index: UV exposure levels
- get_sunrise_sunset: Sunrise/sunset times
- get_us_alerts: US weather alerts

## Guidelines

- If a location is given, use geocode_location first to get coordinates
- If 'output_format' specifies keys, use those EXACT key names in your response
- If 'output_format' specifies units (e.g., "fahrenheit"), convert accordingly
- Use 'context' to better understand the user's intent

## Response Format

Your final response MUST be valid JSON with only the requested data.
NEVER include explanations, questions, or clarification requests in your response.
Do not wrap the JSON in markdown code blocks or add any text before/after it.

## Examples

Request: "Weather in 2020, BE"
Response: {"location": "Antwerpen, Belgium", "temperature": 5.2, "conditions": "Cloudy"}

Request: "Temperature in NYC in fahrenheit"
Response: {"temperature": 42}

Request: "What's the temp and humidity in Paris? Return as t and h"
Response: {"t": 12, "h": 78}

Request: "Amsterdam forecast for 3 days"
Response: {"location": "Amsterdam", "forecast": [{"date": "2025-01-07", "high": 8, "low": 3}, {"date": "2025-01-08", "high": 7, "low": 2}, {"date": "2025-01-09", "high": 9, "low": 4}]}"""


class ServiceAgent:
    """LLM-powered agent that interprets requests and uses tools."""

    def __init__(self, provider_name: str | None = None, model_type: str | None = None, model: str | None = None):
        """Initialize the agent with a specific LLM provider.

        Args:
            provider_name: Name of LLM provider ('anthropic', 'openai', 'gemini', 'vertex')
                          If None, uses default from config
            model_type: Optional model type for providers that support multiple
                       model families (e.g., 'gemini' for Vertex AI)
            model: Optional model name override. If provided, uses this model
                  instead of the default from environment.
        """
        self.provider = get_provider(provider_name, model_type, model)

    async def process_request(self, request: dict, meta_fields: list | bool | None = None, raw: bool = False) -> dict:
        """Process a request and return structured JSON response.

        Args:
            request: Dict containing:
                - request: The user's request (required)
                - context: Optional context to help interpret the request
                - output_format: Optional dict with keys/units preferences
            meta_fields: If True, include all meta info. If list, include specific fields.
                        Available: model, provider, iterations, usage, cost, latency_ms, tools, logs
            raw: If True, return unwrapped response (backward compatibility)

        Returns:
            Dict with structured response data, optionally wrapped in {"data": ..., "meta": ...}
        """
        start_time = time.time()
        tools_used = []  # Track tool calls: {"name": str, "input": dict, "iteration": int}
        logs = []  # Track execution logs

        user_message = self._build_user_message(request)
        messages = [{"role": "user", "content": user_message}]

        logger.info(f"{'='*60}")
        logger.info(f"REQUEST: {request.get('request', '')[:100]}")
        if request.get('context'):
            logger.info(f"CONTEXT: {request.get('context')}")

        # Token tracking
        total_input_tokens = 0
        total_output_tokens = 0

        # Agentic loop - keep calling LLM until it's done
        max_iterations = 10  # Safety limit
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"--- Iteration {iteration} ---")

            response = await self.provider.complete_with_tools(
                messages=messages,
                tools=TOOLS,
                system_prompt=SYSTEM_PROMPT
            )

            # Track tokens
            usage = self.provider.get_usage(response)
            total_input_tokens += usage["input_tokens"]
            total_output_tokens += usage["output_tokens"]

            # Check if LLM is done (no more tool calls)
            if self.provider.is_complete(response):
                final_text = self.provider.extract_final_response(response)
                logger.info(f"MODEL COMPLETE - generating response")
                logs.append(f"[{iteration}] MODEL COMPLETE")
                result = self._parse_json_response(final_text)
                logger.info(f"RESPONSE: {json.dumps(result)[:200]}...")
                self._log_cost(total_input_tokens, total_output_tokens)
                logger.info(f"{'='*60}")
                return self._wrap_response(
                    result, meta_fields, raw,
                    total_input_tokens, total_output_tokens,
                    iteration, tools_used, logs, start_time
                )

            # Handle tool calls
            tool_calls = self.provider.parse_tool_calls(response)

            if not tool_calls:
                # No tool calls but not complete - extract whatever we have
                final_text = self.provider.extract_final_response(response)
                logger.info(f"NO TOOL CALLS - extracting response")
                logs.append(f"[{iteration}] NO TOOL CALLS - extracting response")
                result = self._parse_json_response(final_text)
                return self._wrap_response(
                    result, meta_fields, raw,
                    total_input_tokens, total_output_tokens,
                    iteration, tools_used, logs, start_time
                )

            # Add assistant's response to conversation
            messages.append(self.provider.format_assistant_message(response))

            # Execute each tool and collect results
            tool_results = []
            for tool_call in tool_calls:
                logger.info(f"TOOL CALL: {tool_call.name}({json.dumps(tool_call.input)})")
                tools_used.append({
                    "name": tool_call.name,
                    "input": tool_call.input,
                    "iteration": iteration
                })
                logs.append(f"[{iteration}] TOOL: {tool_call.name}({json.dumps(tool_call.input)})")
                tool_result = await self._execute_tool(tool_call)
                logger.info(f"TOOL RESULT: {tool_result[:150]}..." if len(tool_result) > 150 else f"TOOL RESULT: {tool_result}")
                tool_results.append(
                    self.provider.format_tool_result(tool_call.id, tool_call.name, tool_result)
                )

            # Add tool results to conversation
            messages.append({"role": "user", "content": tool_results})

        # If we hit max iterations, return error
        logger.error("MAX ITERATIONS REACHED")
        logs.append(f"[{iteration}] ERROR: Max iterations reached")
        result = {"error": "Max iterations reached", "partial_data": None}
        return self._wrap_response(
            result, meta_fields, raw,
            total_input_tokens, total_output_tokens,
            iteration, tools_used, logs, start_time
        )

    def _log_cost(self, input_tokens: int, output_tokens: int) -> None:
        """Log token usage and estimated cost."""
        pricing = self.provider.pricing
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        logger.info(
            f"MODEL: {self.provider.model_name} | "
            f"TOKENS: {input_tokens} in / {output_tokens} out | "
            f"COST: ${total_cost:.6f} (${input_cost:.6f} + ${output_cost:.6f})"
        )

    def _wrap_response(
        self,
        result: dict,
        meta_fields: list | bool | None,
        raw: bool,
        input_tokens: int,
        output_tokens: int,
        iterations: int,
        tools_used: list,
        logs: list,
        start_time: float
    ) -> dict:
        """Wrap result with optional meta information.

        Args:
            result: The parsed JSON result
            meta_fields: If True, include all meta. If list, include specific fields.
            raw: If True, return unwrapped result (backward compatibility)
            input_tokens: Total input tokens used
            output_tokens: Total output tokens used
            iterations: Number of LLM iterations
            tools_used: List of tool calls made
            logs: Execution logs
            start_time: Request start time for latency calculation

        Returns:
            Wrapped response {"data": result} or {"data": result, "meta": {...}}
            Or unwrapped result if raw=True
        """
        if raw:
            return result

        latency_ms = int((time.time() - start_time) * 1000)

        if meta_fields:
            meta = self._build_meta(
                meta_fields=meta_fields,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                iterations=iterations,
                tools_used=tools_used,
                logs=logs,
                latency_ms=latency_ms
            )
            return {"data": result, "meta": meta}

        return {"data": result}

    def _build_meta(
        self,
        meta_fields: list | bool,
        input_tokens: int,
        output_tokens: int,
        iterations: int,
        tools_used: list,
        logs: list,
        latency_ms: int
    ) -> dict:
        """Build meta dict based on requested fields.

        Args:
            meta_fields: True for all fields, or list of specific field names
            input_tokens: Total input tokens
            output_tokens: Total output tokens
            iterations: Number of LLM calls
            tools_used: List of tool calls
            logs: Execution logs
            latency_ms: Total latency in milliseconds

        Returns:
            Dict with requested meta fields
        """
        all_fields = meta_fields is True
        fields = meta_fields if isinstance(meta_fields, list) else []

        meta = {}

        if all_fields or "model" in fields:
            meta["model"] = self.provider.model_name

        if all_fields or "provider" in fields:
            model_config = MODELS.get(self.provider.model_name, {})
            meta["provider"] = model_config.get("provider", "unknown")

        if all_fields or "iterations" in fields:
            meta["iterations"] = iterations

        if all_fields or "usage" in fields:
            meta["usage"] = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            }

        if all_fields or "cost" in fields:
            pricing = self.provider.pricing
            input_cost = (input_tokens / 1_000_000) * pricing["input"]
            output_cost = (output_tokens / 1_000_000) * pricing["output"]
            meta["cost"] = {
                "input": round(input_cost, 6),
                "output": round(output_cost, 6),
                "total": round(input_cost + output_cost, 6)
            }

        if all_fields or "latency_ms" in fields:
            meta["latency_ms"] = latency_ms

        if all_fields or "tools" in fields:
            meta["tools"] = tools_used

        if all_fields or "logs" in fields:
            meta["logs"] = logs

        return meta

    def _build_user_message(self, request: dict) -> str:
        """Build the user message from request parameters."""
        user_request = request.get("request", "")
        context = request.get("context", "")
        output_format = request.get("output_format")

        parts = [user_request]

        if context:
            parts.append(f"\nContext: {context}")

        if output_format:
            if isinstance(output_format, dict):
                if "keys" in output_format:
                    parts.append(f"\nOutput keys (use these exact names): {output_format['keys']}")
                if "units" in output_format:
                    parts.append(f"\nUnits: {output_format['units']}")
            else:
                parts.append(f"\nOutput format: {output_format}")

        return "".join(parts)

    async def _execute_tool(self, tool_call: Any) -> str:
        """Execute a tool call and return the result as string."""
        tool_name = tool_call.name
        tool_input = tool_call.input

        func = TOOL_FUNCTIONS.get(tool_name)
        if not func:
            return f"Error: Unknown tool '{tool_name}'"

        try:
            result = await func(**tool_input)
            return result
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"

    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON from LLM response text."""
        if not text:
            return {"error": "Empty response from LLM"}

        # Try to parse the text as JSON directly
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        matches = re.findall(json_pattern, text)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # Try to find JSON object in the text
        brace_pattern = r'\{[\s\S]*\}'
        matches = re.findall(brace_pattern, text)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # If all parsing fails, return the raw text in an error response
        return {"error": "Could not parse JSON from response", "raw_response": text}
