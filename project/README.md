# AI Smart Travel & Itinerary Planner

An agentic travel planning application that follows a Think → Act → Look loop, uses SQLite-backed memory, applies safety limits and human approval gates, and supports both mock and live Gemini-backed workflows.

## Features

- Travel request intake and validation
- Destination search, weather analysis, route planning, and budget calculations
- Persistent user preferences and session memory
- Safety controls with step caps and approval prompts for sensitive actions
- Stage 1 deterministic mock LLM for offline development and tests
- Stage 2 Google Gemini integration for live LLM planning
- FastAPI backend with SSE status streaming
- Responsive frontend dashboard and itinerary UI

## Project layout

- `backend/` – API, database, agent logic, memory, safety, and tools
- `frontend/` – static HTML, CSS, and frontend JavaScript
- `tests/` – automated regression and PRD validation suite
- `AI_Smart_Travel_Itinerary_Planner_PRD.md` – product requirements
- `task.md` – implementation and delivery plan

## Requirements

- Python 3.11+
- pip
- Optional: Google Gemini API key for live model mode

## Quickstart

1. Create and activate a virtual environment

   Windows PowerShell:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   macOS/Linux:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies

   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment

   Copy the sample config and adjust values if needed:

   ```bash
   copy .env.example .env
   ```

   Typical values:
   - `MOCK_LLM=True` for offline/mock mode
   - `MOCK_LLM=False` for live Gemini mode
   - `GEMINI_API_KEY=...` when using Gemini
   - `DATABASE_URL=sqlite:///./travel_planner.db`

4. Start the backend

   ```bash
   uvicorn backend.main:app --reload
   ```

   The API will be available at:
   - http://127.0.0.1:8000
   - http://127.0.0.1:8000/health

5. Open the frontend

   Serve the static app from the `frontend/` directory, for example:

   ```bash
   python -m http.server 8001 --directory frontend
   ```

   Then open:
   - http://127.0.0.1:8001/index.html

## Public deployment (Render)

Render hosts the FastAPI backend and the frontend from the same web service. The
website calls the API on the same origin, so no separate frontend host or CORS
configuration is needed. A persistent disk keeps SQLite preferences and logs
across service restarts; Render requires a paid instance for persistent disks.

1. Push this project to a GitHub repository. The included `.gitignore` excludes
   `.env`, local databases, and virtual environments. Never upload API keys.
2. In the Render dashboard, choose **New > Blueprint** and connect the GitHub
   repository containing `render.yaml`.
3. Review the `ai-smart-travel-planner-api` service and apply the Blueprint.
   The service uses a Starter instance and a 1 GB persistent disk for SQLite.
4. Wait for the first deploy to finish, then open the service's
   `https://<service-name>.onrender.com` URL. The homepage serves the app and
   `/health` should return `{"status":"ok"}`.
5. To enable Gemini instead of the default deterministic mock mode, add
   `MOCK_LLM=False` and `GEMINI_API_KEY` in the Render service's environment
   settings, then redeploy. Keep the API key private.

## Mock mode (recommended for local testing)

Set the following in `.env`:

```env
MOCK_LLM=True
```

This uses the deterministic fake LLM and avoids external API dependencies.

## Real Gemini mode

Set:

```env
MOCK_LLM=False
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Then restart the backend server.

## API overview

- `POST /api/plan` – create a trip plan
- `GET /api/plan/{session_id}/status` – fetch session state
- `GET /api/plan/{session_id}/stream` – SSE status stream
- `POST /api/plan/{session_id}/approve` – approve/proceed with sensitive actions
- `POST /api/chat` – ask follow-up questions about the itinerary
- `GET /api/preferences` – list stored preferences
- `PUT /api/preferences` – save or update preferences
- `DELETE /api/preferences` – delete preferences
- `GET /api/logs/{session_id}` – get execution logs

## Test suite

Run:

```bash
python -m pytest -q
```

Current verification status:
- 43 tests passing

## Notes

- The project is designed to work in mock mode by default for local QA.
- Logging redacts sensitive values to minimize credential leakage.
- Agent execution is capped at the configured maximum step count for safety.
