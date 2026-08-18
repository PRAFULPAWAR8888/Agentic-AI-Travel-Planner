import os
from typing import TypedDict, Annotated
import operator

import psycopg
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import (AnyMessage, SystemMessage, HumanMessage, AIMessage)
from langchain_groq import ChatGroq

# tools configuration
from tools.tavily_tools import tavily_search
from tools.flight_tools import search_flights

from dotenv import load_dotenv
load_dotenv()

#LLM Configuration
llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"))

#DATABASE Configuration
DATABASE_URL = os.getenv("DATABASE_URL")

#Create Shared Memory
class TravelState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    user_query: str
    flight_results: str
    hotel_results: str
    itinerary : str
    llm_calls: int
    

#Flight Agent

def flight_agent(state: TravelState):
    query = state["user_query"]
    flight_data = search_flights(query)
    return {
        "flight_results": flight_data,
        "messages": [
            AIMessage(content = f"Flight results fetched")],
        "llm_calls": state.get("llm_calls", 0) + 1
        
    }

#Hotel Agent

def hotel_agent(state: TravelState):
    query = f"Hotels in {state['user_query']}"
    hotel_results  = tavily_search(query)
    return {
        "hotel_results": hotel_results,
        "messages":[
            AIMessage(content = "Hotel information featched")
        ],
        "llm_calls": state.get("llm_calls", 0) + 1
    }

#Itinerary Agent

def itinerary_agent(state: TravelState):
    prompt = f"""
    Create a travel itinerary.
    User Query: 
    {state['user_query']}
    
    Flight Results:
    {state['flight_results']}
    
    Hotel Results:
    {state['hotel_results']}
    """ 
    response = llm.invoke([SystemMessage(content = "You are an expert travel planner"), HumanMessage(content = prompt)])
    
    return {
        "itinerary" : response.content,
        "messages": [response],
        "llm_calls": state.get("llm_calls",0) + 1
    }
    
# fianl Agent
  
def final_agent(state: TravelState):
    final_prompt = f"""
    Generate a final travel response.
    Flights:
    {state['flight_results']}
    
    Hotels:
    {state['hotel_results']}
    
    Itinerary:
    {state['itinerary']}
    """
    response = llm.invoke([HumanMessage(content = final_prompt)])
    
    return {
        "messages" : [response],
        "llm_calls": state.get("llm_calls", 0) + 1
    }
    
graph = StateGraph(TravelState)

graph.add_node("flight_agent", flight_agent)
graph.add_node("hotel_agent", hotel_agent)
graph.add_node("itinerary_agent", itinerary_agent)
graph.add_node("final_agent", final_agent)

graph.add_edge(START, "flight_agent")
graph.add_edge("flight_agent", "hotel_agent")
graph.add_edge("hotel_agent", "itinerary_agent")
graph.add_edge("itinerary_agent", "final_agent")
graph.add_edge("final_agent", END)

_conn = psycopg.connect(
    DATABASE_URL,
    autocommit=True
)
checkpointer = PostgresSaver(_conn)
checkpointer.setup()

app = graph.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    config = {
        "configurable" : {
            "thread_id" : "user_praful"
        }
    }
    
    user_input = input("Enter your travel query: ")
    result = app.invoke( { "messages" : [HumanMessage(content = user_input)], "user_query" : user_input, "flight_results" : "", "hotel_results" : "", "itinerary" : "", "llm_calls": 0}, config = config)

print("\nFINAL RESPONSE:\n")

for msg in result["messages"]:
    print(msg.content)
       



