"""Planning module (PRD Requirement 5: Planning Before Acting).

Generates a structured multi-step execution plan before executing any external tools.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.models.travel import TravelRequest


class PlanStep(BaseModel):
    """Single step in the structured pre-execution plan."""
    step_id: int
    title: str
    description: str
    tool_needed: Optional[str] = None
    status: str = "PENDING"  # PENDING, IN_PROGRESS, COMPLETED, SKIPPED, FAILED
    result_summary: Optional[str] = None


class ExecutionPlan(BaseModel):
    """Complete structured pre-execution plan created before tool execution."""
    session_id: str
    destination: str
    total_steps: int
    steps: List[PlanStep] = Field(default_factory=list)
    created_at: str

    def mark_step_in_progress(self, step_id: int) -> None:
        for s in self.steps:
            if s.step_id == step_id:
                s.status = "IN_PROGRESS"
                break

    def mark_step_completed(self, step_id: int, summary: Optional[str] = None) -> None:
        for s in self.steps:
            if s.step_id == step_id:
                s.status = "COMPLETED"
                s.result_summary = summary
                break

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "destination": self.destination,
            "total_steps": self.total_steps,
            "steps": [s.model_dump() for s in self.steps],
            "created_at": self.created_at,
        }


def generate_travel_plan(
    session_id: str,
    request: TravelRequest,
    recalled_preferences: Optional[Dict[str, Any]] = None,
    created_at: str = "",
) -> ExecutionPlan:
    """Create a structured execution plan according to PRD Section 5.5.
    
    Divides the task into 7 structured steps:
    1. Understand travel preferences & recall memory
    2. Search tourist attractions, hotels, and restaurants
    3. Retrieve destination weather information
    4. Calculate routes, distances, and travel times
    5. Calculate and optimize estimated expenses
    6. Verify safety constraints & booking approvals
    7. Generate and present final personalized itinerary
    """
    pref_notes = ""
    if recalled_preferences:
        pref_notes = f" (incorporating saved preferences: {list(recalled_preferences.keys())})"

    steps = [
        PlanStep(
            step_id=1,
            title="Understand Travel Preferences",
            description=f"Analyze {request.days}-day trip to {request.destination} with budget ₹{request.budget:,.2f}{pref_notes}.",
            tool_needed=None,
        ),
        PlanStep(
            step_id=2,
            title="Search Destination Attractions & Amenities",
            description=f"Discover tourist spots, hotels, and restaurants in {request.destination} matching interests: {request.preferences.interests or 'Sightseeing'}.",
            tool_needed="destination_search",
        ),
        PlanStep(
            step_id=3,
            title="Check Weather Conditions",
            description=f"Retrieve weather forecasts and rain probabilities in {request.destination} starting {request.start_date}.",
            tool_needed="weather_info",
        ),
        PlanStep(
            step_id=4,
            title="Plan Routes & Calculate Travel Distances",
            description=f"Map transit paths from {request.origin} to {request.destination} and between chosen attractions.",
            tool_needed="route_planning",
        ),
        PlanStep(
            step_id=5,
            title="Calculate & Optimize Budget",
            description=f"Calculate itemized expenses across transport, lodging, food, and activities against budget ₹{request.budget:,.2f}.",
            tool_needed="budget_calculator",
        ),
        PlanStep(
            step_id=6,
            title="Safety & Approval Verification",
            description="Verify step limit boundaries and confirm human approval gates for any transactional actions.",
            tool_needed=None,
        ),
        PlanStep(
            step_id=7,
            title="Assemble Final Itinerary",
            description=f"Synthesize verified observations into a day-by-day itinerary with maps and cost breakdown for {request.destination}.",
            tool_needed=None,
        ),
    ]

    return ExecutionPlan(
        session_id=session_id,
        destination=request.destination,
        total_steps=len(steps),
        steps=steps,
        created_at=created_at,
    )

