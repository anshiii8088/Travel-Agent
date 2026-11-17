"""Agent Execution Logger and Sanitizer (PRD Section 5.6.C).

Records step-by-step Think, Act, and Look decisions into the database
while automatically redacting API keys, passwords, and sensitive credentials.
"""

import json
import re
from typing import Any, Dict, List, Optional
from backend.database import log_execution_step, get_session_logs

# Patterns for sensitive credentials to redact
SENSITIVE_PATTERNS = [
    (re.compile(r"(api[_-]?key|secret|password|token|bearer)\s*[:=]\s*['\"]?([^'\"\s,]+)['\"]?", re.IGNORECASE), r"\1: [REDACTED]"),
    (re.compile(r"AIza[0-9A-Za-z-_]{35}"), "[REDACTED_API_KEY]"),
    (re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b"), "[REDACTED_CARD_NUMBER]"),
]


def sanitize_data(data: Any) -> Any:
    """Recursively redact sensitive tokens from strings, dictionaries, and lists."""
    if isinstance(data, str):
        cleaned = data
        for pattern, replacement in SENSITIVE_PATTERNS:
            cleaned = pattern.sub(replacement, cleaned)
        return cleaned

    elif isinstance(data, dict):
        sanitized_dict = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if any(term in k_lower for term in ("key", "secret", "password", "token", "auth")):
                sanitized_dict[k] = "[REDACTED]"
            else:
                sanitized_dict[k] = sanitize_data(v)
        return sanitized_dict

    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]

    return data


class AgentExecutionLogger:
    """Manages audit logging for agent Think -> Act -> Look phases."""

    def __init__(self, session_id: str, db_path: Optional[str] = None) -> None:
        self.session_id = session_id
        self.db_path = db_path
        self._in_memory_logs: List[Dict[str, Any]] = []

    def log_step(
        self,
        step_number: int,
        phase: str,  # PLAN, THINK, ACT, LOOK, SAFETY, ERROR_RECOVERY
        thought: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_input: Optional[Any] = None,
        tool_output: Optional[Any] = None,
        status: str = "SUCCESS",
        error_message: Optional[str] = None,
    ) -> None:
        """Sanitize and persist a single execution step to memory and SQLite."""
        clean_thought = sanitize_data(thought) if thought else None
        clean_input = sanitize_data(tool_input) if tool_input is not None else None
        clean_output = sanitize_data(tool_output) if tool_output is not None else None
        clean_error = sanitize_data(error_message) if error_message else None

        entry = {
            "session_id": self.session_id,
            "step_number": step_number,
            "phase": phase,
            "thought": clean_thought,
            "tool_name": tool_name,
            "tool_input": clean_input,
            "tool_output": clean_output,
            "status": status,
            "error_message": clean_error,
        }
        self._in_memory_logs.append(entry)

        # Write to persistent database
        log_execution_step(
            session_id=self.session_id,
            step_number=step_number,
            phase=phase,
            thought=clean_thought,
            tool_name=tool_name,
            tool_input=clean_input,
            tool_output=clean_output,
            status=status,
            error_message=clean_error,
            db_path=self.db_path,
        )

    def get_logs(self) -> List[Dict[str, Any]]:
        """Retrieve stored logs for this session."""
        if self._in_memory_logs:
            return self._in_memory_logs
        return get_session_logs(self.session_id, db_path=self.db_path)

