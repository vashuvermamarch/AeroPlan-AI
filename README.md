# AeroPlan AI ✈️

AeroPlan AI is a premium, state-of-the-art **Multi-Agent Travel Planner Orchestration Engine**. It uses a graph-based multi-agent workflow to dynamically fetch live flight options, search for ideal hotels, design a custom travel itinerary, and generate a final, polished response for user travel requests.

The application features a stunning, interactive dark-themed web interface built using Streamlit, styled with custom CSS glassmorphism and glowing neon accents. It displays the execution of agents and intermediate data in real-time as they stream.

---

## 🚀 Key Features

* **Multi-Agent Orchestration**: Built on LangGraph to coordinate four specialized agents working in a shared-state pipeline.
* **Real-Time Execution Tracker**: Interactive UI with a live agent timeline showing status updates (Pending ⚪, Active ⚡, Done ✓).
* **Live Flight Retrieval**: Queries the AviationStack API to retrieve current real-world flight status/schedules, featuring smart heuristics to parse airport IATA codes (e.g. JFK, LAX) from free-form user text.
* **Dynamic Hotel Discovery**: Integrates the Tavily search engine to search for top accommodation recommendations for the destination.
* **Custom Itinerary Design**: Uses the Groq Llama-3-70B model to design a day-by-day travel plan based on real flight and hotel results.
* **Persistent Shared State**: Uses Postgres (Neon DB) and LangGraph checkpointing to store conversation state and message history, protected against timeout issues through pooled connection handling.
* **Purple-Free Premium Theme**: Custom CSS with radial background gradients, neon cyan/blue highlights, and glassmorphic card backdrops.

---

## 🛠️ Technology Stack

* **Orchestration**: LangGraph
* **LLM Engine**: LangChain & ChatGroq (Llama 3.3 70B)
* **Web Frontend**: Streamlit (with Custom CSS/HTML overrides)
* **Database Checkpointing**: Neon Serverless Postgres DB & `psycopg` (v3)
* **APIs & Search Tools**:
  * AviationStack API (Real-time flight data)
  * Tavily Search API (Hotel & local recommendation search)
  * Groq Cloud API (High-performance inference)

---

## 🤖 The Multi-Agent Workflow

```mermaid
graph TD
    START([Start]) --> FA[Flight Agent]
    FA --> HA[Hotel Agent]
    HA --> IA[Itinerary Agent]
    IA --> FI[Final Agent]
    FI --> END([End])

    subgraph State Graph Execution
        FA -- Fetches Flights --> State
        HA -- Fetches Hotels --> State
        IA -- Generates Days Itinerary --> State
        FI -- Synthesizes Final Presentation --> State
    end
    
    State[(Neon Postgres Checkpointer)] <--> State Graph Execution
```

1. **Flight Search Agent (`flight_agent`)**: Extracts airport codes from user query text and queries AviationStack for real-world flights. Returns flight logs to the shared state.
2. **Hotel Agent (`hotel_agent`)**: Uses Tavily Search to search for recommended hotels at the target destination, adding formatted results to the shared state.
3. **Itinerary Agent (`itinerary_agent`)**: Invokes ChatGroq with the combined user request, flight data, and hotel options to construct a highly personalized day-by-day sightseeing plan.
4. **Final Agent (`final_agent`)**: Synthesizes the flight list, hotel recommendations, and itinerary draft into a polished, customer-facing response.

---

## ⚙️ Environment Configuration

Create a `.env` file in the root of the project with the following variables:

```env
GROQ_API_KEY = your_groq_api_key
AVIATIONSTACK_API_KEY = your_aviationstack_api_key
TAVILY_API_KEY = your_tavily_api_key
NEON_DB_API_KEY = postgresql://...
```

---

## 🏁 Setup & Installation

### 1. Set Up Virtual Environment & Dependencies
Clone the repository, open a terminal in the root folder, and run:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows CMD:
venv\Scripts\activate
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Mac/Linux:
source venv/bin/activate

# Install requirements
pip install -r requirement.txt
```

### 2. Run the Application

#### Streamlit Web App Interface (Recommended)
Launch the premium interactive frontend:
```bash
streamlit run frontend.py
```

#### Command Line Interface (CLI)
Run the script interactively in the terminal:
```bash
python main.py
```
