# AI Smart Travel & Itinerary Planner Agent - Step-by-Step Execution Plan

**Document Version:** 1.0  
**Target PRD:** `AI_Smart_Travel_Itinerary_Planner_PRD.md` (v2.0)  
**Status:** In Progress  
**Last Updated:** November 2026  

---

## 1. Project Overview & Architecture Blueprint

The goal is to build an Agentic AI Travel and Itinerary Planning application following the **Think → Act → Look** cycle, featuring 4 core tools, persistent SQLite memory, safety controls (step limiting, user approvals), a two-stage testing strategy (Fake LLM first, real Google Gemini LLM next), and a full-stack responsive web interface with a real-time agent execution dashboard.

### System Architecture Layout

```
                  +----------------------------------------------+
                  |               Web Frontend                   |
                  |  (HTML5 / CSS3 / Vanilla JS / Leaflet Maps)  |
                  +----------------------+-----------------------+
                                         | HTTP / SSE / WebSocket
                                         v
                  +----------------------------------------------+
                  |            FastAPI Backend App               |
                  |       (REST Endpoints, Static Files)         |
                  +----------------------+-----------------------+
                                         |
               +-------------------------+-------------------------+
               |                                                   |
               v                                                   v
+-------------------------------+               +----------------------------------+
|      Agent Orchestrator       |               |          Storage Layer           |
|  - Planning Before Acting     |               |  (SQLite DB via SQLAlchemy/SQL)  |
|  - Think -> Act -> Look Loop  |               |  - Long-Term Preferences         |
|  - Safety & Step Controller   |               |  - Itinerary History             |
|  - Execution Logger           |               |  - Agent Execution Logs          |
+---------------+---------------+               +----------------------------------+
                |
     +----------+----------+
     |                     |
     v                     v
+-----------+       +---------------+
| LLM Layer |       | Agent Tools   |
| - Fake LLM|       | 1. Search     |
| - Gemini  |       | 2. Weather    |
+-----------+       | 3. Route      |
                    | 4. Budget     |
                    +---------------+
```

---

## 2. Directory Structure Plan

```
project/
├── AI_Smart_Travel_Itinerary_Planner_PRD.md
├── task.md                                # This Execution Plan
├── requirements.txt                       # Python dependencies
├── .env.example                           # Template for API keys & config
├── .env                                   # Local environment config
├── backend/
│   ├── __init__.py
│   ├── main.py                            # FastAPI entry point & routes
│   ├── config.py                          # Settings & environment loading
│   ├── database.py                        # SQLite connection & schema init
│   ├── models/                            # Pydantic & DB schemas
│   │   ├── __init__.py
│   │   ├── travel.py                      # Request/Response/Itinerary schemas
│   │   ├── memory.py                      # User preferences & history models
│   │   └── execution_log.py               # Step-by-step agent trace schemas
│   ├── tools/                             # 4 Core PRD Tools
│   │   ├── __init__.py
│   │   ├── base.py                        # Base tool interface & error handling
│   │   ├── search_tool.py                 # Tool 1: Destination, attractions, hotels, food
│   │   ├── weather_tool.py                # Tool 2: Weather forecasts & rain probability
│   │   ├── route_tool.py                  # Tool 3: Routes, distances, durations
│   │   └── budget_tool.py                 # Tool 4: Cost breakdown & alternative suggestions
│   ├── agent/                             # Agentic Core Engine
│   │   ├── __init__.py
│   │   ├── planner.py                     # Requirement 5: Structured Planning phase
│   │   ├── loop.py                        # Requirement 1: Think -> Act -> Look Engine
│   │   ├── memory.py                      # Requirement 4: Short-term & Long-term memory
│   │   ├── safety.py                      # Requirement 6: Step limiter & human approval gate
│   │   ├── logger.py                      # Requirement 6.C: Sanitized execution audit logger
│   │   └── llm_provider.py                # Stage 1: Fake LLM vs Stage 2: Gemini LLM
│   └── services/                          # Business logic & orchestrators
│       ├── __init__.py
│       └── travel_planner_service.py      # End-to-end trip planning workflow
├── frontend/
│   ├── index.html                         # Unified responsive web app
│   ├── css/
│   │   └── styles.css                     # Modern UI styling, cards, timeline, dashboard
│   └── js/
│       ├── app.js                         # State management & event handlers
│       ├── api.js                         # Backend API communication
│       └── components/
│           ├── trip_form.js               # User Input Management (FR-01)
│           ├── itinerary_view.js          # Day-by-day schedule & map (FR-03, FR-08)
│           ├── chat_interface.js          # Travel Assistant Chat (FR-09, FR-10)
│           ├── agent_dashboard.js         # Real-time Think->Act->Look monitor
│           └── memory_modal.js            # User preference inspector/editor
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_tools.py                      # Unit tests for the 4 tools & error recovery
    ├── test_fake_llm_stage1.py            # 10 PRD Stage 1 test cases
    ├── test_safety_and_limits.py          # 10-step cap, booking approvals
    └── test_memory_persistence.py         # SQLite memory recall and updates
```

---

## 3. Phased Execution Roadmap

### Phase 1: Environment Setup & Foundation
- [x] **Task 1.1: Dependency Specification**
  - Create `requirements.txt` containing:
    - `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`
    - `google-genai` / `google-generativeai`, `langchain-core`
    - `httpx` or `requests` (for external APIs)
    - `pytest`, `pytest-asyncio` (for testing)
- [x] **Task 1.2: Environment Configuration**
  - Create `.env.example` and local `.env` with configurable flags:
    - `MOCK_LLM=True` (default to Fake LLM for Stage 1)
    - `GEMINI_API_KEY=""`
    - `DATABASE_URL="sqlite:///./travel_planner.db"`
    - `MAX_AGENT_STEPS=10`
- [x] **Task 1.3: Project Scaffold & Config Module**
  - Build `backend/config.py` using `pydantic_settings.BaseSettings`.
  - Validate Python environment.

---

### Phase 2: Data Models & SQLite Storage Layer (FR-01, FR-04, Req 4, Req 6)
- [x] **Task 2.1: Domain Models (`backend/models/travel.py`)**
  - `TravelRequest`: origin, destination, start_date, days, travellers, budget, travel_style, interests.
  - `Attraction`: name, visit_time, duration, location, activities, distance, cost.
  - `DailyItinerary`: day_number, date, attractions, meals, hotel, day_cost.
  - `BudgetBreakdown`: transport, accommodation, food, activities, miscellaneous, total, remaining_budget, is_over_budget.
  - `ItineraryResult`: destination, summary, daily_schedule, hotels, restaurants, budget_breakdown, weather_info, routes.
- [x] **Task 2.2: User Memory & Persistence Models (`backend/models/memory.py`)**
  - Short-term session memory schema (in-memory state of active trip session).
  - Long-term persistent preferences: favorite destinations, activity tags, dietary preferences, budget tier, preferred transport mode.
- [x] **Task 2.3: Execution Logging Models (`backend/models/execution_log.py`)**
  - Step logs: `step_id`, `timestamp`, `thought_reasoning`, `action_tool`, `tool_input`, `tool_output`, `status`, `error_msg`, `duration_ms`.
- [x] **Task 2.4: SQLite Database Initialization (`backend/database.py`)**
  - Create tables for `user_preferences`, `saved_itineraries`, and `execution_logs`.
  - Implement CRUD helpers for memory viewing, updating, and clearing.

---

### Phase 3: External Tool Implementations with Error Recovery (Req 2 & Req 3)
- [x] **Task 3.1: Base Tool & Error Handler (`backend/tools/base.py`)**
  - Define `BaseTool` abstract interface with `.execute(**kwargs)`.
  - Implement retry decorator (max 2 retries with backoff).
  - Define standard failure payload format (never fabricate data; flag fallback estimates as unverified).
- [x] **Task 3.2: Tool 1 - Destination Search Tool (`backend/tools/search_tool.py`)**
  - Input: destination, interests, budget tier.
  - Output: Attractions, hotels, and restaurants with costs, ratings, descriptions.
  - Resilience: Curated fallback database for top destinations (Munnar, Goa, Paris, Tokyo, etc.) when live search is unavailable.
- [x] **Task 3.3: Tool 2 - Weather Information Tool (`backend/tools/weather_tool.py`)**
  - Input: destination, travel_date.
  - Output: temperature (°C), conditions (Sunny/Rain/Cloudy), precipitation probability.
  - Error recovery: Handle network/API failure; return labeled estimate with warning flag for outdoor planning.
- [x] **Task 3.4: Tool 3 - Route Planning Tool (`backend/tools/route_tool.py`)**
  - Input: origin_coords/place, destination_coords/place, travel_mode (drive, transit, walk).
  - Output: distance (km), duration (mins), suggested route summary.
  - Fallback: Geodesic/Haversine heuristic estimate when routing API is offline.
- [x] **Task 3.5: Tool 4 - Budget Calculator Tool (`backend/tools/budget_tool.py`)**
  - Input: transport_cost, lodging_cost, food_cost, activity_cost, total_budget, travellers.
  - Output: total_expense, per_person_expense, remaining_budget, variance, affordable recommendations if over-budget.
  - Deterministic calculations guaranteed.

---

### Phase 4: Agent Core Engine (Req 1, 4, 5, 6)
- [x] **Task 4.1: Planning Stage Module (`backend/agent/planner.py`)**
  - Takes raw user request + recalled long-term preferences.
  - Produces an explicit multi-step plan before tool invocation (e.g. 7-step sequence as defined in PRD Section 5.5).
- [x] **Task 4.2: Think → Act → Look Execution Loop (`backend/agent/loop.py`)**
  - **Think**: Analyze current state, previous observations, and goal. Decide next action or finalize.
  - **Act**: Select tool and invoke with structured parameters.
  - **Look**: Observe tool output, validate constraints (budget fit, weather feasibility), check errors.
  - Loop termination: Goal met, or step limit reached.
- [x] **Task 4.3: Safety Controller & Execution Limiter (`backend/agent/safety.py`)**
  - Enforce `MAX_STEPS = 10` hard cap. If step counter reaches 10, halt gracefully and report incomplete subtasks.
  - Human-in-the-Loop Approval gate: Intercept actions like booking, payment, or private info dispatch; issue `APPROVAL_REQUIRED` status.
- [x] **Task 4.4: Execution Logger & Sanitizer (`backend/agent/logger.py`)**
  - Log every Think, Act, Look step with timestamps.
  - Sanitize logs: automatically redact keys, credentials, and sensitive private data.
- [x] **Task 4.5: Memory Manager (`backend/agent/memory.py`)**
  - Manage session short-term memory (active context).
  - Query SQLite for existing user preferences on start.
  - Persist newly learned preferences after user consent.

---

### Phase 5: Testing Strategy - Stage 1: Fake LLM Implementation & Test Suite (Req 7)
- [x] **Task 5.1: Fake LLM Provider (`backend/agent/llm_provider.py`)**
  - Deterministic mock LLM responding according to PRD section 5.7 rules.
  - Allows full autonomous loop execution, tool invocation, and decision making completely offline.
- [x] **Task 5.2: Comprehensive Automated Test Suite (`tests/`)**
  - Implement tests for the 10 PRD-mandated scenarios:
    1. `test_valid_destination`: Generates complete day-by-day itinerary.
    2. `test_invalid_destination`: Gracefully catches error and requests clarification.
    3. `test_budget_too_low`: Triggers budget tool alert and suggests cost-saving alternatives.
    4. `test_weather_api_failure`: Gracefully recovers without crashing, alerts user, uses labeled estimates.
    5. `test_route_api_failure`: Falls back to alternative distance estimation.
    6. `test_previous_preference_recall`: Confirms memory manager injects saved preferences into new trip.
    7. `test_step_limit_enforcement`: Asserts loop stops at step 10 when over limit.
    8. `test_booking_request_approval`: Verifies human approval requirement before booking action.
    9. `test_destination_change_modification`: Verifies itinerary updates while preserving core preferences.
    10. `test_fake_llm_standalone`: Verifies system functions completely offline without Gemini API key.

---

### Phase 6: Stage 2: Real Google Gemini LLM Integration
- [ ] **Task 6.1: Gemini Client Integration (`backend/agent/llm_provider.py`)**
  - Implement `GeminiLLMProvider` using Google Gemini 2.5/Flash API.
  - System prompts enforcing Think → Act → Look structured output and tool schemas.
- [ ] **Task 6.2: Fallback & Mode Switcher**
  - Seamless toggle between `FakeLLM` (for unit tests / mock mode) and `GeminiLLM` via `.env` or UI toggle.
- [ ] **Task 6.3: Itinerary Modification & Conversational Chat (FR-09, FR-10)**
  - Support follow-up questions ("reduce budget by 20%", "swap day 2 for indoor museums").
  - Maintain context while updating specific days or activities.

---

### Phase 7: Backend API Development (FastAPI)
- [ ] **Task 7.1: REST Endpoints (`backend/main.py`)**
  - `POST /api/plan`: Start planning task (returns session ID & streaming/polling updates).
  - `GET /api/plan/{session_id}/status`: Fetch current execution state & Think-Act-Look logs.
  - `POST /api/plan/{session_id}/approve`: Submit user approval for sensitive actions.
  - `POST /api/chat`: Chatbot assistant for itinerary queries and modifications.
  - `GET /api/preferences`: Retrieve saved long-term user preferences.
  - `PUT /api/preferences`: Update preferences.
  - `DELETE /api/preferences`: Clear saved preferences.
  - `GET /api/logs/{session_id}`: Retrieve sanitized execution log.
- [ ] **Task 7.2: Server-Sent Events (SSE) or Live Polling for Agent Activity**
  - Stream live Think → Act → Look steps directly to frontend agent activity dashboard.

---

### Phase 8: Frontend User Interface Development
- [ ] **Task 8.1: Modern UI Layout & Styling (`frontend/index.html`, `styles.css`)**
  - Responsive, clean travel design with tabbed navigation:
    1. Plan Trip (Input Form)
    2. Itinerary View (Daily Timeline, Cards, Map)
    3. AI Chatbot Assistant (Drawer / Floating Panel)
    4. Agent Activity Dashboard (Live reasoning, tool monitor, step counter)
    5. Memory & Preferences Settings
- [ ] **Task 8.2: Trip Input Form Component (`frontend/js/components/trip_form.js`)**
  - Form validation for Origin, Destination, Dates, Days, Travellers, Budget, Style, Interests.
- [ ] **Task 8.3: Itinerary Results & Interactive Map (`frontend/js/components/itinerary_view.js`)**
  - Day-by-day timeline with time slots, duration, cost, attraction images/tags.
  - Hotel & restaurant recommendation cards.
  - Budget breakdown summary card (pie/bar visuals).
  - Interactive Leaflet.js map with markers and routes.
- [ ] **Task 8.4: Live Agent Activity Dashboard (`frontend/js/components/agent_dashboard.js`)**
  - Visual display of:
    - Current Task & Structured Plan (Steps 1 to 7)
    - Active Phase badge (Think, Act, Look)
    - Tool invocation details (Tool name, Input payload, Output status)
    - Execution Step Gauge (e.g. `Step 4 / 10`)
    - Error recovery notices
- [ ] **Task 8.5: Chatbot & Modification Panel (`frontend/js/components/chat_interface.js`)**
  - Conversational interface with quick suggestion pills ("Reduce budget", "Find vegetarian options", "Change destination").
- [ ] **Task 8.6: User Memory Inspector (`frontend/js/components/memory_modal.js`)**
  - View, edit, or delete saved travel preferences.

---

### Phase 9: End-to-End Verification & Quality Assurance
- [x] **Task 9.1: Automated Test Suite Execution**
  - Run `pytest` across all unit, tool, safety, memory, and Stage 1 Fake LLM scenarios.
- [x] **Task 9.2: End-to-End Simulation Run**
  - Run full Munnar / Goa trip planning workflow.
  - Verify live Think → Act → Look updates in UI.
  - Verify budget calculation accuracy and weather warnings.
- [x] **Task 9.3: Security & Safety Audit**
  - Ensure zero credential exposure in logs or UI.
  - Verify step limit termination test.
  - Verify booking confirmation safety prompt.

---

### Phase 10: Documentation & Handover
- [x] **Task 10.1: Update `task.md` with Completion Status**
- [x] **Task 10.2: Provide Comprehensive README / Quickstart Guide**
  - Instructions on running mock mode (`MOCK_LLM=True`) and real Gemini mode.
  - Local server start instructions (`uvicorn backend.main:app --reload`).

---

## 4. Requirement Verification Traceability Matrix

| Requirement | PRD Section | Covered In Phase / Task | Verification Method |
|---|---|---|---|
| User Input Management | FR-01 | Phase 2 (Task 2.1), Phase 8 (Task 8.2) | Form input validation & API model tests |
| AI Destination Recommendation | FR-02 | Phase 3 (Task 3.2), Phase 4 (Task 4.2) | Destination Search tool & LLM prompt |
| Day-by-Day Itinerary Generation | FR-03 | Phase 2 (Task 2.1), Phase 8 (Task 8.3) | Complete itinerary output validation |
| Budget Planning & Calculation | FR-04 | Phase 3 (Task 3.5), Phase 8 (Task 8.3) | Budget tool math assertions & UI breakdown |
| Hotel & Restaurant Suggestions | FR-05, FR-06 | Phase 3 (Task 3.2), Phase 8 (Task 8.3) | Search tool results & recommendation cards |
| Weather Forecasting & Alerts | FR-07 | Phase 3 (Task 3.3), Phase 8 (Task 8.3) | Weather tool forecast & fallback tests |
| Route Planning & Map Display | FR-08 | Phase 3 (Task 3.4), Phase 8 (Task 8.3) | Route tool calculation & Leaflet map markers |
| AI Chatbot & Modifications | FR-09, FR-10 | Phase 6 (Task 6.3), Phase 8 (Task 8.5) | Follow-up modification requests |
| Think → Act → Look Loop | Req 1 (5.1) | Phase 4 (Task 4.2), Phase 8 (Task 8.4) | Loop cycle trace in test logs & UI dashboard |
| 4 AI Agent Tools | Req 2 (5.2) | Phase 3 (Tasks 3.1 - 3.5) | Tool unit tests (`tests/test_tools.py`) |
| Tool Failure & Error Recovery | Req 3 (5.3) | Phase 3 (Tasks 3.1 - 3.4), Phase 5 (5.2) | Mock error injection tests (weather, route) |
| Short- & Long-Term Memory | Req 4 (5.4) | Phase 2 (Task 2.2), Phase 4 (Task 4.5) | Memory recall & SQLite CRUD tests |
| Structured Planning Before Acting | Req 5 (5.5) | Phase 4 (Task 4.1), Phase 8 (Task 8.4) | Pre-execution plan generation assertion |
| Safety & Step Limit (Max 10) | Req 6.B (5.6) | Phase 4 (Task 4.3), Phase 5 (Task 5.2) | Step cap test (`tests/test_safety_and_limits.py`)|
| User Approval Gate | Req 6.A (5.6) | Phase 4 (Task 4.3), Phase 7 (Task 7.1) | Simulated booking approval interception test |
| Execution Logging & Redaction | Req 6.C (5.6) | Phase 2 (2.3), Phase 4 (4.4), Phase 7 (7.1) | Sanitized log format check |
| Fake LLM Stage 1 Testing | Req 7 (5.7) | Phase 5 (Tasks 5.1 & 5.2) | 10 PRD Stage 1 test suite passing offline |
| Real Gemini LLM Integration | Req 7 (5.7) | Phase 6 (Tasks 6.1 - 6.3) | Live Gemini API integration test |

