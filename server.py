import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route
from starlette.responses import JSONResponse

from tools import register_all_tools
from resources import register_all_resources
from prompts import register_all_prompts

# Initialize FastMCP server
mcp = FastMCP("weather")

# Register all tools, resources, and prompts
register_all_tools(mcp)
register_all_resources(mcp)
register_all_prompts(mcp)

# Get the internal Starlette app
app = mcp.sse_app()


# Blanket REST API endpoint - LLM interprets any request
async def services_api(request):
    """Blanket endpoint for any service request. LLM decides what to do.

    POST /api/services
    Body: {
        "request": "Weather in Amsterdam for next 3 days",  # Required
        "context": "Planning a trip",                        # Optional
        "output_format": {"keys": ["temp"], "units": "F"},   # Optional
        "provider": "anthropic",                             # Optional (anthropic, openai, gemini, vertex)
        "type": "gemini"                                     # Optional (model type for vertex provider)
    }
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"error": "Invalid JSON body"},
            status_code=400
        )

    if "request" not in body:
        return JSONResponse(
            {"error": "Missing required field: request"},
            status_code=400
        )

    # Import here to avoid circular imports
    from services.agent import ServiceAgent

    # Extract provider and type if specified, otherwise use defaults
    provider = body.pop("provider", None)
    model_type = body.pop("type", None)

    try:
        agent = ServiceAgent(provider_name=provider, model_type=model_type)
        result = await agent.process_request(body)
        return JSONResponse(result)
    except ValueError as e:
        # Invalid provider name or model type
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse(
            {"error": f"Internal error: {str(e)}"},
            status_code=500
        )


# Add REST API route
app.routes.append(Route("/api/services", services_api, methods=["POST"]))


# Add CORS middleware to allow requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting MCP server on 0.0.0.0:{port}...")
    print(f"REST API available at: http://0.0.0.0:{port}/api/services")
    uvicorn.run(app, host="0.0.0.0", port=port)
