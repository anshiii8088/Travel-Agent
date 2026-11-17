"""Stage 1 Fake LLM Verification Suite (PRD Section 5.7: Requirements Testing Table).

Executes and verifies all 10 mandated test cases using the deterministic Fake LLM
completely offline without requiring an external API key or network access.
"""

import os
import tempfile
import pytest

from backend.agent.llm_provider import FakeLLMProvider, get_llm_provider
from backend.agent.loop import TravelPlannerAgent
from backend.agent.memory import MemoryManager
from backend.agent.safety import SafetyController
from backend.config import settings
from backend.database import init_db
from backend.models.travel import TravelPreference, TravelRequest


@pytest.fixture
def temp_db():
    """Create an isolated temporary SQLite database for testing."""
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


# ==============================================================================
# PRD Test Case 1: Valid Destination -> Generates an itinerary
# ==============================================================================
def test_case_01_valid_destination(temp_db):
    """PRD Test Case 1: Valid destination generates a complete day-by-day itinerary."""
    llm = FakeLLMProvider()
    request = llm.parse_user_intent("Plan a 3-day trip to Munnar within ₹8,000")

    agent = TravelPlannerAgent(db_path=temp_db)
    result = agent.run_planning_cycle(request)

    assert result.status == "COMPLETED"
    assert result.itinerary is not None
    assert result.itinerary.destination == "Munnar"
    assert len(result.itinerary.daily_schedule) == 3
    assert len(result.itinerary.hotels) >= 1
    assert result.itinerary.budget.total_estimated_cost > 0


# ==============================================================================
# PRD Test Case 2: Invalid Destination -> Requests correction
# ==============================================================================
def test_case_02_invalid_destination(temp_db):
    """PRD Test Case 2: Invalid or non-existent destination triggers correction request."""
    llm = FakeLLMProvider()
    request = llm.parse_user_intent("Plan a trip to nowhere_place_xyz123")

    agent = TravelPlannerAgent(db_path=temp_db)
    result = agent.run_planning_cycle(request)

    # Must fail gracefully and request correction without crashing
    assert result.status == "ERROR"
    assert result.error_message is not None
    assert "not recognized" in result.error_message or "valid destination" in result.error_message


# ==============================================================================
# PRD Test Case 3: Budget Too Low -> Suggests alternatives
# ==============================================================================
def test_case_03_budget_too_low(temp_db):
    """PRD Test Case 3: Budget lower than minimum estimated expenses triggers alternatives."""
    llm = FakeLLMProvider()
    # A tiny budget of ₹1,500 for a 3-day trip
    request = llm.parse_user_intent("Plan a 3-day trip to Munnar within ₹1,500")

    agent = TravelPlannerAgent(db_path=temp_db)
    result = agent.run_planning_cycle(request)

    assert result.status == "COMPLETED"
    assert result.itinerary is not None
    budget = result.itinerary.budget
    assert budget.is_over_budget is True
    assert budget.remaining_budget < 0
    assert len(budget.affordable_alternatives) >= 1
    # Must offer concrete saving alternatives
    assert any("Accommodation" in alt or "Transport" in alt for alt in budget.affordable_alternatives)


# ==============================================================================
# PRD Test Case 4: Weather API Failure -> Handles the error
# ==============================================================================
def test_case_04_weather_api_failure(temp_db):
    """PRD Test Case 4: Weather API outage is handled safely with labeled estimates."""
    llm = FakeLLMProvider()
    request = llm.parse_user_intent("Plan a 2-day trip to Munnar")

    agent = TravelPlannerAgent(db_path=temp_db)
    result = agent.run_planning_cycle(request, simulate_weather_failure=True)

    assert result.status == "COMPLETED"
    assert result.itinerary is not None
    assert len(result.itinerary.weather) == 2
    # Verify estimates are clearly flagged and never claimed as live verified
    for w in result.itinerary.weather:
        assert w.is_estimate is True
        assert "unverified" in w.recommendation or "estimate" in w.condition.lower()


# ==============================================================================
# PRD Test Case 5: Route API Failure -> Attempts recovery
# ==============================================================================
def test_case_05_route_api_failure(temp_db):
    """PRD Test Case 5: Route API failure attempts recovery using heuristic fallback."""
    llm = FakeLLMProvider()
    request = llm.parse_user_intent("Plan a 2-day trip to Munnar")

    agent = TravelPlannerAgent(db_path=temp_db)
    result = agent.run_planning_cycle(request, simulate_route_failure=True)

    assert result.status == "COMPLETED"
    assert result.itinerary is not None
    assert len(result.itinerary.routes) >= 1
    assert result.itinerary.routes[0].distance_km > 0


# ==============================================================================
# PRD Test Case 6: Previous Preference -> Recalls saved memory
# ==============================================================================
def test_case_06_previous_preference_recall(temp_db):
    """PRD Test Case 6: Recalls previous saved travel preferences into new tasks."""
    # Session 1: User indicates preferences
    mem = MemoryManager("session-1", db_path=temp_db)
    mem.save_preference("favorite_activities", ["Trekking", "Tea Tasting"])
    mem.save_preference("dietary_preferences", "Vegetarian")
    mem.save_preference("preferred_transport", "Cab")

    # Session 2: User says "Plan another trip for me"
    recalled = mem.recall_user_profile()
    assert "Trekking" in recalled.favorite_activities
    assert recalled.preferred_transport == "Cab"

    llm = FakeLLMProvider()
    req = llm.parse_user_intent("Plan a 3-day trip to Munnar", recalled_preferences=recalled.model_dump())

    assert "Trekking" in req.preferences.interests
    assert req.preferences.dietary_preferences == "Vegetarian"
    assert req.preferences.preferred_transport == "Cab"


# ==============================================================================
# PRD Test Case 7: More Than 10 Tool Steps -> Stops execution
# ==============================================================================
def test_case_07_step_limit_enforcement(temp_db):
    """PRD Test Case 7: Agent enforces strict 10 tool-step limit and halts safely."""
    llm = FakeLLMProvider()
    request = llm.parse_user_intent("Plan a 3-day trip to Munnar")

    # Override max steps to 2 to test cutoff boundary
    agent = TravelPlannerAgent(db_path=temp_db)
    result = agent.run_planning_cycle(request, max_steps_override=2)

    assert result.status == "LIMIT_REACHED"
    assert "Maximum execution step limit" in result.error_message
    assert result.steps_taken <= 2


# ==============================================================================
# PRD Test Case 8: Booking Request -> Asks for approval
# ==============================================================================
def test_case_08_booking_request_approval(temp_db):
    """PRD Test Case 8: Intercepts simulated booking action and requests human approval."""
    llm = FakeLLMProvider()
    request = llm.parse_user_intent("Book a 3-day trip to Munnar")

    agent = TravelPlannerAgent(db_path=temp_db)
    result = agent.run_planning_cycle(request, simulate_booking_action=True)

    assert result.status == "APPROVAL_REQUIRED"
    assert result.pending_approval_prompt is not None
    assert "Approval Required" in result.pending_approval_prompt


# ==============================================================================
# PRD Test Case 9: User Changes Destination -> Updates itinerary
# ==============================================================================
def test_case_09_user_changes_destination(temp_db):
    """PRD Test Case 9: Updates itinerary when user prompts destination change."""
    llm = FakeLLMProvider()
    request = llm.parse_user_intent("Plan a 2-day trip to Munnar within ₹10,000")

    agent = TravelPlannerAgent(db_path=temp_db)
    init_res = agent.run_planning_cycle(request)
    assert init_res.status == "COMPLETED"
    assert init_res.itinerary.destination == "Munnar"

    # User follow-up: "Change destination to Goa"
    modified = llm.modify_itinerary(init_res.itinerary, "Change destination to Goa")
    assert modified.destination == "Goa"
    assert "Goa" in modified.daily_schedule[0].title
    assert modified.budget.total_budget == 10000.0  # Preserves budget


# ==============================================================================
# PRD Test Case 10: Fake LLM Test -> Runs without a real LLM
# ==============================================================================
def test_case_10_fake_llm_standalone():
    """PRD Test Case 10: System operates completely offline without Gemini API key."""
    # Ensure MOCK_LLM is enabled
    assert settings.MOCK_LLM is True
    provider = get_llm_provider()
    assert isinstance(provider, FakeLLMProvider)

    # Intent parsing works offline
    req = provider.parse_user_intent("Plan a 2-day trip to Munnar within ₹5,000")
    assert req.destination == "Munnar"
    assert req.days == 2
    assert req.budget == 5000.0

    # Chat works offline
    ans = provider.answer_chat_query("What should I pack?")
    assert "pack" in ans.lower()


def test_phase_6_budget_reduction_percentage_and_indoor_swap(temp_db):
    """Phase 6 follow-up requests should handle percentage reductions and indoor swaps."""
    llm = FakeLLMProvider()
    request = llm.parse_user_intent("Plan a 3-day trip to Munnar within ₹10,000")

    agent = TravelPlannerAgent(db_path=temp_db)
    result = agent.run_planning_cycle(request)
    assert result.status == "COMPLETED"

    reduced = llm.modify_itinerary(result.itinerary, "reduce budget by 20%")
    assert reduced.budget.total_budget == pytest.approx(result.itinerary.budget.total_budget * 0.8)

    swapped = llm.modify_itinerary(result.itinerary, "swap day 2 for indoor museums")
    assert swapped.daily_schedule[1].title.lower().count("museum") >= 1 or "museum" in (swapped.daily_schedule[1].notes or "").lower()

