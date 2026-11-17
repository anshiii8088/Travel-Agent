"""Service layer for orchestrating trip planning requests and session state."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.agent.llm_provider import get_llm_provider
from backend.agent.loop import AgentLoopResult, TravelPlannerAgent
from backend.agent.memory import MemoryManager
from backend.database import (
    clear_all_preferences,
    delete_preference,
    get_all_preferences,
    get_session_logs,
    set_preference,
)
from backend.models.travel import TravelRequest


class TravelPlannerService:
    """Holds active planning sessions and exposes API-friendly orchestration methods."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path
        self._sessions: Dict[str, AgentLoopResult] = {}

    def start_planning(self, request: TravelRequest) -> AgentLoopResult:
        """Execute a travel planning cycle and retain the result for polling."""
        session_id = request.origin or "session"
        session_id = f"{session_id}-{len(self._sessions) + 1}"
        agent = TravelPlannerAgent(session_id=session_id, db_path=self.db_path)
        result = agent.run_planning_cycle(request)
        self._sessions[session_id] = result
        return result

    def plan_trip(self, request: TravelRequest) -> AgentLoopResult:
        """Compatibility entry point for FastAPI route handlers."""
        return self.start_planning(request)

    def get_status(self, session_id: str) -> Optional[AgentLoopResult]:
        """Return the stored session state for a given session ID."""
        return self._sessions.get(session_id)

    def approve_action(self, session_id: str, approved: bool = True) -> Dict[str, Any]:
        """Handle approval responses for sensitive actions like booking."""
        result = self._sessions.get(session_id)
        if result is None:
            return {"session_id": session_id, "status": "NOT_FOUND"}

        if approved:
            result.status = "APPROVED"
            result.pending_approval_prompt = None
            return {
                "session_id": session_id,
                "status": "APPROVED",
                "itinerary": result.itinerary.model_dump() if result.itinerary else None,
            }

        result.status = "CANCELLED"
        result.pending_approval_prompt = None
        return {"session_id": session_id, "status": "CANCELLED"}

    def chat(self, session_id: Optional[str], user_query: str, itinerary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Answer conversational user questions using the active itinerary context."""
        provider = get_llm_provider()
        parsed_itinerary = None
        if session_id:
            result = self._sessions.get(session_id)
            if result and result.itinerary:
                parsed_itinerary = result.itinerary
        if itinerary and parsed_itinerary is None:
            try:
                from backend.models.travel import ItineraryResult
                parsed_itinerary = ItineraryResult.model_validate(itinerary)
            except Exception:
                parsed_itinerary = None
        response = provider.answer_chat_query(user_query, parsed_itinerary)
        if session_id:
            memory = MemoryManager(session_id, db_path=self.db_path)
            memory.record_message("user", user_query)
            memory.record_message("assistant", response)
        return {"session_id": session_id, "response": response}

    def get_preferences(self) -> Dict[str, Any]:
        """Return all saved long-term preferences."""
        return get_all_preferences(db_path=self.db_path)

    def upsert_preferences(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Persist a single or multiple preferences from a dictionary payload."""
        if "key" in payload and "value" in payload:
            set_preference(payload["key"], payload["value"], category=payload.get("category", "general"), db_path=self.db_path)
        else:
            for key, value in payload.items():
                set_preference(key, value, category="general", db_path=self.db_path)
        return self.get_preferences()

    def delete_preference(self, key: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Delete one preference or clear the whole store."""
        if key is None and payload and "key" in payload:
            key = payload["key"]
        if key:
            deleted = delete_preference(key, db_path=self.db_path)
            return {"deleted": deleted, "key": key, "preferences": self.get_preferences()}
        clear_all_preferences(db_path=self.db_path)
        return {"deleted": True, "preferences": self.get_preferences()}

    def get_logs(self, session_id: str) -> List[Dict[str, Any]]:
        """Return sanitized execution logs for a session."""
        return get_session_logs(session_id, db_path=self.db_path)
