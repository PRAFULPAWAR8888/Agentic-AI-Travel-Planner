# Agentic AI Travel Planner

An interactive, multi-agent travel planning application that turns a natural-language request into a researched, budget-aware itinerary. The application uses LangGraph to coordinate specialist agents, Model Context Protocol (MCP) tools to retrieve live travel data, and Streamlit to provide a simple human-in-the-loop experience.

> **Important:** This application provides planning guidance. Flight prices, hotel availability, weather conditions, and travel requirements can change. Always verify details with the official provider before booking.

## Highlights

- Natural-language trip planning from a single user request.
- An LLM-powered supervisor that validates the request, extracts trip constraints, and selects only the agents needed for the request.
- Specialist agents for flights, hotels, weather, budget analysis, and itinerary generation.
- MCP integrations for AviationStack, Tavily, and a custom OpenWeather server.
- Human approval before the final plan is generated.
- Revision support: provide feedback on a draft and let the final response agent incorporate it.
- Thread-based conversations in the Streamlit interface.
- Optional PostgreSQL-backed LangGraph checkpoints for persistent workflow state.
- Local development and Docker Compose deployment options.

## How the agentic workflow works

```text
User request
     |
     v
Travel-request guardrail
     |
     v
Supervisor agent
  - extracts destination, origin, duration, budget, style, preferences
  - selects the required specialist agents
     |
     +--> Flight agent -----> AviationStack MCP
     +--> Hotel agent ------> Tavily MCP search
     +--> Weather agent ----> Custom OpenWeather MCP server
     +--> Budget agent -----> LLM analysis of costs and feasibility
     +--> Itinerary agent --> draft plan using all available research
                              |
                              v
                       Human approval / feedback
                              |
                              v
                    Final response agent
```

All agents read and update a shared `TravelState` object. LangGraph controls the order of execution and routes around agents that the supervisor did not select. The graph pauses at the approval node using a LangGraph interrupt, so the user can approve the draft or request changes before the final answer is produced.

## Agents and responsibilities

| Agent | Responsibility |
| --- | --- |
| **Input guardrail** | Checks that the request is related to travel planning and rejects unrelated requests safely. |
| **Supervisor** | Converts the request into structured trip constraints, explains the routing decision, and selects the necessary agents. |
| **Flight agent** | Uses AviationStack airport and airline data to provide airport choices, airline guidance, estimated duration, fare guidance, and booking considerations. |
| **Hotel agent** | Uses Tavily MCP search to research accommodation options and suitable areas to stay. |
| **Weather agent** | Uses the custom OpenWeather MCP server for current conditions and a short forecast. |
| **Budget agent** | Reviews the available research, estimates cost categories, identifies risks, evaluates feasibility, and suggests savings. |
| **Itinerary agent** | Combines the specialist outputs into a structured draft itinerary for review. |
| **Human approval** | Pauses execution and collects approval or revision feedback from the user. |
| **Final response agent** | Produces a polished final plan based on the draft, budget notes, approval, and user feedback. |

## Technology stack

### Application and user interface

- **Python 3.12+** - primary implementation language.
- **Streamlit** - interactive web interface, session controls, draft review, and approval form.
- **python-dotenv** - loads local environment variables from `.env`.
- **Requests** - HTTP calls in the custom weather MCP server.

### Agent orchestration and LLM

- **LangGraph** - stateful graph orchestration, conditional routing, interrupts, and checkpoint integration.
- **LangChain** - message types and model/tool integration.
- **LangChain OpenAI** - OpenAI chat model integration. The default model is `gpt-5-mini`.
- **Pydantic-compatible typed state** - `TravelState` defines the shared data exchanged by graph nodes.

### Model Context Protocol and data services

- **MCP** - standard interface between agents and external tools.
- **langchain-mcp-adapters** - discovers and invokes MCP tools from the application.
- **AviationStack MCP** - local workspace MCP server for aviation reference and flight data.
- **Tavily MCP** - remote MCP search for hotel and destination research.
- **Custom OpenWeather MCP server** - local MCP server exposing current weather and forecast tools.

### Persistence and deployment

- **PostgreSQL** - optional LangGraph checkpoint store using `langgraph-checkpoint-postgres`.
- **psycopg** - PostgreSQL connectivity.
- **uv** - recommended dependency and workspace manager.
- **Docker and Docker Compose** - containerized application and PostgreSQL services.

## Requirements

- Python 3.12 or newer for local development.
- An OpenAI API key.
- A Tavily API key.
- An AviationStack API key.
- An OpenWeather API key.
- `uv` (recommended) or `pip`.
- PostgreSQL only if persistent checkpoints are required. The application can run without `DATABASE_URL`.
- Docker Desktop if you want to use Docker Compose.

## Installation

### Option A: Install with uv (recommended)

From the repository root:

```powershell
git clone https://github.com/PRAFULPAWAR8888/Agentic-AI-Travel-Planner.git
cd Agentic-AI-Travel-Planner

python -m venv .venv
.\.venv\Scripts\Activate.ps1

uv sync
```

`uv sync` installs the root project and the local `aviationstack-mcp` workspace package declared in `pyproject.toml`.

If PowerShell blocks script activation, either allow scripts for the current user or run commands through the virtual environment directly:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Option B: Install with pip

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .\aviationstack-mcp
```

## Configuration

Create a file named `.env` in the repository root. Never commit this file or share the keys.

```dotenv
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-5-mini
TAVILY_API_KEY=your-tavily-api-key
AVIATIONSTACK_API_KEY=your-aviationstack-api-key
OPENWHETHER_API_KEY=your-openweather-api-key
```

The source code currently expects `OPENWHETHER_API_KEY` (with the spelling shown above) for OpenWeather. Keep that exact name unless you also update the application code.

### Optional PostgreSQL persistence

Without `DATABASE_URL`, the graph runs without a PostgreSQL checkpointer. For a local PostgreSQL instance, add a connection string such as:

```dotenv
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/langgraph_memory
```

The database must exist before the application starts. The graph calls `PostgresSaver.setup()` to create the required checkpoint tables.

## Run locally

Start the Streamlit application from the repository root:

```powershell
streamlit run Fronted/frontend1.py
```

Or, when using uv:

```powershell
uv run streamlit run Fronted/frontend1.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`. Enter a request such as:

```text
Plan a 7-day Japan trip under Rs. 2 lakh. I prefer budget hotels and no overnight flights.
```

Choose **Create Draft Plan**, review the research and draft itinerary, then select **Yes** or **No, revise it**. If revision is selected, enter feedback before choosing **Submit Approval**. Use **New Thread** in the sidebar to start a separate workflow state.

## Run with Docker Compose

Docker Compose starts the Streamlit application and a PostgreSQL 16 service:

```powershell
docker compose up --build
```

Before starting, create `.env` with the API keys and add the container database URL:

```dotenv
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/langgraph_memory
```

Then open `http://localhost:8501`. Stop the services with:

```powershell
docker compose down
```

PostgreSQL data is stored in the named `postgres_data` volume. To remove that local database data as well, run `docker compose down -v`.

## MCP integrations

The MCP client is configured in [MCP_Configured_Tools/mcp_client.py](MCP_Configured_Tools/mcp_client.py).

- **Tavily** is connected through its remote streamable HTTP MCP endpoint.
- **AviationStack** is started locally over stdio with `python -m aviationstack_mcp`.
- **OpenWeather** is provided by [Custom_MCP_Servers/custom_weather_mcp_server.py](Custom_MCP_Servers/custom_weather_mcp_server.py) and started locally over stdio.

The application uses the active Python interpreter (`sys.executable`) to launch the local MCP servers, so the AviationStack package must be installed in the same environment used to run Streamlit.

## Project structure

```text
Agent_States/
  state.py                         Shared TravelState definition
Agents/
  agents.py                        Guardrail, supervisor, specialist, approval, and final agents
configurations/
  config.py                        Environment loading and OpenAI model configuration
Custom_MCP_Servers/
  custom_weather_mcp_server.py     Current weather and forecast MCP tools
Graphs/
  graph.py                         LangGraph topology and optional PostgreSQL checkpointer
MCP_Configured_Tools/
  mcp_client.py                    Tavily, AviationStack, and weather MCP client setup
Fronted/
  frontend1.py                     Streamlit user interface
aviationstack-mcp/
  src/aviationstack_mcp/           Local AviationStack MCP workspace package
pyproject.toml                     Project metadata and dependencies
requirements.txt                   Pinned pip dependencies
Dockerfile                         Container image definition
docker-compose.yml                 Application and PostgreSQL services
```

## Development notes

- The graph executes selected specialist agents in a deterministic order: flight, hotel, weather, budget, then itinerary.
- Tool outputs and intermediate agent results are printed to the terminal to help diagnose model or MCP integration issues.
- API data is used as research input and is not a booking or price guarantee.
- Keep API credentials in environment variables or Streamlit secrets, never in source control.
- The repository includes a `uv.lock` file for reproducible uv-based installs.

## Troubleshooting

### MCP tools are unavailable

Confirm that all API keys are present, the application is running from the repository root, and the AviationStack MCP package is installed in the active environment:

```powershell
uv run python -m aviationstack_mcp
```

The command should start the MCP server. Stop it with `Ctrl+C`.

### PostgreSQL connection errors

If you do not need persistent state, remove `DATABASE_URL` from `.env`. If persistence is required, verify that PostgreSQL is running and that the host, port, database, username, and password in the connection string are correct. With Docker Compose, the hostname is `postgres`, not `localhost`.

### OpenWeather authentication errors

Verify that the variable is named `OPENWHETHER_API_KEY`, matching the current source code, and that the key is active with OpenWeather.

## License

This project is distributed under the license included in the repository. The bundled [aviationstack-mcp](aviationstack-mcp) package includes its own license and attribution details.
