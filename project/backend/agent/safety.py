"""Safety and Execution Controller (PRD Section 5.6).

Enforces execution step limits (max 10 steps), requires user confirmation
for sensitive actions (booking, payments, personal data), and validates policies.
"""

from enum import Enum
from typing import Any, Dict, Optional, Set
from pydantic import BaseModel, Field


class SafetyActionType(str, Enum):
    """Categorization of actions based on risk level."""
    SAFE_QUERY = "SAFE_QUERY"              # Search, weather, route, budget
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"  # Booking, payments, dispatching private info
    RESTRICTED = "RESTRICTED"              # Unauthorized payment or bypass attempt


class SafetyDecision(BaseModel):
    """Result of a safety evaluation on a proposed agent action."""
    action_type: SafetyActionType
    allowed_to_proceed: bool
    requires_user_approval: bool = False
    approval_prompt: Optional[str] = None
    reason: str


class SafetyController:
    """Monitors and constrains agent actions to ensure safety and resource bounds."""

    # Default maximum tool steps allowed per planning session (PRD Requirement 6.B)
    DEFAULT_MAX_STEPS: int = 10

    # Actions strictly requiring human approval before execution (PRD Requirement 6.A)
    SENSITIVE_ACTIONS: Set[str] = {
        "book_hotel",
        "book_flight",
        "book_transport",
        "make_payment",
        "confirm_reservation",
        "share_personal_info",
    }

    def __init__(self, max_steps: int = DEFAULT_MAX_STEPS) -> None:
        self.max_steps = max_steps
        self.current_step_count = 0
        self.is_cancelled = False
        self.pending_approval_action: Optional[Dict[str, Any]] = None
        self.approved_actions: Set[str] = set()

    def check_step_limit(self) -> tuple[bool, Optional[str]]:
        """Verify whether the agent has reached the maximum execution step limit.
        
        Returns:
            (can_continue, message_if_stopped)
        """
        if self.is_cancelled:
            return False, "Task execution was cancelled by the user."

        if self.current_step_count >= self.max_steps:
            return (
                False,
                f"Maximum execution step limit ({self.max_steps}) reached. "
                "Agent stopped execution safely to prevent runaway loops.",
            )
        return True, None

    def record_step(self) -> int:
        """Increment step counter and return new count."""
        self.current_step_count += 1
        return self.current_step_count

    def cancel_task(self) -> None:
        """Mark current task as cancelled by user (PRD Requirement 6.D)."""
        self.is_cancelled = True

    def evaluate_action(
        self, action_name: str, action_payload: Optional[Dict[str, Any]] = None
    ) -> SafetyDecision:
        """Evaluate a proposed action against safety rules and human approval gates."""
        if self.is_cancelled:
            return SafetyDecision(
                action_type=SafetyActionType.RESTRICTED,
                allowed_to_proceed=False,
                reason="Task was cancelled by user.",
            )

        action_clean = action_name.lower().strip()

        # Check for sensitive transactional actions requiring user approval
        if action_clean in self.SENSITIVE_ACTIONS:
            # If already approved by user in this session, allow
            if action_clean in self.approved_actions:
                return SafetyDecision(
                    action_type=SafetyActionType.SAFE_QUERY,
                    allowed_to_proceed=True,
                    reason=f"Action '{action_clean}' was explicitly approved by user.",
                )

            self.pending_approval_action = {
                "action": action_clean,
                "payload": action_payload or {},
            }
            return SafetyDecision(
                action_type=SafetyActionType.APPROVAL_REQUIRED,
                allowed_to_proceed=False,
                requires_user_approval=True,
                approval_prompt=(
                    f"User Approval Required: The agent wants to execute '{action_clean}'. "
                    f"Details: {action_payload or 'Standard booking parameters'}. "
                    "Do you authorize this transaction?"
                ),
                reason=f"Action '{action_clean}' requires explicit user confirmation before proceeding.",
            )

        # Non-booking analytical tools (search, weather, route, budget) are safe to proceed
        return SafetyDecision(
            action_type=SafetyActionType.SAFE_QUERY,
            allowed_to_proceed=True,
            reason="Action is read-only / analytical and within safety boundaries.",
        )

    def grant_approval(self, action_name: str) -> None:
        """Record user confirmation for a pending sensitive action."""
        self.approved_actions.add(action_name.lower().strip())
        self.pending_approval_action = None

