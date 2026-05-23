<div align="center">

# ✈️ AeroPlan AI

### Intelligent Multi-Agent Travel Booking System

*Powered by LangGraph · Groq Llama 3.3 · AviationStack · Tavily · Streamlit*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?style=flat-square&logo=streamlit)](https://streamlit.io)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-blueviolet?style=flat-square)](https://langchain-ai.github.io/langgraph/)
[![Groq](https://img.shields.io/badge/Groq-Llama%203.3%2070B-orange?style=flat-square)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

## 📋 Table of Contents

1. [Overview](#-overview)
2. [Quick Start — Get Running in 5 Minutes](#-quick-start--get-running-in-5-minutes)
3. [Environment Setup](#-environment-setup)
4. [Project Structure](#-project-structure)
5. [Agent Architecture Diagram](#-agent-architecture-diagram)
6. [Agent Deep Dive](#-agent-deep-dive)
7. [Data Flow](#-data-flow)
8. [Tech Stack](#-tech-stack)
9. [API Keys Reference](#-api-keys-reference)
10. [Key Design Decisions](#-key-design-decisions)

---

## 🌍 Overview

**AeroPlan AI** is a production-grade, multi-agent AI travel orchestration platform. Instead of a single LLM trying to do everything, it uses a **LangGraph state machine** to coordinate four specialist AI agents in sequence — each owning one domain of the travel planning problem:

- 🛫 **Flight Agent** — finds real live flights via AviationStack API
- 🏨 **Hotel Agent** — searches hotel options using Tavily AI search
- 🗺️ **Itinerary Agent** — generates a day-by-day travel plan via Llama 3.3 70B
- 📋 **Final Agent** — synthesises everything into a polished trip summary

The result is displayed in a stunning **glassmorphic Streamlit UI** with PDF export and clipboard copy built in. All conversation threads are persisted to **PostgreSQL (Neon)** via LangGraph checkpointing.

---

## 🚀 Quick Start — Get Running in 5 Minutes

### Prerequisites

- Python 3.10 or higher
- Git
- A terminal (PowerShell on Windows)
- API keys (see [API Keys Reference](#-api-keys-reference))

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/vashuvermamarch/AreoPlan-AI.git
cd AreoPlan-AI
```

---

### Step 2 — Create & Activate a Virtual Environment

```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

---

### Step 3 — Install Dependencies

```bash
pip install -r requirement.txt
```

---

### Step 4 — Configure Environment Variables

Create a `.env` file in the project root (copy the template below):

```bash
# .env — never commit this file!

GROQ_API_KEY=your_groq_api_key_here
AVIATIONSTACK_API_KEY=your_aviationstack_key_here
TAVILY_API_KEY=your_tavily_key_here
NEON_DB_API_KEY=postgresql://user:password@host/dbname?sslmode=require
```

> See [API Keys Reference](#-api-keys-reference) for where to get each key.

---

### Step 5 — Run the App

#### Option A — One-click launcher (Windows)

```bash
.\run.bat
```

#### Option B — Manual start

```bash
streamlit run frontend.py
```

The app will open at **http://localhost:8501** automatically.

---

### Step 6 — Use the App

1. Type your travel request in the prompt bar at the bottom  
   *(e.g. "Plan a 7-day trip from Delhi to Muscat in June 2026")*
2. Hit **Enter** or click **Send**
3. Watch the four agents execute in sequence, streaming results live
4. Use **📋 Copy Plan** to copy the full plan to your clipboard
5. Use **⬇ PDF export** to download a formatted PDF of the plan
6. All past trips are saved — revisit them from the **Journeys** tab in the sidebar

---

### Step 7 — Run CLI Mode (optional)

If you want to run the agent pipeline directly without the UI:

```bash
python main.py
```

You'll be prompted to enter a travel request in the terminal. The full agent pipeline runs and prints the final synthesised response.

---

## 🔐 Environment Setup

| Variable | Description | Required |
|---|---|---|
| `GROQ_API_KEY` | Groq Cloud API key for Llama 3.3 70B inference | ✅ Yes |
| `AVIATIONSTACK_API_KEY` | AviationStack key for live flight data | ✅ Yes |
| `TAVILY_API_KEY` | Tavily AI web search key for hotel/destination research | ✅ Yes |
| `NEON_DB_API_KEY` | PostgreSQL connection string (Neon serverless) for LangGraph checkpointing | ✅ Yes |

---

## 📁 Project Structure

```
AeroPlan-AI/
│
├── frontend.py              # Streamlit UI — glassmorphic dashboard, all rendering logic
├── main.py                  # LangGraph agent graph definition + CLI entry point
│
├── tools/
│   ├── flight_tool.py       # Flight Agent tool — AviationStack API + LLM IATA extraction
│   └── tavily_tool.py       # Hotel Agent tool — Tavily AI web search
│
├── .streamlit/
│   └── config.toml          # Streamlit theme config (dark glassmorphic palette)
│
├── .env                     # 🔒 Secret keys (git-ignored, never commit)
├── .gitignore               # Git exclusion rules
├── requirement.txt          # Python dependencies
├── run.bat                  # Windows one-click launcher script
└── README.md                # This file
```

---

## 🧠 Agent Architecture Diagram

```
                         USER QUERY
                             │
                             ▼
                    ┌─────────────────┐
                    │   Streamlit UI   │
                    │  (frontend.py)   │
                    └────────┬────────┘
                             │  invoke(state)
                             ▼
              ╔══════════════════════════════╗
              ║     LangGraph StateGraph      ║
              ║      (TravelState)            ║
              ╠══════════════════════════════╣
              ║                              ║
              ║  ┌────────────────────────┐  ║
              ║  │       START            │  ║
              ║  └───────────┬────────────┘  ║
              ║              │               ║
              ║              ▼               ║
              ║  ┌────────────────────────┐  ║
              ║  │    ✈️  Flight Agent     │  ║
              ║  │  search_flights(query) │  ║
              ║  │  → AviationStack API   │  ║
              ║  │  → LLM IATA Extractor  │  ║
              ║  │  → Self-Heal Fallback  │  ║
              ║  └───────────┬────────────┘  ║
              ║              │ flight_results ║
              ║              ▼               ║
              ║  ┌────────────────────────┐  ║
              ║  │    🏨  Hotel Agent      │  ║
              ║  │  tavily_search(query)  │  ║
              ║  │  → Tavily AI Search    │  ║
              ║  │  → Top 5 Web Results   │  ║
              ║  └───────────┬────────────┘  ║
              ║              │ hotel_results  ║
              ║              ▼               ║
              ║  ┌────────────────────────┐  ║
              ║  │  🗺️  Itinerary Agent   │  ║
              ║  │  Llama 3.3 70B (Groq)  │  ║
              ║  │  + flights + hotels    │  ║
              ║  │  → Day-by-Day Plan     │  ║
              ║  └───────────┬────────────┘  ║
              ║              │ itinerary      ║
              ║              ▼               ║
              ║  ┌────────────────────────┐  ║
              ║  │  📋  Final Agent        │  ║
              ║  │  Llama 3.3 70B (Groq)  │  ║
              ║  │  Synthesises all data  │  ║
              ║  │  → Final Trip Summary  │  ║
              ║  └───────────┬────────────┘  ║
              ║              │               ║
              ║  ┌───────────▼────────────┐  ║
              ║  │         END            │  ║
              ║  └────────────────────────┘  ║
              ║                              ║
              ╠══════════════════════════════╣
              ║  PostgreSQL Checkpointer      ║
              ║  (Neon Serverless DB)         ║
              ║  Persists every state step    ║
              ╚══════════════════════════════╝
                             │
                             ▼
                    ┌─────────────────┐
                    │  Streamlit UI   │
                    │  Renders each   │
                    │  result as it   │
                    │  arrives        │
                    └─────────────────┘
```

---

## 🔬 Agent Deep Dive

### ✈️ 1. Flight Agent — `flight_agent(state)`

**File:** `tools/flight_tool.py` · **Entry:** `search_flights(query)`

The Flight Agent is the most technically sophisticated component. It uses a **three-layer extraction + self-healing search strategy**:

#### Layer 1 — LLM IATA Extraction
Sends the raw user query to **Llama 3.3 70B** on Groq with a structured prompt asking it to identify the departure city and destination city, then map them to their 3-letter IATA airport codes (e.g. `DEL` for Delhi, `MCT` for Muscat). Returns a clean JSON `{"dep_iata": "...", "arr_iata": "..."}`.

#### Layer 2 — Regex Fallback
If the LLM call fails or returns empty codes, a regex pattern `\b[A-Z]{3}\b` scans the user query for any 3-letter uppercase sequences, filtering out English stop-words (`FOR`, `AND`, `THE`, etc.) to reduce false positives.

#### Layer 3 — Self-Healing API Search
Once IATA codes are resolved, it queries the **AviationStack REST API** in progressive fallback order:
1. **Both** departure + arrival IATA (most specific)
2. **Arrival only** — if step 1 returns nothing
3. **Departure only** — if step 2 returns nothing
4. **Graceful failure** — returns a clear "no flights found" message if all strategies fail

Returns up to 5 formatted flight strings with airline, route, and status.

---

### 🏨 2. Hotel Agent — `hotel_agent(state)`

**File:** `tools/tavily_tool.py` · **Entry:** `tavily_search(query)`

Constructs an enriched query `"Best hotels for {user_query}"` and sends it to the **Tavily AI Search API** — an AI-native web search engine optimised for RAG and agent pipelines.

- Fetches the top 5 web results
- Extracts title, URL, and content snippet
- Truncates snippets to 300 characters with a `[READ MORE]` marker to avoid token bloat in downstream agents
- Returns a clean, numbered markdown string

---

### 🗺️ 3. Itinerary Agent — `itinerary_agent(state)`

**File:** `main.py` · **Model:** Llama 3.3 70B via Groq

Receives the full `TravelState` containing both the flight results and hotel results, then calls **Llama 3.3 70B** with the system role `"You are an expert travel planner"` and a rich prompt that includes the user query, all flights found, and all hotel options.

Generates a structured **day-by-day itinerary** grounded in the real flight and hotel data gathered by the previous two agents — not hallucinated recommendations.

---

### 📋 4. Final Agent — `final_agent(state)`

**File:** `main.py` · **Model:** Llama 3.3 70B via Groq

Receives flights, hotels, and the itinerary, then synthesises a polished final travel summary — the "travel proposal" that the user sees as the main output. Acts as the editorial layer that makes the output coherent and readable.

---

## 🔄 Data Flow

```
User Query (string)
       │
       ├─► [LangGraph State: TravelState]
       │        ├── messages:        list[AnyMessage]   # full conversation history
       │        ├── user_query:      str                # original user input
       │        ├── flight_results:  str                # filled by Flight Agent
       │        ├── hotel_results:   str                # filled by Hotel Agent
       │        ├── itinerary:       str                # filled by Itinerary Agent
       │        └── llm_calls:       int                # tracks total LLM invocations
       │
       ├─► Flight Agent writes → flight_results
       ├─► Hotel Agent writes  → hotel_results
       ├─► Itinerary Agent reads (flight_results + hotel_results) → writes itinerary
       └─► Final Agent reads (all three) → writes to messages[]
                                                │
                              ┌─────────────────▼──────────────────┐
                              │   PostgreSQL (Neon) Checkpointer    │
                              │   Saves every state snapshot with   │
                              │   thread_id for session replay      │
                              └────────────────────────────────────┘
```

The `Annotated[list[AnyMessage], operator.add]` annotation on `messages` means LangGraph **appends** each agent's messages rather than replacing them — giving you a full audit trail of every agent's contribution.

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **LLM Inference** | Groq Cloud — Llama 3.3 70B Versatile | Fast, high-quality text generation |
| **Agent Orchestration** | LangGraph `StateGraph` | Deterministic multi-agent pipeline |
| **State Persistence** | LangGraph `PostgresSaver` + Neon | Thread-based conversation memory |
| **Flight Data** | AviationStack REST API | Live real-world flight information |
| **Web Search** | Tavily AI Search API | Hotel & destination research |
| **IATA Extraction** | Llama 3.3 70B (structured JSON mode) | Airport code resolution from natural language |
| **UI Framework** | Streamlit | Reactive Python web app |
| **UI Theme** | Glassmorphism CSS + Backdrop Filter | Frosted glass dark aesthetic |
| **PDF Export** | fpdf2 (v2.5+ API) | Downloadable trip documents |
| **Clipboard** | Browser Clipboard API + execCommand fallback | One-click plan copying |
| **LLM Integration** | LangChain + `langchain-groq` | LLM client abstraction |
| **Environment** | python-dotenv | Secure secret management |

---

## 🔑 API Keys Reference

| Service | Get Your Key | Free Tier |
|---|---|---|
| **Groq** | https://console.groq.com | ✅ Free with rate limits |
| **AviationStack** | https://aviationstack.com | ✅ 100 req/month free |
| **Tavily** | https://tavily.com | ✅ 1,000 searches/month free |
| **Neon (PostgreSQL)** | https://neon.tech | ✅ Free serverless Postgres |

---

## 💡 Key Design Decisions

### Why LangGraph instead of a single LLM call?
Each agent is isolated and owns one task. This means failures are localised (if flight search fails, hotel search still runs), results are grounded in real data at each step, and the pipeline is easy to extend (add a `visa_agent` or `weather_agent` without touching the others).

### Why Groq + Llama 3.3?
Groq's LPU inference hardware runs Llama 3.3 70B at **~300 tokens/sec** — fast enough for real-time streaming in the UI with no perceptible lag, at a fraction of the cost of GPT-4.

### Why PostgreSQL for checkpointing?
LangGraph's `PostgresSaver` persists the entire `TravelState` after every node execution. This means:
- Users can close the browser and resume any trip conversation
- The Journeys tab can replay any past trip from the database
- Thread IDs tie each conversation to a unique user session

### Why AviationStack + Tavily instead of one search API?
Flight data requires structured, real-time data from an aviation-specific source. Hotel/destination data benefits from AI-native web search that understands semantic queries. Mixing both gives the best results for each domain.

### Self-Healing Flight Search
Rather than returning an error when a combined departure+arrival search returns no results, the flight tool degrades gracefully through three search strategies — ensuring the user always gets some flight context even if the exact route isn't in the live feed.

---

<div align="center">

Built with ❤️ using Python, LangGraph, and Groq

</div>
