"""Travel and Itinerary domain models and schemas (FR-01 to FR-08)."""

from datetime import date
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TravelPreference(BaseModel):
    """User travel preferences for recommendation matching."""
    travel_style: str = Field(default="Balanced", description="e.g. Budget, Luxury, Adventure, Relaxed, Cultural")
    interests: List[str] = Field(default_factory=list, description="e.g. ['Nature', 'Beaches', 'History', 'Food']")
    dietary_preferences: Optional[str] = Field(default="Any", description="e.g. Vegetarian, Non-Vegetarian, Vegan")
    preferred_transport: Optional[str] = Field(default="Public / Car", description="e.g. Cab, Bus, Train, Rental")


class TravelRequest(BaseModel):
    """Input payload submitted by the user (FR-01)."""
    origin: str = Field(..., description="Starting location, e.g. Kochi, Bangalore")
    destination: str = Field(..., description="Travel destination, e.g. Munnar, Goa")
    start_date: str = Field(..., description="Travel start date in YYYY-MM-DD")
    days: int = Field(..., ge=1, le=14, description="Number of travel days")
    travellers: int = Field(default=1, ge=1, le=50, description="Total number of travellers")
    budget: float = Field(..., gt=0, description="Total budget in specified currency (e.g. INR)")
    currency: str = Field(default="INR", description="Currency symbol/code")
    preferences: TravelPreference = Field(default_factory=TravelPreference)
    special_requests: Optional[str] = Field(default=None, description="Additional custom instructions")


class Attraction(BaseModel):
    """Single tourist attraction or activity (FR-03)."""
    name: str
    description: str
    recommended_time: str = Field(..., description="e.g. 09:00 AM - 11:30 AM")
    duration_hours: float = Field(..., description="Estimated duration in hours")
    location: str
    activities: List[str] = Field(default_factory=list)
    estimated_cost: float = Field(default=0.0, description="Entry or activity cost per person")
    distance_from_prev_km: Optional[float] = Field(default=0.0, description="Distance from previous stop")
    rating: Optional[float] = Field(default=4.5)


class MealRecommendation(BaseModel):
    """Restaurant / dining recommendation (FR-06)."""
    meal_type: str = Field(..., description="Breakfast, Lunch, or Dinner")
    restaurant_name: str
    cuisine: str
    location: str
    estimated_cost: float
    rating: float = 4.2


class HotelRecommendation(BaseModel):
    """Accommodation recommendation (FR-05)."""
    name: str
    location: str
    price_per_night: float
    rating: float = 4.3
    amenities: List[str] = Field(default_factory=list)
    total_lodging_cost: float = 0.0


class DayItinerary(BaseModel):
    """Day-by-day travel schedule (FR-03)."""
    day_number: int
    date: str
    title: str
    attractions: List[Attraction] = Field(default_factory=list)
    meals: List[MealRecommendation] = Field(default_factory=list)
    hotel: Optional[HotelRecommendation] = None
    day_total_cost: float = 0.0
    notes: Optional[str] = None


class BudgetBreakdown(BaseModel):
    """Expense breakdown calculated by Budget Agent (FR-04)."""
    transportation_cost: float = 0.0
    accommodation_cost: float = 0.0
    food_cost: float = 0.0
    tickets_activities_cost: float = 0.0
    contingency_cost: float = 0.0
    total_estimated_cost: float = 0.0
    total_budget: float = 0.0
    remaining_budget: float = 0.0
    cost_per_person: float = 0.0
    is_over_budget: bool = False
    affordable_alternatives: List[str] = Field(default_factory=list)


class WeatherForecastItem(BaseModel):
    """Weather information for a destination day (FR-07)."""
    date: str
    destination: str
    temperature_celsius: float
    condition: str
    rain_probability_pct: int
    is_estimate: bool = False
    recommendation: Optional[str] = None


class RouteSegment(BaseModel):
    """Route information between locations (FR-08)."""
    from_location: str
    to_location: str
    travel_mode: str = "Drive"
    distance_km: float
    duration_minutes: int
    estimated_fare: float = 0.0


class ItineraryResult(BaseModel):
    """Complete personalized travel plan response."""
    itinerary_id: str
    destination: str
    origin: str
    start_date: str
    days: int
    travellers: int
    currency: str = "INR"
    overview: str
    daily_schedule: List[DayItinerary] = Field(default_factory=list)
    hotels: List[HotelRecommendation] = Field(default_factory=list)
    budget: BudgetBreakdown
    weather: List[WeatherForecastItem] = Field(default_factory=list)
    routes: List[RouteSegment] = Field(default_factory=list)
    execution_steps_count: int = 0
    created_at: str

