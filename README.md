# Agentic AI Travel Planner

An interactive, multi-agent travel planner built with Streamlit, LangGraph, LangChain, and MCP. The application turns a natural-language travel request into a researched draft itinerary, shows the supporting flight, hotel, weather, and budget information, and asks the user to approve or provide feedback before producing the final plan.

## What it does

- Validates that a request is related to travel planning.
- Extracts trip constraints such as destination, origin, duration, budget, travel style, and preferences.
- Routes work to only the specialist agents needed for the request:
  - **Flight agent** - airports, airlines, routes, duration, fare guidance, and booking advice.
  - **Hotel agent** - hotel and area recommendations using Tavily search.
  - **Weather agent** - current conditions and a short forecast using OpenWeather.
  - **Budget agent** - cost categories, risks, feasibility, and money-saving suggestions.
  - **Itinerary agent** - a structured draft plan combining the available research.
- Pauses for human approval using LangGraph interrupts.
- Produces a polished final response using the approval decision and feedback.
- Optionally persists LangGraph state with PostgreSQL checkpoints.

## Architecture

```text
Streamlit UI
    |
    v
LangGraph application
    |
    +--> Supervisor + travel-request guardrail
    |
    +--> Flight agent ------> AviationStack MCP
    +--> Hotel agent  ------> Tavily MCP
    +--> Weather agent -----> Custom OpenWeather MCP server
    +--> Budget agent
    +--> Itinerary agent
    |
    +--> Human approval
    |
    +--> Final response agent
```

Agents share a `TravelState` object. The graph runs selected specialist agents in a consistent order, then creates an itinerary and pauses before the final response.

## Requirements

- Python 3.12
- An OpenAI API key
- A Tavily API key
- An AviationStack API key
- An OpenWeather API key
- PostgreSQL is optional and only required when persistent checkpoints are desired
- The AviationStack MCP server referenced by the project must be available locally

## Installation

Clone the repository and create a virtual environment:

```powershell
git clone https://github.com/PRAFULPAWAR8888/Agentic-AI-Travel-Planner.git
cd Agentic-AI-Travel-Planner
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies with either the project package manager or pip:

```powershell
pip install -e .
```

Or:

```powershell
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the repository root. The variable names below match the application code:

```dotenv
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-5-mini
TAVILY_API_KEY=your-tavily-api-key
AVIATIONSTACK_API_KEY=your-aviationstack-api-key
OPENWHETHER_API_KEY=your-openweather-api-key
DATABASE_URL=postgresql://user:password@localhost:5432/travel_planner
```

`DATABASE_URL` is optional. If it is omitted, the graph runs without a PostgreSQL checkpointer. The application currently uses the variable name `OPENWHETHER_API_KEY` (including the spelling in the source code) for the OpenWeather credential.

### AviationStack MCP server

The MCP client starts the AviationStack server over stdio. Update the `aviationstack` entry in [MCP_Configured_Tools/mcp_client.py](MCP_Configured_Tools/mcp_client.py) so its Python executable points to the local virtual environment containing the AviationStack MCP package. The checked-in path is machine-specific and should be changed for another machine.

The custom weather MCP server is located at [Custom_MCP_Servers/custom_weather_mcp_server.py](Custom_MCP_Servers/custom_weather_mcp_server.py) and is started by the MCP client over stdio.

## Running the app

From the repository root:

```powershell
streamlit run Fronted/frontend1.py
```

Open the URL printed by Streamlit, enter a travel request, and select **Create Draft Plan**. For example:

```text
Plan a 7-day Japan trip under Rs. 2 lakh. I prefer budget hotels and no overnight flights.
```

Review the generated research and draft itinerary, choose **Yes** or **No, revise it**, optionally enter feedback, and select **Submit Approval** to generate the final plan. Use **New Thread** in the sidebar to start a separate conversation state.

## Project structure

```text
Agent_States/
  state.py                    Shared LangGraph TravelState definition
Agents/
  agents.py                   Supervisor and specialist agent functions
configurations/
  config.py                   Environment loading and OpenAI model setup
Custom_MCP_Servers/
  custom_weather_mcp_server.py OpenWeather MCP tools
Graphs/
  graph.py                    LangGraph topology and checkpoint setup
MCP_Configured_Tools/
  mcp_client.py               Tavily, AviationStack, and weather MCP client
Fronted/
  frontend1.py                Streamlit user interface
```

## Data and API notes


- Hotel research uses Tavily's remote MCP endpoint.
- Weather data comes from OpenWeather's current-weather and forecast endpoints.
- API responses are used as planning inputs; fares, availability, weather, and hotel information should be verified with the provider before booking.
- Do not commit `.env` files or API keys. The repository ignores `.env` and virtual-environment files.

## Development

The project targets Python 3.12 and declares its dependencies in [pyproject.toml](pyproject.toml). The `uv.lock` file can be used when working with `uv`:

```powershell
uv sync
uv run streamlit run Fronted/frontend1.py
```

The application prints intermediate agent inputs and outputs to the terminal while it runs, which can help diagnose MCP or model integration issues.
