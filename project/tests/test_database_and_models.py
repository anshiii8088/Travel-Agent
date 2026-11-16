"""Unit tests for Phase 2: Domain Models and SQLite Storage Layer."""

import os
import tempfile
import pytest
from pydantic import ValidationError

from backend.models.travel import (
    TravelPreference,
    TravelRequest,
    Attraction,
    MealRecommendation,
    HotelRecommendation,
    DayItinerary,
    BudgetBreakdown,
    WeatherForecastItem,
    RouteSegment,
    ItineraryResult,
)
from backend.models.memory import (
    UserPreferenceItem,
    UserPreferencesProfile,
    ShortTermMemory,
)
from backend.models.execution_log import AgentStepLog
from backend.database import (
    init_db,
    set_preference,
    get_preference,
    get_all_preferences,
    delete_preference,
    clear_all_preferences,
    save_itinerary,
    get_itinerary,
    log_execution_step,
    get_session_logs,
)


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database file for isolated testing."""
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
# Model Tests
# ==============================================================================

def test_travel_request_valid():
    """Test valid TravelRequest creation (FR-01)."""
    req = TravelRequest(
        origin="Kochi",
        destination="Munnar",
        start_date="2026-12-01",
        days=3,
        travellers=2,
        budget=12000.0,
        preferences=TravelPreference(
            travel_style="Nature",
            interests=["Tea Gardens", "Trekking"],
            dietary_preferences="Vegetarian",
        ),
    )
    assert req.destination == "Munnar"
    assert req.days == 3
    assert req.budget == 12000.0
    assert req.preferences.dietary_preferences == "Vegetarian"


def test_travel_request_invalid_budget():
    """Test that non-positive budget fails validation."""
    with pytest.raises(ValidationError):
        TravelRequest(
            origin="Kochi",
            destination="Munnar",
            start_date="2026-12-01",
            days=3,
            travellers=2,
            budget=-500.0,
        )


def test_travel_request_invalid_days():
    """Test that days <= 0 or > 14 fails validation."""
    with pytest.raises(ValidationError):
        TravelRequest(
            origin="Kochi",
            destination="Munnar",
            start_date="2026-12-01",
            days=0,
            travellers=1,
            budget=5000.0,
        )


def test_itinerary_result_structure():
    """Test ItineraryResult structure and nesting (FR-03, FR-04)."""
    itinerary = ItineraryResult(
        itinerary_id="test-123",
        destination="Munnar",
        origin="Kochi",
        start_date="2026-12-01",
        days=1,
        travellers=1,
        overview="A wonderful 1-day exploration of Munnar's tea country.",
        daily_schedule=[
            DayItinerary(
                day_number=1,
                date="2026-12-01",
                title="Tea Gardens & Scenic Views",
                attractions=[
                    Attraction(
                        name="Tea Museum",
                        description="Historical tea processing demonstration",
                        recommended_time="09:00 AM - 11:00 AM",
                        duration_hours=2.0,
                        location="Nullatanni, Munnar",
                        activities=["Tea Tasting", "Museum Tour"],
                        estimated_cost=250.0,
                    )
                ],
                meals=[
                    MealRecommendation(
                        meal_type="Lunch",
                        restaurant_name="Rapsy Restaurant",
                        cuisine="Kerala Traditional",
                        location="Main Bazaar",
                        estimated_cost=300.0,
                    )
                ],
                day_total_cost=550.0,
            )
        ],
        hotels=[
            HotelRecommendation(
                name="Munnar Hill Resort",
                location="Chithirapuram",
                price_per_night=2500.0,
                rating=4.5,
                total_lodging_cost=2500.0,
            )
        ],
        budget=BudgetBreakdown(
            transportation_cost=1500.0,
            accommodation_cost=2500.0,
            food_cost=900.0,
            tickets_activities_cost=500.0,
            contingency_cost=600.0,
            total_estimated_cost=6000.0,
            total_budget=8000.0,
            remaining_budget=2000.0,
            cost_per_person=6000.0,
            is_over_budget=False,
        ),
        weather=[
            WeatherForecastItem(
                date="2026-12-01",
                destination="Munnar",
                temperature_celsius=19.5,
                condition="Pleasant & Misty",
                rain_probability_pct=15,
            )
        ],
        routes=[
            RouteSegment(
                from_location="Kochi",
                to_location="Munnar",
                distance_km=125.0,
                duration_minutes=240,
                estimated_fare=1500.0,
            )
        ],
        created_at="2026-11-11T12:00:00",
    )
    assert itinerary.itinerary_id == "test-123"
    assert len(itinerary.daily_schedule) == 1
    assert itinerary.budget.remaining_budget == 2000.0
    assert not itinerary.budget.is_over_budget


# ==============================================================================
# Database Persistence Tests (Req 4, Req 6.C)
# ==============================================================================

def test_preference_crud(temp_db):
    """Test saving, retrieving, updating, and clearing persistent preferences."""
    # 1. Initially empty
    assert get_preference("travel_style", db_path=temp_db) is None

    # 2. Set preference
    set_preference("travel_style", "Nature & Adventure", category="style", db_path=temp_db)
    set_preference("dietary", "Vegetarian", category="food", db_path=temp_db)
    set_preference("favorite_destinations", ["Munnar", "Goa", "Manali"], category="destination", db_path=temp_db)

    # 3. Retrieve
    assert get_preference("travel_style", db_path=temp_db) == "Nature & Adventure"
    assert get_preference("dietary", db_path=temp_db) == "Vegetarian"
    dests = get_preference("favorite_destinations", db_path=temp_db)
    assert isinstance(dests, list)
    assert "Munnar" in dests

    # 4. Get all
    all_prefs = get_all_preferences(db_path=temp_db)
    assert len(all_prefs) == 3
    assert all_prefs["travel_style"]["value"] == "Nature & Adventure"
    assert all_prefs["travel_style"]["category"] == "style"

    # 5. Update preference (upsert)
    set_preference("travel_style", "Cultural & Heritage", category="style", db_path=temp_db)
    assert get_preference("travel_style", db_path=temp_db) == "Cultural & Heritage"

    # 6. Delete preference
    deleted = delete_preference("dietary", db_path=temp_db)
    assert deleted is True
    assert get_preference("dietary", db_path=temp_db) is None

    # 7. Clear all preferences
    clear_all_preferences(db_path=temp_db)
    assert len(get_all_preferences(db_path=temp_db)) == 0


def test_itinerary_persistence(temp_db):
    """Test saving and retrieving complete itineraries."""
    itinerary_payload = {
        "destination": "Goa",
        "highlights": ["Calangute Beach", "Fort Aguada"],
        "budget_total": 15000,
    }
    save_itinerary(
        itinerary_id="goa-trip-001",
        destination="Goa",
        start_date="2026-11-20",
        days=4,
        travellers=2,
        budget=15000.0,
        itinerary_data=itinerary_payload,
        db_path=temp_db,
    )

    saved = get_itinerary("goa-trip-001", db_path=temp_db)
    assert saved is not None
    assert saved["id"] == "goa-trip-001"
    assert saved["destination"] == "Goa"
    assert saved["days"] == 4
    assert saved["itinerary_data"]["highlights"] == ["Calangute Beach", "Fort Aguada"]

    # Non-existent itinerary
    assert get_itinerary("non-existent-id", db_path=temp_db) is None


def test_execution_logging(temp_db):
    """Test agent execution audit logging (Think -> Act -> Look trace)."""
    session = "session-test-456"

    # Log Step 1: PLAN
    log_execution_step(
        session_id=session,
        step_number=1,
        phase="PLAN",
        thought="Identified destination Munnar, 3 days, budget 8000.",
        status="SUCCESS",
        db_path=temp_db,
    )

    # Log Step 2: ACT (Tool call)
    log_execution_step(
        session_id=session,
        step_number=2,
        phase="ACT",
        tool_name="destination_search",
        tool_input={"destination": "Munnar", "interests": ["Nature"]},
        tool_output={"attractions_found": 5},
        status="SUCCESS",
        db_path=temp_db,
    )

    # Log Step 3: LOOK (Observation)
    log_execution_step(
        session_id=session,
        step_number=3,
        phase="LOOK",
        thought="5 attractions retrieved. Moving to weather forecast.",
        status="SUCCESS",
        db_path=temp_db,
    )

    logs = get_session_logs(session, db_path=temp_db)
    assert len(logs) == 3
    assert logs[0]["phase"] == "PLAN"
    assert logs[1]["phase"] == "ACT"
    assert logs[1]["tool_name"] == "destination_search"
    assert logs[1]["tool_input"]["destination"] == "Munnar"
    assert logs[2]["phase"] == "LOOK"
