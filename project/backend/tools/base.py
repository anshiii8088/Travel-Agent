"""Base tool architecture, ToolResult structure, and retry/error handling mechanism (Req 2 & 3)."""

from abc import ABC, abstractmethod
import time
from typing import Any, Callable, Dict, Optional
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Standardized response container for all agent tool executions."""
    tool_name: str
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    is_estimate: bool = False
    is_fallback: bool = False
    retries_attempted: int = 0
    warning: Optional[str] = None

    def to_summary_dict(self) -> Dict[str, Any]:
        """Sanitized representation suitable for logging and LLM prompt consumption."""
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "is_estimate": self.is_estimate,
            "is_fallback": self.is_fallback,
            "error": self.error,
            "warning": self.warning,
            "data": self.data,
        }


class BaseTool(ABC):
    """Abstract base class for all external tools in the travel planning agent."""

    name: str = "base_tool"
    description: str = "Base tool description"

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool logic and return a ToolResult."""
        pass

    def _execute_with_retry(
        self,
        func: Callable[[], Dict[str, Any]],
        max_retries: int = 2,
        delay_seconds: float = 0.5,
    ) -> tuple[bool, Dict[str, Any], Optional[str], int]:
        """Execute callable with exponential backoff retry mechanism.
        
        Returns:
            (success, data, error_message, retries_attempted)
        """
        last_error = None
        retries = 0

        for attempt in range(max_retries + 1):
            try:
                data = func()
                return True, data, None, retries
            except Exception as exc:
                last_error = str(exc)
                retries = attempt
                if attempt < max_retries:
                    time.sleep(delay_seconds * (2 ** attempt))

        return False, {}, last_error, retries

