"""Unit tests for Phase 4: Agent Core Engine (Think -> Act -> Look, Planning, Safety, Memory)."""

import os
import tempfile
import pytest

from backend.agent import (
    AgentExecutionLogger,
    AgentLoopResult,
    ExecutionPlan,
    MemoryManager,
    PlanStep,
    SafetyActionType,
    SafetyController,
    TravelPlannerAgent,
    generate_travel_plan,
    sanitize_data,
)
from backend.database import init_db
from backend.models.travel import TravelPreference, TravelRequest


@pytest.fixture
def temp_db():
    """Create an isolated temporary SQLite database."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(db_path=path)
    yield path
    import gc
    gc.collect()
    try:
        if os.path.exists(path):
            os.remove(path)
    except PermissionError:
        pass


@pytest.fixture
def sample_request():
    return TravelRequest(
        origin="Kochi",
        destination="Munnar",
        start_date="2026-12-01",
        days=3,
        travellers=2,
        budget=10000.0,
        preferences=TravelPreference(
            travel_style="Nature",
            interests=["Tea Gardens", "Waterfalls"],
            dietary_preferences="Vegetarian",
        ),
    )


# ==============================================================================
# 1. Planning Before Acting Tests (PRD Requirement 5)
# ==============================================================================

def test_pre_execution_planning(sample_request):
    """Verify structured multi-step plan is generated prior to tool actions."""
    plan = generate_travel_plan("session-test-plan", sample_request)
    assert isinstance(plan, ExecutionPlan)
    assert plan.total_steps == 7
    assert plan.steps[0].title == "Understand Travel Preferences"
    assert plan.steps[1].tool_needed == "destination_search"
    assert plan.steps[2].tool_needed == "weather_info"
    assert plan.steps[3].tool_needed == "route_planning"
    assert plan.steps[4].tool_needed == "budget_calculator"
    assert plan.steps[5].title == "Safety & Approval Verification"
    assert plan.steps[6].title == "Assemble Final Itinerary"


# ==============================================================================
# 2. Safety Controller & Approval Gate Tests (PRD Requirement 6)
# ==============================================================================

def test_safety_step_limit_enforcement():
    """Verify max 10 steps cap halts execution."""
    safety = SafetyController(max_steps=3)
    assert safety.check_step_limit()[0] is True
    safety.record_step()  # 1
    safety.record_step()  # 2
    safety.record_step()  # 3
    can_continue, reason = safety.check_step_limit()
    assert can_continue is False
    assert "limit (3) reached" in reason


def test_safety_sensitive_action_requires_approval():
    """Verify booking actions require human authorization (Req 6.A)."""
    safety = SafetyController()
    decision = safety.evaluate_action("book_hotel", {"hotel": "Tea County", "cost": 3000})
    assert decision.requires_user_approval is True
    assert decision.allowed_to_proceed is False
    assert "Approval Required" in decision.approval_prompt

    # Safe read-only actions proceed without approval
    safe_decision = safety.evaluate_action("destination_search")
    assert safe_decision.requires_user_approval is False
    assert safe_decision.allowed_to_proceed is True


def test_safety_approval_grant():
    """Verify granting approval allows sensitive action to proceed."""
    safety = SafetyController()
    safety.grant_approval("book_hotel")
    decision = safety.evaluate_action("book_hotel")
    assert decision.allowed_to_proceed is True


def test_safety_user_cancellation():
    """Verify task cancellation immediately blocks further actions."""
    safety = SafetyController()
    safety.cancel_task()
    can_continue, reason = safety.check_step_limit()
    assert can_continue is False
    assert "cancelled by the user" in reason


# ==============================================================================
# 3. Execution Logger & Data Sanitization Tests (PRD Requirement 6.C)
# ==============================================================================

def test_logger_sanitization():
    """Verify sensitive tokens and keys are redacted from logs."""
    raw_payload = {
        "api_key": "AIzaSyD-secret-1234567890abcdef",
        "user_query": "Find hotels in Munnar",
        "auth_token": "bearer xyz987",
        "nested": {
            "credit_card": "4111 2222 3333 4444",
            "password": "SuperSecretPassword123!",
        },
    }
    sanitized = sanitize_data(raw_payload)
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["auth_token"] == "[REDACTED]"
    assert sanitized["nested"]["password"] == "[REDACTED]"
    assert sanitized["user_query"] == "Find hotels in Munnar"


def test_logger_execution_recording(temp_db):
    """Verify logger writes Think-Act-Look entries into SQLite."""
    logger = AgentExecutionLogger("session-log-test", db_path=temp_db)
    logger.log_step(1, phase="THINK", thought="Analyzing preferences.")
    logger.log_step(2, phase="ACT", tool_name="destination_search", tool_output={"status": "ok"})
    logger.log_step(3, phase="LOOK", thought="Attractions retrieved successfully.")

    logs = logger.get_logs()
    assert len(logs) == 3
    assert logs[0]["phase"] == "THINK"
    assert logs[1]["phase"] == "ACT"
    assert logs[2]["phase"] == "LOOK"


# ==============================================================================
# 4. Memory Manager Tests (PRD Requirement 4)
# ==============================================================================

def test_memory_profile_persistence(temp_db):
    """Verify user preferences are stored and recalled across tasks."""
    mem = MemoryManager("session-mem-test", db_path=temp_db)
    mem.learn_from_request(
        destination="Munnar",
        interests=["Trekking", "Tea Tasting"],
        dietary="Vegetarian",
        transport="Cab",
    )

    profile = mem.recall_user_profile()
    assert "Munnar" in profile.preferred_destinations
    assert "Trekking" in profile.favorite_activities
    assert "Vegetarian" in profile.preferred_food_types
    assert profile.preferred_transport == "Cab"


def test_database_initializes_automatically_on_first_use():
    """The database schema should be created automatically when first used without explicit init_db()."""
    db_path = os.path.join(tempfile.gettempdir(), "travel_planner_autoinit_test.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    mem = MemoryManager("auto-init-session", db_path=db_path)
    profile = mem.recall_user_profile()
    assert profile.preferred_destinations == []
    assert isinstance(profile.favorite_activities, list)

    if os.path.exists(db_path):
        os.remove(db_path)


# ==============================================================================
# 5. Think -> Act -> Look Cycle Integration Tests (PRD Requirement 1)
# ==============================================================================

def test_agent_full_planning_cycle(sample_request, temp_db):
    """Verify end-to-end execution of Think -> Act -> Look planning loop."""
    agent = TravelPlannerAgent(session_id="agent-run-001", db_path=temp_db)
    result = agent.run_planning_cycle(sample_request)

    assert result.status == "COMPLETED"
    assert result.itinerary is not None
    assert result.itinerary.destination == "Munnar"
    assert len(result.itinerary.daily_schedule) == 3
    assert result.itinerary.budget.total_budget == 10000.0
    assert result.steps_taken >= 4

    # Verify execution logs recorded Think -> Act -> Look steps
    logs = agent.logger.get_logs()
    phases = [l["phase"] for l in logs]
    assert "PLAN" in phases
    assert "THINK" in phases
    assert "LOOK" in phases


def test_agent_weather_failure_handling(sample_request, temp_db):
    """Verify loop handles Weather API failure gracefully (PRD Test Case 4)."""
    agent = TravelPlannerAgent(session_id="agent-run-weather-err", db_path=temp_db)
    result = agent.run_planning_cycle(sample_request, simulate_weather_failure=True)

    assert result.status == "COMPLETED"
    assert result.itinerary is not None
    # Weather items should have is_estimate = True
    assert any(w.is_estimate for w in result.itinerary.weather)


def test_agent_route_failure_handling(sample_request, temp_db):
    """Verify loop recovers from routing API outage (PRD Test Case 5)."""
    agent = TravelPlannerAgent(session_id="agent-run-route-err", db_path=temp_db)
    result = agent.run_planning_cycle(sample_request, simulate_route_failure=True)

    assert result.status == "COMPLETED"
    assert result.itinerary is not None
    assert len(result.itinerary.routes) >= 1


def test_agent_booking_approval_gate(sample_request, temp_db):
    """Verify loop halts and requests confirmation on booking action (PRD Test Case 8)."""
    agent = TravelPlannerAgent(session_id="agent-run-booking", db_path=temp_db)
    result = agent.run_planning_cycle(sample_request, simulate_booking_action=True)

    assert result.status == "APPROVAL_REQUIRED"
    assert "Approval Required" in result.pending_approval_prompt


def test_agent_step_limit_halt(sample_request, temp_db):
    """Verify loop stops when max step limit reached (PRD Test Case 7)."""
    # Restrict max steps to 2
    agent = TravelPlannerAgent(session_id="agent-run-limit", max_steps=2, db_path=temp_db)
    result = agent.run_planning_cycle(sample_request, max_steps_override=2)

    assert result.status == "LIMIT_REACHED"
    assert "Maximum execution step limit" in result.error_message

