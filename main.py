import os
from typing import TypedDict, Annotated
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
from langchain_openai import ChatOpenAI

# Tools configuration
# from tools.tavily_tools import tavily_search
from mcp_client import tavily_mcp_search 
from tools.flight_tools import search_flights

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# ============================================================
# LLM CONFIGURATION
# ============================================================

llm = ChatOpenAI(
    model="gpt-5-mini",
    api_key=os.getenv("OPENAI_API_KEY")
)


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL is not configured in .env")
    raise ValueError("DATABASE_URL is missing from .env")


# ============================================================
# DATABASE CONNECTION + LANGGRAPH CHECKPOINTER
# ============================================================

try:
    # Connect to PostgreSQL
    conn = psycopg.connect(
        DATABASE_URL,
        autocommit=True
    )

    # Test the connection
    with conn.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()

    print("✅ DATABASE CONNECTED SUCCESSFULLY")

    # Create LangGraph PostgreSQL checkpointer
    checkpointer = PostgresSaver(conn)

    # Create required LangGraph tables
    checkpointer.setup()

    print("✅ LANGGRAPH CHECKPOINTER INITIALIZED SUCCESSFULLY")

except Exception as e:
    print("❌ DATABASE CONNECTION FAILED")
    print(f"Error: {e}")

    raise


# ============================================================
# SHARED STATE
# ============================================================

class TravelState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    user_query: str
    flight_results: str
    hotel_results: str
    itinerary: str
    llm_calls: int


# ============================================================
# FLIGHT AGENT
# ============================================================

def flight_agent(state: TravelState):

    query = state["user_query"]

    flight_data = search_flights(query)

    return {
        "flight_results": flight_data,
        "messages": [
            AIMessage(content="Flight results fetched")
        ],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# ============================================================
# HOTEL AGENT
# ============================================================

def hotel_agent(state: TravelState):

    query = f" BestHotels in {state['user_query']}"

    # hotel_results = tavily_search(query)
    
    # Use the asynchronous tavily_mcp_search function
    hotel_results = asyncio.run(
        
        tavily_mcp_search(query)
        
        )
    
    

    return {
        "hotel_results": hotel_results,
        "messages": [
            AIMessage(content="Hotel information fetched")
        ],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# ============================================================
# ITINERARY AGENT
# ============================================================

def itinerary_agent(state: TravelState):

    prompt = f"""
Create a detailed travel itinerary.

User Query:
{state['user_query']}

Flight Results:
{state['flight_results']}

Hotel Results:
{state['hotel_results']}
"""

    response = llm.invoke(
        [
            SystemMessage(
                content="You are an expert travel planner."
            ),
            HumanMessage(
                content=prompt
            )
        ]
    )

    return {
        "itinerary": response.content,
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# ============================================================
# FINAL AGENT
# ============================================================

def final_agent(state: TravelState):

    final_prompt = f"""
Generate a final travel response for the user.

Flights:
{state['flight_results']}

Hotels:
{state['hotel_results']}

Itinerary:
{state['itinerary']}
"""

    response = llm.invoke(
        [
            HumanMessage(
                content=final_prompt
            )
        ]
    )

    return {
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# ============================================================
# BUILD LANGGRAPH
# ============================================================

graph = StateGraph(TravelState)

# Add agents
graph.add_node("flight_agent", flight_agent)
graph.add_node("hotel_agent", hotel_agent)
graph.add_node("itinerary_agent", itinerary_agent)
graph.add_node("final_agent", final_agent)


# ============================================================
# GRAPH FLOW
# ============================================================

graph.add_edge(
    START,
    "flight_agent"
)

graph.add_edge(
    "flight_agent",
    "hotel_agent"
)

graph.add_edge(
    "hotel_agent",
    "itinerary_agent"
)

graph.add_edge(
    "itinerary_agent",
    "final_agent"
)

graph.add_edge(
    "final_agent",
    END
)


# ============================================================
# COMPILE GRAPH
# ============================================================

app = graph.compile(
    checkpointer=checkpointer
)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    config = {
        "configurable": {
            "thread_id": "user_praful1"
        }
    }

    print("\n========================================")
    print("       AI TRAVEL PLANNER")
    print("========================================")

    user_input = input(
        "\nEnter your travel query: "
    )

    result = app.invoke(
        {
            "messages": [
                HumanMessage(
                    content=user_input
                )
            ],
            "user_query": user_input,
            "flight_results": "",
            "hotel_results": "",
            "itinerary": "",
            "llm_calls": 0
        },
        config=config
    )

    print("\n========================================")
    print("          FINAL RESPONSE")
    print("========================================\n")

    # Print only the final AI response
    print(result["messages"][-1].content)

    print("\n========================================")
    print(
        f"Total LLM calls: {result['llm_calls']}"
    )
    print("========================================")