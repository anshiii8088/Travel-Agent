"""Execution log domain models for agent traceability and dashboard (Req 6.C)."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AgentStepLog(BaseModel):
    """Structured log item representing a single Think, Act, or Look step."""
    session_id: str
    step_number: int
    phase: str = Field(..., description="PLAN, THINK, ACT, LOOK, SAFETY, or ERROR_RECOVERY")
    thought: Optional[str] = Field(default=None, description="Internal reasoning / analysis")
    tool_name: Optional[str] = Field(default=None, description="Tool executed if ACT phase")
    tool_input: Optional[Any] = Field(default=None, description="Sanitized input arguments")
    tool_output: Optional[Any] = Field(default=None, description="Sanitized observation result")
    status: str = Field(default="SUCCESS", description="SUCCESS, ERROR, RECOVERED, LIMIT_REACHED, APPROVAL_REQUIRED")
    error_message: Optional[str] = None
    created_at: str

