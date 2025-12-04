import uvicorn
import os
from fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware

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
    print(f"Starting MCP weather server on 0.0.0.0:{port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
