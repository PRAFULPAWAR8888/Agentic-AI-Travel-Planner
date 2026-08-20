import os
import asyncio
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

client = MultiServerMCPClient(
    {
        "tavily": {
            "transport":"streamable_http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
        }
    }
     
)

#Tools Discovery:
async def main():
    
    tools = await client.get_tools()
    print("\nAvailable tools:")
    
    for tool in tools:
        print(tool.name)

async def main():
    tools = await client.get_tools()
    
    search_tool = next((tool for tool in tools if tool.name == "tavily_search"), None)
    
    result = await search_tool.ainvoke(
        {"query" : "Best hotels in Delhi"}
    )
    
    print(result)

search_tool = None

async def initialize_mcp():
    global search_tool
    if search_tool is not None:
        return
    
    tools = await client.get_tools()
    print("\nAvailable tools:")
    for tool in tools:
        print(tool.name)
    
    search_tool = next((tool for tool in tools if tool.name == "tavily_search"))
    
async def  tavily_mcp_search(query: str):
    await initialize_mcp()
    result = await search_tool.ainvoke(
        {"query" : query}
        
    )
    return result

if __name__ == "__main__":
    asyncio.run(main())
    
        
    