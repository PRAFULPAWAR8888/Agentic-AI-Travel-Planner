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
        "supervisor_reasoning" : parsed["reasoning"],
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
    
    print("\n ====== BUDGET AGENT INPUT ===== ")
    print("Trip Constraints:")
    print(state.get("trip_constraints"))
    print("\n Flight Results:")
    print(state.get("flight_results"))
    print("\n Hotel Results:")
    print(state.get("hotel_results"))
    print("\n Weather Results:")
    print(state.get("weather_results"))
    print("===================================")
    
    prompt  = f""" Analyze the following trip information and provide budget 
    
    user query:
    {state['user_query']}
    
    trip constraints:
    {state.get('trip_constraints')}
    
    flight results:
    {state.get('flight_results')}
    
    hotel results:
    {state.get('hotel_results')}
    
    weather results:
    {state.get('weather_results')}
    
    Return a concise budget assessment with:
    1. Estimated cost categories
    2. risk areas
    3. money-saving suggestions
    4. whether the plan seems feasible
    
    """
    
    result = _llm_text("You are a travel budget expert.", prompt)
    
    return {
        "budget_results" : result,
        "messages" : [AIMessage(content = "Budget agent completed its task.")],
        "llm_calls" : state.get("llm_calls", 0) + 1
    }
    
def itinerary_agent(state : TravelState):
    print("\n ====== ITINERARY AGENT INPUT =====")
    print("Trip constraints:")
    print(state.get("trip_constraints"))
    print("\n Flight Results:")
    print(state.get("flight_results"))
    print("\n Hotel Results:")
    print(state.get("hotel_results"))
    print("\n Weather Results:")
    print(state.get("weather_results"))
    print("\n Budget Results:")
    print(state.get("budget_results"))
    print("===================================")
    
    prompt = f"""
    Create a detailed travel itinerary based on the provided  information:
    
    User query:
    {state['user_query']}
    
    Trip constraints:
    {state.get('trip_constraints')}
    
    Flight results:
    {state.get('flight_results')}
    
    Hotel results:
    {state.get('hotel_results')}
    
    Weather results:
    {state.get('weather_results')}
    
    Budget results:
    {state.get('budget_results')}
    
    Make the output clear, structured, and easy to follow. Include day-by-day activities, travel tips, and any relevant notes for the traveler. and ready for human review
    
    """
    
    result = _llm_text("You are a travel itinerary expert.", prompt)
    
    print("\n ====== ITINERARY AGENT LLM RESPONSE =====")
    print(result)
    print("==========================================\n")
    
    approval_request = f""" Please review this draft travel plan. 
    {result} 
    Replay with approval or feedback for improvement.
    """
    
    
    
    return {
        "itinerary" : result,
        "approval_request" : approval_request,
        "messages" : [AIMessage(content = "Draft itinerary created and sent for human review.")],
        "llm_calls" : state.get("llm_calls", 0) + 1
        
    }
    
def human_approval_agent(state : TravelState):
    feedback = interrupt(
        {
            "question" : "Do you approve this itinerary?",
            "draft_itinerary" : state.get("itinerary", ""),
            "approval_request" : state.get("approval_request", ""),
            "expected_response" : {
                "approved" : True,
                "feedback" : "Optional feedback for improvement"
            },
        }
    )
    
    approved = feedback["approved"]
    human_feedback = feedback["feedback"]
    
    return {
        "approved" : approved,
        "human_feedback" : human_feedback,
        "messages" : [AIMessage(content = "Human approval received.")],
        "llm_calls" : state.get("llm_calls", 0) + 1
    }

def final_response_agent(state : TravelState):
    
    
    print("\n ====== FINAL RESPONSE AGENT INPUT =====")
    print("Approved:", state.get("approved"))
    print("Human Feedback:", state.get("human_feedback"))
    print("===================================")
    
    if state.get("approved"):
        prompt = f"""
        The user has approved this draft travel itinerary.
        produce a final, polished version of the itinerary that incorporates any human feedback and is ready for the user to follow.
        
        
       Draft itinerary:
       {state.get("itinerary")}
       
       Budget notes:
        {state.get("budget_results")}
        
        
        """
        
    else:
        prompt = f"""
        The human did not approve the draft.
        
        original draft itinerary:
        {state.get("itinerary")}
        
        Human feedback:
        {state.get("human_feedback")}
        
        Budget notes:
        {state.get("budget_results")}
       """
       
        result = _llm_text("You are a travel planning expert.", prompt)
        
        print("\n ====== FINAL RESPONSE AGENT LLM RESPONSE =====") 
        print(result)
        print("==========================================\n")
        
        return {
            "final_response" : result,
            "messages" : [AIMessage(content = result)],
            "llm_calls" : state.get("llm_calls", 0) + 1
        }
        