import os
import asyncio
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
OPENWHETHER_API_KEY = os.getenv("OPENWHETHER_API_KEY")

llm = ChatOpenAI(
    model="gpt-5-mini",
       api_key=os.getenv("OPENAI_API_KEY")
)

import os
import sys

APP_PYTHON = sys.executable
AVIATION_PYTHON = sys.executable

if os.name == "nt":
    # Windows - local development
    AVIATION_COMMAND = r"C:\Users\pawar\Desktop\Agentic AI Travel Planner\aviationstack-mcp\.venv\Scripts\python.exe"
    WEATHER_COMMAND = r"C:\Users\pawar\Desktop\Agentic AI Travel Planner\aviationstack-mcp\.venv\Scripts\python.exe"
    WEATHER_SERVER = r"C:\Users\pawar\Desktop\Agentic AI Travel Planner\Custom_MCP_Servers\custom_weather_mcp_server.py"

else:
    # Linux - Streamlit Cloud
    AVIATION_COMMAND = sys.executable
    WEATHER_COMMAND = sys.executable
    WEATHER_SERVER = "/mount/src/agentic-ai-travel-planner/Custom_MCP_Servers/custom_weather_mcp_server.py"

client = MultiServerMCPClient(
    {
        # Remote Mcp server
        "tavily": {
            "transport":"streamable_http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
        },
        
        # Local MCP Server
        
        "aviationstack": {
                    "transport": "stdio",
                    "command": AVIATION_COMMAND,
                    "args": [
                        "-m",
                        "aviationstack_mcp",
                        "mcp",
                        "run"
                        
                    ],
                    "env": {
                        "AVIATIONSTACK_API_KEY": AVIATIONSTACK_API_KEY
                    }
                    
                },
        
        # Custom MCP Server
        
        "weather" : {
                    "transport" : "stdio",
                    "command" : WEATHER_COMMAND,
                    "args" :[
                        WEATHER_SERVER
                        ],
                    "env" : {
                        "OPENWHETHER_API_KEY" : OPENWHETHER_API_KEY
                    }
                },
        
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
aviation_tools = {}

async def initialize_mcp():
    global search_tool
    global aviation_tools
    
    if search_tool is not None and aviation_tools:
        return
    
    tools = await client.get_tools()
    print("\nAvailable tools:")
    for tool in tools:
        print(tool.name)
    
    search_tool = next((tool for tool in tools if tool.name == "tavily_search"))
    
    aviation_tools = {tool.name: tool for tool in tools if tool.name != "tavily_search"}
    
    
    
 #functions for tavily tools   
    
async def  tavily_mcp_search(query: str):
    await initialize_mcp()
    result = await search_tool.ainvoke(
        {"query" : query}
        
    )
    return result




# functions avation stack tools

async def aviation_mcp_call(tool_name: str, tool_args: dict):
    tools = await client.get_tools()
    tool = next(
        t for t in tools
        if t.name == tool_name
    )
    result = await tool.ainvoke(
        tool_args or {}
    )
    return result

async def get_airports():
    await initialize_mcp()
    
    tool = aviation_tools.get("list_airports")
    if not tool:
        return "Airport tool unavailable"
    
    result = await tool.ainvoke({})
    return result

async def get_airlines():
    await initialize_mcp()
    tool = aviation_tools.get("list_airlines")
    if not tool:
        return "Airline tool unavailable"
    
    result = await tool.ainvoke({})
    return result





# functios for weather tools

    
weather_tool = None
forecast_tool = None

async def initialize_weather_tools():
    
    global weather_tool, forecast_tool
    
    if weather_tool is not None:
        return
    
    tools  = await client.get_tools()
    
    weather_tool = next(
        t for t in tools 
        if t.name == "get_current_weather"
    )
    
    forecast_tool = next(
        t for t in tools
        if t.name == "get_forecast"
        
    )
    
async def weather_mcp_search(city : str):
        await initialize_weather_tools()
        return await weather_tool.ainvoke(
            {
                "city" : city
            }
        )
        
async def forecast_mcp_search(city : str):
        await initialize_weather_tools()
        return await forecast_tool.ainvoke(
            {
                "city" : city
            }
        )
        
        
    ##########################################################
    # Destination Extractor
    #############################################################
    
def extract_destination(query:str):
        prompt = f"""
        Extract only the destination city or country.
        
        Query : {query}
        
        Return only destination name.
        
        """
        
        response = llm.invoke(prompt)
        return response.content.strip()
        
    
     
        

if __name__ == "__main__":
    asyncio.run(main())
    
        
    