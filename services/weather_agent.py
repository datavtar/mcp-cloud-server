"""Weather Agent - LLM-powered intelligent weather service."""
import json
import re
from typing import Any

from providers import get_provider
from services.tool_registry import TOOLS, TOOL_FUNCTIONS


SYSTEM_PROMPT = """You are an intelligent weather data service. Your job is to:

1. Interpret the user's weather query
2. Use the available tools to gather the requested weather data
3. Return a clean JSON response with the information

## Guidelines

- If the user provides a location name (not coordinates), use geocode_location first
- Choose the most appropriate tool(s) based on what the user asks for:
  - "current weather" / "right now" → get_current_weather
  - "forecast" / "next few days" → get_global_forecast
  - "hourly" / "next few hours" → get_global_hourly
  - "air quality" / "pollution" / "AQI" → get_air_quality
  - "UV" / "sun exposure" → get_uv_index
  - "sunrise" / "sunset" → get_sunrise_sunset
  - "alerts" / "warnings" (US only) → get_us_alerts

- If a 'service' hint is provided, prioritize that tool
- If 'output_keys' are specified, use those EXACT key names in your JSON response
- Default to Celsius for temperature unless 'expectation' says otherwise
- Always return valid JSON (no markdown code blocks, just raw JSON)

## Response Format

Your final response MUST be valid JSON. Example:
{"location": "Amsterdam", "temperature": 18, "conditions": "Partly cloudy"}

Do not wrap the JSON in markdown code blocks or add any text before/after it."""


class WeatherAgent:
    """LLM-powered weather agent that interprets queries and uses tools."""

    def __init__(self, provider_name: str | None = None):
        """Initialize the agent with a specific LLM provider.

        Args:
            provider_name: Name of LLM provider ('anthropic', 'openai', etc.)
                          If None, uses default from config
        """
        self.provider = get_provider(provider_name)

    async def process_request(self, request: dict) -> dict:
        """Process a weather request and return structured JSON response.

        Args:
            request: Dict containing:
                - query: Natural language weather query (required)
                - service: Optional hint for which tool to prioritize
                - output_keys: Optional list of specific keys for response
                - expectation: Optional guidance on format/units

        Returns:
            Dict with weather data structured per the request
        """
        user_message = self._build_user_message(request)
        messages = [{"role": "user", "content": user_message}]

        # Agentic loop - keep calling LLM until it's done
        max_iterations = 10  # Safety limit
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            response = await self.provider.complete_with_tools(
                messages=messages,
                tools=TOOLS,
                system_prompt=SYSTEM_PROMPT
            )

            # Check if LLM is done (no more tool calls)
            if self.provider.is_complete(response):
                final_text = self.provider.extract_final_response(response)
                return self._parse_json_response(final_text)

            # Handle tool calls
            tool_calls = self.provider.parse_tool_calls(response)

            if not tool_calls:
                # No tool calls but not complete - extract whatever we have
                final_text = self.provider.extract_final_response(response)
                return self._parse_json_response(final_text)

            # Add assistant's response to conversation
            messages.append(self.provider.format_assistant_message(response))

            # Execute each tool and collect results
            tool_results = []
            for tool_call in tool_calls:
                result = await self._execute_tool(tool_call)
                tool_results.append(
                    self.provider.format_tool_result(tool_call.id, result)
                )

            # Add tool results to conversation
            messages.append({"role": "user", "content": tool_results})

        # If we hit max iterations, return error
        return {"error": "Max iterations reached", "partial_data": None}

    def _build_user_message(self, request: dict) -> str:
        """Build the user message from request parameters."""
        query = request.get("query", "")
        service = request.get("service", "")
        output_keys = request.get("output_keys")
        expectation = request.get("expectation", "")

        parts = [f"Query: {query}"]

        if service:
            parts.append(f"Service hint: {service}")

        if output_keys:
            parts.append(f"Output keys (use these exact names): {output_keys}")

        if expectation:
            parts.append(f"Expectations: {expectation}")

        return "\n".join(parts)

    async def _execute_tool(self, tool_call: Any) -> str:
        """Execute a tool call and return the result as string.

        Args:
            tool_call: Tool call object with name and input attributes

        Returns:
            String result from tool execution
        """
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
        """Parse JSON from LLM response text.

        Args:
            text: Text that should contain JSON

        Returns:
            Parsed dict, or error dict if parsing fails
        """
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
