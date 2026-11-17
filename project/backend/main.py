"""FastAPI entry point for the AI Travel Planner backend."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.models.travel import TravelRequest
from backend.services.travel_planner_service import TravelPlannerService

service = TravelPlannerService()
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


class PlanApprovalRequest(BaseModel):
    approved: bool = Field(default=True)


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str = Field(..., min_length=1)
    itinerary: Optional[Dict[str, Any]] = None


app = FastAPI(title="AI Smart Travel Itinerary Planner", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/plan")
def plan_trip(request: Dict[str, Any]) -> Dict[str, Any]:
    """Create a travel itinerary from a user request."""
    try:
        validated = TravelRequest.model_validate(request)
    except Exception as exc:  # pragma: no cover - defensive validation path
        raise HTTPException(status_code=422, detail=f"Invalid request payload: {exc}") from exc

    result = service.plan_trip(validated)
    payload = {
        "session_id": result.session_id,
        "status": result.status,
        "steps_taken": result.steps_taken,
        "error_message": result.error_message,
        "pending_approval_prompt": result.pending_approval_prompt,
    }
    if result.plan:
        payload["plan"] = result.plan.to_dict()
    if result.itinerary:
        payload["itinerary"] = result.itinerary.model_dump()
    return payload


@app.get("/api/plan/{session_id}/status")
def get_plan_status(session_id: str) -> Dict[str, Any]:
    result = service.get_status(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    payload = {
        "session_id": result.session_id,
        "status": result.status,
        "steps_taken": result.steps_taken,
        "error_message": result.error_message,
        "pending_approval_prompt": result.pending_approval_prompt,
    }
    if result.plan:
        payload["plan"] = result.plan.to_dict()
    if result.itinerary:
        payload["itinerary"] = result.itinerary.model_dump()
    return payload


@app.get("/api/plan/{session_id}/stream")
def stream_plan_status(session_id: str):
    """Stream lightweight server-sent events representing session progress."""
    result = service.get_status(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")

    def event_generator():
        for _ in range(2):
            payload = {
                "session_id": session_id,
                "status": result.status,
                "steps_taken": result.steps_taken,
                "error_message": result.error_message,
                "pending_approval_prompt": result.pending_approval_prompt,
            }
            yield "event: session_status\n"
            yield f"data: {json.dumps(payload)}\n\n"
            time.sleep(0.1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/plan/{session_id}/approve")
def approve_plan(session_id: str, approval: PlanApprovalRequest) -> Dict[str, Any]:
    response = service.approve_action(session_id, approved=approval.approved)
    if response.get("status") == "NOT_FOUND":
        raise HTTPException(status_code=404, detail="Session not found")
    return response


@app.post("/api/chat")
def chat_with_agent(request: ChatRequest) -> Dict[str, Any]:
    response = service.chat(request.session_id, request.message, request.itinerary)
    return response


@app.get("/api/preferences")
def get_preferences() -> Dict[str, Any]:
    return service.get_preferences()


@app.put("/api/preferences")
def update_preferences(payload: Dict[str, Any]) -> Dict[str, Any]:
    return service.upsert_preferences(payload)


@app.delete("/api/preferences")
def delete_preferences(payload: Optional[Dict[str, Any]] = None, key: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    return service.delete_preference(key=key, payload=payload)


@app.get("/api/logs/{session_id}")
def get_logs(session_id: str) -> Dict[str, Any]:
    return {"session_id": session_id, "logs": service.get_logs(session_id)}


@app.get("/")
def root() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
