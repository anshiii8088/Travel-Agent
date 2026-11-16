"""Memory domain models for short-term session context and long-term storage (Req 4)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class UserPreferenceItem(BaseModel):
    """Single persistent user preference entry."""
    key: str = Field(..., description="Unique preference key (e.g. favorite_destinations, dietary)")
    value: Any = Field(..., description="Value (string, list, or dict)")
    category: str = Field(default="general", description="Categorization: destination, food, budget, transport")
    updated_at: Optional[str] = None


class UserPreferencesProfile(BaseModel):
    """Aggregated long-term preferences profile recalled by the agent."""
    preferred_destinations: List[str] = Field(default_factory=list)
    favorite_activities: List[str] = Field(default_factory=list)
    preferred_food_types: List[str] = Field(default_factory=list)
    typical_budget_tier: str = Field(default="Moderate")
    preferred_transport: str = Field(default="Public / Car")
    custom_notes: Dict[str, Any] = Field(default_factory=dict)


class ShortTermMemory(BaseModel):
    """Short-term conversational and working memory for the active planning task."""
    session_id: str
    active_destination: Optional[str] = None
    step_count: int = 0
    intermediate_findings: Dict[str, Any] = Field(default_factory=dict)
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    is_completed: bool = False
    requires_approval: bool = False
    pending_approval_action: Optional[str] = None

