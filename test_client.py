import asyncio
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

# Your Cloud Run URL
SERVER_URL = "https://mcp-server-795733096524.us-central1.run.app/sse"

async def run():
    print(f"Connecting to {SERVER_URL}...")
    
    # Connect to the SSE endpoint
    async with sse_client(SERVER_URL) as (read_stream, write_stream):
        # Start the MCP session
        async with ClientSession(read_stream, write_stream) as session:
            
            # 1. Initialize
            await session.initialize()
            print("✅ Connected and initialized!")
            
            # 2. List Available Tools
            tools = await session.list_tools()
            print(f"\nFound {len(tools.tools)} tools:")
            for tool in tools.tools:
                print(f" - {tool.name}: {tool.description}")

            # 3. Call a Tool (Test logic)
            print("\nTesting 'get_forecast' for New York...")
            result = await session.call_tool("get_forecast", arguments={
                "latitude": 40.7128,
                "longitude": -74.0060
            })
            
            # 4. Print Result
            print("\n--- TOOL RESULT ---")
            # The result content is a list of text or image blocks
            for content in result.content:
                print(content.text)

if __name__ == "__main__":
    asyncio.run(run())
