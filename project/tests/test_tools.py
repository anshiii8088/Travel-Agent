"""Unit tests for Phase 3: External Tool Implementations with Error Recovery (Req 2 & 3)."""

import pytest
from backend.tools import (
    DestinationSearchTool,
    WeatherTool,
    RoutePlanningTool,
    BudgetCalculatorTool,
)


# ==============================================================================
# Tool 1: Destination Search Tool Tests
# ==============================================================================

def test_destination_search_valid():
    """Test searching a curated destination (Munnar)."""
    tool = DestinationSearchTool()
    res = tool.execute(destination="Munnar", interests=["Nature", "Tea Gardens"])

    assert res.success is True
    assert res.data["destination"] == "Munnar"
    assert len(res.data["attractions"]) >= 3
    assert len(res.data["hotels"]) >= 1
    assert len(res.data["restaurants"]) >= 1

    # Check attraction attributes
    first_att = res.data["attractions"][0]
    assert "name" in first_att
    assert "estimated_cost" in first_att
    assert "recommended_time" in first_att


def test_destination_search_invalid():
    """Test invalid destination detection (PRD Test Case 2)."""
    tool = DestinationSearchTool()
    res = tool.execute(destination="xyz_unknown_123")

    assert res.success is False
    assert "not recognized" in res.error or "valid destination" in res.error


def test_destination_search_fallback():
    """Test general valid city fallback synthesis."""
    tool = DestinationSearchTool()
    res = tool.execute(destination="Shimla", interests=["Sightseeing"])

    assert res.success is True
    assert res.is_fallback is True
    assert res.data["destination"] == "Shimla"
    assert len(res.data["attractions"]) >= 2


# ==============================================================================
# Tool 2: Weather Tool Tests
# ==============================================================================

def test_weather_tool_valid():
    """Test valid weather lookup for 3 days."""
    tool = WeatherTool()
    res = tool.execute(destination="Munnar", start_date="2026-12-01", days=3)

    assert res.success is True
    assert res.data["days"] == 3
    forecasts = res.data["forecasts"]
    assert len(forecasts) == 3
    assert forecasts[0]["date"] == "2026-12-01"
    assert "temperature_celsius" in forecasts[0]
    assert "rain_probability_pct" in forecasts[0]
    assert forecasts[0]["is_estimate"] is False


def test_weather_tool_failure_recovery():
    """Test weather tool failure recovery and labeled estimates (PRD Test Case 4)."""
    tool = WeatherTool()
    res = tool.execute(
        destination="Munnar",
        start_date="2026-12-01",
        days=2,
        simulate_failure=True,
    )

    # Must recover gracefully instead of crashing
    assert res.success is True
    assert res.is_estimate is True
    assert res.is_fallback is True
    assert res.retries_attempted == 2
    assert "failed after 2 retries" in res.warning
    assert res.data["live_weather_available"] is False
    assert res.data["forecasts"][0]["is_estimate"] is True


# ==============================================================================
# Tool 3: Route Planning Tool Tests
# ==============================================================================

def test_route_planning_valid():
    """Test route planning between Kochi and Munnar with stops."""
    tool = RoutePlanningTool()
    res = tool.execute(
        origin="Kochi",
        destination="Munnar",
        stops=["Tea Museum", "Mattupetty Dam"],
        travel_mode="Drive",
    )

    assert res.success is True
    assert res.data["total_distance_km"] > 0
    assert res.data["total_duration_minutes"] > 0
    assert res.data["total_estimated_fare"] > 0
    assert len(res.data["segments"]) >= 2


def test_route_planning_failure_recovery():
    """Test route planning API failure recovery (PRD Test Case 5)."""
    tool = RoutePlanningTool()
    res = tool.execute(
        origin="Kochi",
        destination="Munnar",
        travel_mode="Drive",
        simulate_failure=True,
    )

    # Must recover and return estimate
    assert res.success is True
    assert res.is_fallback is True
    assert res.is_estimate is True
    assert res.data["live_routing_available"] is False
    assert res.data["total_distance_km"] > 0


# ==============================================================================
# Tool 4: Budget Calculator Tool Tests
# ==============================================================================

def test_budget_calculator_within_budget():
    """Test trip expenses fitting within budget."""
    tool = BudgetCalculatorTool()
    res = tool.execute(
        total_budget=10000.0,
        transportation_cost=2500.0,
        accommodation_cost=3000.0,
        food_cost=1500.0,
        activity_cost=800.0,
        travellers=2,
    )

    assert res.success is True
    assert res.data["is_over_budget"] is False
    assert res.data["remaining_budget"] > 0
    assert res.data["cost_per_person"] > 0
    assert len(res.data["affordable_alternatives"]) == 0


def test_budget_calculator_over_budget_alternatives():
    """Test budget exceeded generates actionable alternatives (PRD Test Case 3)."""
    tool = BudgetCalculatorTool()
    res = tool.execute(
        total_budget=5000.0,
        transportation_cost=3500.0,
        accommodation_cost=4000.0,
        food_cost=2000.0,
        activity_cost=1000.0,
        travellers=1,
    )

    assert res.success is True
    assert res.data["is_over_budget"] is True
    assert res.data["remaining_budget"] < 0
    # Must propose concrete alternatives
    alternatives = res.data["affordable_alternatives"]
    assert len(alternatives) >= 2
    assert any("Accommodation" in a for a in alternatives)
    assert any("Transport" in a for a in alternatives)

