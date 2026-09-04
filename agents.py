import os
import json
from typing import TypedDict, Annotated, Any
import operator
import asyncio
import psycopg
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import (
    AnyMessage,
    SystemMessage,
    HumanMessage,
    AIMessage
)

#module used to make human in the loop
from  langgraph.types import interrupt

#config module to make project more production grade and managble
from configurations.config import  get_llm

# for deleclare llm object
from langchain_openai import ChatOpenAI

# Tools configuration
# from tools.tavily_tools import tavily_search
from MCP_Configured_Tools.mcp_client import (
    get_airports,
    get_airlines,
    aviation_mcp_call,
    tavily_mcp_search,extract_destination,forecast_mcp_search,weather_mcp_search
)
#from tools.flight_tools import search_flights

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

#use stage as agent memory:
from Agent_States.state import TravelState


# LLM object declered
llm  = get_llm()


# Helper function to send system instructions and a user prompt to the LLM
# and return the generated text response.
def _llm_text(system:str, prompt:str) ->str:
    response = llm.invoke(
        
        [
            SystemMessage(content=system),
            HumanMessage(content = prompt)
        ]
    )
    return response.content

# Helper function to extract and parse a JSON object from the LLM response text.
def _json_from_llm(text:str)-> dict:
    print("\n=====RAW LLM RESPONSE=====")
    print(text)
    print("===========================")
    
    start = text.index("{")
    end = text.index("}") + 1
    
    json_text = text[start:end]
    
    print("\n====== Extracted json =======")
    print(json_text)
    print("=============================\n")
    
    return json.loads(json_text)

# supervisor agent

def supervisor_agent(state : TravelState):
    query = state["user_query"]
    prompt = f"""
    You are the supervisor of a real_world multi_agent travel planning system.
    
    Decide which specialist agent are neeeded for this user request.
    
    Available agents:
    - flight_agent : use when flights, airports, airlines, routes or airfare guidance are needed
    - hotel_agent : use when hotels, stays, neighborhoods, or accommodation are needed
    - weather_agent : use when weather, climate, season, packing, or forecast is useful
    - budget_agent : use when budget, affordability, cost, or price constrainsts are mentioned
    - itinerary_agent : almost always needed to produce the travel plan
    
    Return only jSON with this schema:
    {{
        "selected_agents": ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent" ],
        "trip_constraints" : {{
            "destination" : "",
            "origin": "",
            "duration" : "",
            "budget" : "",
            "travel_style" : "",
            "special_preferences": []
            
        }},
        "reasoning" : ""
    }}
    
    User request:
    {query}
    """
    
    raw = _llm_text("You route work to specialist agents. Return strict JSON only", prompt,)
    
    print("\n ======RAW LLM RESPONSE=====")
    print(raw)
    print("===============================\n")

    parsed = _json_from_llm(raw)
    
    print("\n===== PARSED JSON ====")
    print(json.dumps(parsed, indent=2))
    print("===========================")
    
    print(type(raw))
    print(type(parsed))
    
    selected = parsed["selected_agents"]
    
    return {
        
        "selected_agents" : selected,
        "trip_constraints" : parsed["trip_constraints"],
        "superviosr_reasoning" : parsed["resoning"],
        "messages" : [AIMessage(content="Supervisor created the agent plan.")],
        "llm_calls" : state.get("llm_calls", 0) + 1
        
    }
    
def flight_agent(state : TravelState):
    query  =  state["user_query"]
    constraints = state["trip_constraints"]
    destination = constraints["destination"]
    
    print("\n ====== FLIGHT AGENT INPUT =====")
    print("Query:", query)
    print("Constraints:", constraints)
    print("===================================")
    
    
    airports = asyncio.run(get_airports(destination, limit = 10))
    airlines = asyncio.run(get_airlines("", limit = 10))
    
    print("\n =============== AIRPORT MCP DATA ==================")
    print(airports)
    print("=======================================================\n")
    
    print("\n ================ AIRLINE MCP DATA =================")
    print(airlines)
    print("=========================================================\n")
    
    prompt  = f"""
    
    create flight guidance for  for this trip
    
    User request:
    {query}
    
    Trip constraints:
    {constraints}
    
    Airport MCP data:
    {str(airports)[:3000]}
    
    Airline MCP data:
    {str(airlines)[:3000]}
    
    Include likely departure/arrival airports, relevant airlines,
    estimated durtion, fare range, peak season warnings, and booking advice.
    
    """
    result = _llm_text("You are a flight planning expert.", prompt)
    
    print("\n ====== FLIGHT AGENT LLM RESPONSE =====")
    print(result)
    print("==========================================\n")   
    
    return {
        "flight_results" : result,
        "messages" : [AIMessage(content="Flight agent completed its task.")],
        "llm_calls" : state.get("llm_calls", 0) + 1,
        
    }
    

def hotel_agent(state : TravelState):
    query  = f" Best hotels and areas to stay for: {state['user_query']}"
    print("\n ====== HOTEL AGENT INPUT ===== ")
    print("Query:", query)
    print("===================================")

    result =  asyncio.run(tavily_mcp_search(query))
    
    return {
        "hotel_results" : str(result),
        "messages" : [AIMessage(content="Hotel agent completed its task.")],
        "llm_calls" : state.get("llm_calls",0) + 1
    }
    
def weather_agent(state : TravelState):
    constraints = state["trip_constraints"]
    city = constraints["destination"]
    
    print("\n ====== WEATHER AGENT INPUT ===== ")
    print("City:", city)
    print("===================================")
    
    weather_data = asyncio.run(weather_mcp_search(city))
    forecast_data = asyncio.run(forecast_mcp_search(city))
    
    print("\n ====== Current Weather===== ")
    print(weather_data)
    print("===================================")
    
    print("\n ====== Forecast Weather===== ")
    print(forecast_data)
    print("===================================")
    
    result = f"""
    Current Weather:
    {weather_data}

    Forecast Weather:
    {forecast_data}
    """
    return {
        "weather_results": result,
        "messages": [AIMessage(content="Weather agent completed its task.")]
    }

def budget_agent(state : TravelState):