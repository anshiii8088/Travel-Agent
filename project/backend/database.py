"""SQLite Database Layer for AI Smart Travel & Itinerary Planner Agent.

Zero-dependency SQLite storage for long-term memory, saved itineraries,
and sanitized execution logs.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from backend.config import settings


def _resolve_db_path() -> str:
    url = getattr(settings, "DATABASE_URL", "sqlite:///./travel_planner.db")
    if url.startswith("sqlite:///"):
        rel_or_abs = url.replace("sqlite:///", "")
        if rel_or_abs == ":memory:":
            return ":memory:"
        return str(Path(__file__).parent.parent / rel_or_abs)
    return str(Path(__file__).parent.parent / "travel_planner.db")


DB_FILE = _resolve_db_path()


def _get_utc_now() -> str:
    """Return current ISO-formatted UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _ensure_db_initialized(db_path: Optional[str] = None) -> None:
    """Create the SQLite tables if they do not already exist."""
    target = db_path if db_path is not None else DB_FILE
    target_path = Path(target)
    if target_path.name and target_path.parent != Path(""):
        target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(target)
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                updated_at TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_itineraries (
                id TEXT PRIMARY KEY,
                destination TEXT NOT NULL,
                start_date TEXT,
                days INTEGER NOT NULL,
                travellers INTEGER NOT NULL,
                budget REAL NOT NULL,
                itinerary_data TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                step_number INTEGER NOT NULL,
                phase TEXT NOT NULL,
                thought TEXT,
                tool_name TEXT,
                tool_input TEXT,
                tool_output TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_db_connection(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    """Yield a connection to the SQLite database and ensure it is properly closed."""
    target = db_path if db_path is not None else DB_FILE
    _ensure_db_initialized(target)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize database tables if they do not exist."""
    _ensure_db_initialized(db_path)


# ==============================================================================
# Long-Term Preference (Memory) CRUD Functions
# ==============================================================================

def set_preference(key: str, value: Any, category: str = "general", db_path: Optional[str] = None) -> None:
    """Save or update a persistent user preference."""
    now = _get_utc_now()
    val_json = json.dumps(value)
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_preferences (key, value, category, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                category = excluded.category,
                updated_at = excluded.updated_at
            """,
            (key, val_json, category, now),
        )
        conn.commit()


def get_preference(key: str, default: Any = None, db_path: Optional[str] = None) -> Any:
    """Retrieve a single saved preference by key."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            return json.loads(row["value"])
    return default


def get_all_preferences(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve all saved user preferences."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value, category, updated_at FROM user_preferences")
        rows = cursor.fetchall()
        return {
            row["key"]: {
                "value": json.loads(row["value"]),
                "category": row["category"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        }


def delete_preference(key: str, db_path: Optional[str] = None) -> bool:
    """Delete a specific user preference."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_preferences WHERE key = ?", (key,))
        conn.commit()
        return cursor.rowcount > 0


def clear_all_preferences(db_path: Optional[str] = None) -> None:
    """Clear all stored preferences."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_preferences")
        conn.commit()


# ==============================================================================
# Itinerary Persistence CRUD Functions
# ==============================================================================

def save_itinerary(
    itinerary_id: str,
    destination: str,
    start_date: str,
    days: int,
    travellers: int,
    budget: float,
    itinerary_data: Dict[str, Any],
    db_path: Optional[str] = None,
) -> None:
    """Save an itinerary to the database."""
    now = _get_utc_now()
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO saved_itineraries
            (id, destination, start_date, days, travellers, budget, itinerary_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                itinerary_id,
                destination,
                start_date,
                days,
                travellers,
                budget,
                json.dumps(itinerary_data),
                now,
            ),
        )
        conn.commit()


def get_itinerary(itinerary_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve a saved itinerary by ID."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM saved_itineraries WHERE id = ?", (itinerary_id,))
        row = cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "destination": row["destination"],
                "start_date": row["start_date"],
                "days": row["days"],
                "travellers": row["travellers"],
                "budget": row["budget"],
                "itinerary_data": json.loads(row["itinerary_data"]),
                "created_at": row["created_at"],
            }
    return None


# ==============================================================================
# Agent Execution Log CRUD Functions
# ==============================================================================

def log_execution_step(
    session_id: str,
    step_number: int,
    phase: str,
    thought: Optional[str] = None,
    tool_name: Optional[str] = None,
    tool_input: Optional[Any] = None,
    tool_output: Optional[Any] = None,
    status: str = "SUCCESS",
    error_message: Optional[str] = None,
    db_path: Optional[str] = None,
) -> None:
    """Log an agent execution step in the audit table."""
    now = _get_utc_now()
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO execution_logs
            (session_id, step_number, phase, thought, tool_name, tool_input, tool_output, status, error_message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                step_number,
                phase,
                thought,
                tool_name,
                json.dumps(tool_input) if tool_input is not None else None,
                json.dumps(tool_output) if tool_output is not None else None,
                status,
                error_message,
                now,
            ),
        )
        conn.commit()


def get_session_logs(session_id: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all execution log steps for a specific planning session."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM execution_logs
            WHERE session_id = ?
            ORDER BY step_number ASC, id ASC
            """,
            (session_id,),
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row["id"],
                "session_id": row["session_id"],
                "step_number": row["step_number"],
                "phase": row["phase"],
                "thought": row["thought"],
                "tool_name": row["tool_name"],
                "tool_input": json.loads(row["tool_input"]) if row["tool_input"] else None,
                "tool_output": json.loads(row["tool_output"]) if row["tool_output"] else None,
                "status": row["status"],
                "error_message": row["error_message"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
