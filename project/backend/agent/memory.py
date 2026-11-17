"""Memory Manager for short-term session state and long-term SQLite memory (PRD Section 5.4).

Maintains active conversational working memory and persists user travel preferences
across tasks (favorite destinations, dietary needs, budget styles, and previous trips).
"""

from typing import Any, Dict, List, Optional
from backend.database import (
    clear_all_preferences,
    delete_preference,
    get_all_preferences,
    get_preference,
    set_preference,
)
from backend.models.memory import ShortTermMemory, UserPreferencesProfile


class MemoryManager:
    """Coordinates working memory for active tasks and persistent long-term memory."""

    def __init__(self, session_id: str, db_path: Optional[str] = None) -> None:
        self.session_id = session_id
        self.db_path = db_path
        self.short_term = ShortTermMemory(session_id=session_id)

    # --------------------------------------------------------------------------
    # Short-Term Working Memory
    # --------------------------------------------------------------------------

    def store_finding(self, key: str, value: Any) -> None:
        """Store intermediate observations from tool executions in working memory."""
        self.short_term.intermediate_findings[key] = value

    def get_finding(self, key: str, default: Any = None) -> Any:
        """Retrieve intermediate tool observation from working memory."""
        return self.short_term.intermediate_findings.get(key, default)

    def record_message(self, role: str, content: str) -> None:
        """Append to conversational context history."""
        self.short_term.conversation_history.append({"role": role, "content": content})

    # --------------------------------------------------------------------------
    # Long-Term Persistent Memory (Between Tasks)
    # --------------------------------------------------------------------------

    def recall_user_profile(self) -> UserPreferencesProfile:
        """Load persistent user preferences from SQLite into an aggregated profile."""
        all_prefs = get_all_preferences(db_path=self.db_path)
        profile = UserPreferencesProfile()

        if "favorite_destinations" in all_prefs:
            val = all_prefs["favorite_destinations"]["value"]
            profile.preferred_destinations = val if isinstance(val, list) else [val]

        if "favorite_activities" in all_prefs:
            val = all_prefs["favorite_activities"]["value"]
            profile.favorite_activities = val if isinstance(val, list) else [val]

        if "dietary_preferences" in all_prefs:
            val = all_prefs["dietary_preferences"]["value"]
            profile.preferred_food_types = val if isinstance(val, list) else [val]

        if "budget_tier" in all_prefs:
            profile.typical_budget_tier = str(all_prefs["budget_tier"]["value"])

        if "preferred_transport" in all_prefs:
            profile.preferred_transport = str(all_prefs["preferred_transport"]["value"])

        return profile

    def save_preference(self, key: str, value: Any, category: str = "general") -> None:
        """Persist or update a user preference in SQLite."""
        set_preference(key, value, category=category, db_path=self.db_path)

    def learn_from_request(
        self,
        destination: Optional[str] = None,
        interests: Optional[List[str]] = None,
        dietary: Optional[str] = None,
        transport: Optional[str] = None,
    ) -> None:
        """Automatically record preferences learned during a trip planning session."""
        if destination:
            dests = get_preference("favorite_destinations", default=[], db_path=self.db_path)
            if destination not in dests:
                dests.append(destination)
                set_preference("favorite_destinations", dests, category="destination", db_path=self.db_path)

        if interests:
            acts = get_preference("favorite_activities", default=[], db_path=self.db_path)
            for act in interests:
                if act not in acts:
                    acts.append(act)
            set_preference("favorite_activities", acts, category="activities", db_path=self.db_path)

        if dietary and dietary != "Any":
            set_preference("dietary_preferences", [dietary], category="food", db_path=self.db_path)

        if transport and transport != "Public / Car":
            set_preference("preferred_transport", transport, category="transport", db_path=self.db_path)

    def delete_saved_preference(self, key: str) -> bool:
        """Remove a specific preference."""
        return delete_preference(key, db_path=self.db_path)

    def clear_memory(self) -> None:
        """Wipe all saved long-term preferences."""
        clear_all_preferences(db_path=self.db_path)

