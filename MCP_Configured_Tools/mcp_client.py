
import os
import sys
import asyncio

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI


# ============================================================
# Environment Variables
# ============================================================

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
OPENWHETHER_API_KEY = os.getenv("OPENWHETHER_API_KEY")


# ============================================================
# LLM
# ============================================================

llm = ChatOpenAI(
    model="gpt-5-mini",
    api_key=os.getenv("OPENAI_API_KEY")
)


# ============================================================
# Python / MCP Server Configuration
# ============================================================

APP_PYTHON = sys.executable

# Use the same Python environment for MCP servers.
# This works both locally and on Streamlit Cloud.
AVIATION_COMMAND = sys.executable
WEATHER_COMMAND = sys.executable


# Get project root directory
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


# Weather MCP server path
WEATHER_SERVER = os.path.join(
    PROJECT_ROOT,
    "Custom_MCP_Servers",
    "custom_weather_mcp_server.py"
)


# ============================================================
# MCP Client
# ============================================================

client = MultiServerMCPClient(
    {

        # ----------------------------------------------------
        # Remote MCP Server - Tavily
        # ----------------------------------------------------

        "tavily": {
            "transport": "streamable_http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
        },


        # ----------------------------------------------------
        # Local MCP Server - AviationStack
        # ----------------------------------------------------

        "aviationstack": {
            "transport": "stdio",

            # Use current project Python
            "command": AVIATION_COMMAND,

            # Start AviationStack MCP
            "args": [
                "-m",
                "aviationstack_mcp"
            ],

            "env": {
                "AVIATIONSTACK_API_KEY": AVIATIONSTACK_API_KEY
            }
        },


        # ----------------------------------------------------
        # Local Custom MCP Server - Weather
        # ----------------------------------------------------

        "weather": {
            "transport": "stdio",

            # Use current project Python
            "command": WEATHER_COMMAND,

            # Run weather MCP server
            "args": [
                WEATHER_SERVER
            ],

            "env": {
                "OPENWHETHER_API_KEY": OPENWHETHER_API_KEY
            }
        }
    }
)


# ============================================================
# Tools Discovery
# ============================================================

async def main():

    tools = await client.get_tools()

    print("\nAvailable tools:")

    for tool in tools:
        print(tool.name)


# ============================================================
# Tavily Tools
# ============================================================

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

    search_tool = next(
        (
            tool
            for tool in tools
            if tool.name == "tavily_search"
        ),
        None
    )

    aviation_tools = {
        tool.name: tool
        for tool in tools
        if tool.name != "tavily_search"
    }


async def tavily_mcp_search(query: str):

    await initialize_mcp()

    if search_tool is None:
        return "Tavily search tool unavailable"

    result = await search_tool.ainvoke(
        {
            "query": query
        }
    )

    return result


# ============================================================
# AviationStack MCP Tools
# ============================================================

async def aviation_mcp_call(
    tool_name: str,
    tool_args: dict
):

    tools = await client.get_tools()

    tool = next(
        (
            t
            for t in tools
            if t.name == tool_name
        ),
        None
    )

    if tool is None:
        return f"AviationStack tool '{tool_name}' unavailable"

    result = await tool.ainvoke(
        tool_args or {}
    )

    return result


async def get_airports():

    await initialize_mcp()

    tool = aviation_tools.get(
        "list_airports"
    )

    if not tool:
        return "Airport tool unavailable"

    result = await tool.ainvoke({})

    return result


async def get_airlines():

    await initialize_mcp()

    tool = aviation_tools.get(
        "list_airlines"
    )

    if not tool:
        return "Airline tool unavailable"

    result = await tool.ainvoke({})

    return result


# ============================================================
# Weather MCP Tools
# ============================================================

weather_tool = None
forecast_tool = None


async def initialize_weather_tools():

    global weather_tool
    global forecast_tool

    if (
        weather_tool is not None
        and forecast_tool is not None
    ):
        return

    tools = await client.get_tools()

    weather_tool = next(
        (
            t
            for t in tools
            if t.name == "get_current_weather"
        ),
        None
    )

    forecast_tool = next(
        (
            t
            for t in tools
            if t.name == "get_forecast"
        ),
        None
    )


async def weather_mcp_search(city: str):

    await initialize_weather_tools()

    if weather_tool is None:
        return "Current weather tool unavailable"

    return await weather_tool.ainvoke(
        {
            "city": city
        }
    )


async def forecast_mcp_search(city: str):

    await initialize_weather_tools()

    if forecast_tool is None:
        return "Forecast tool unavailable"

    return await forecast_tool.ainvoke(
        {
            "city": city
        }
    )


# ============================================================
# Destination Extractor
# ============================================================

def extract_destination(query: str):

    prompt = f"""
Extract only the destination city or country.

Query: {query}

Return only the destination name.
"""

    response = llm.invoke(prompt)

    return response.content.strip()


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":

    asyncio.run(main())

