"""Agentic Think -> Act -> Look Execution Loop (PRD Section 5.1, 5.5, 5.6).

Implements the autonomous cycle:
1. Think: Analyze progress and decide next tool or synthesis step.
2. Act: Verify safety controls and execute tool with structured parameters.
3. Look: Inspect tool observation, validate constraints, and update memory.
"""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import uuid

from backend.agent.logger import AgentExecutionLogger
from backend.agent.memory import MemoryManager
from backend.agent.planner import ExecutionPlan, generate_travel_plan
from backend.agent.safety import SafetyActionType, SafetyController
from backend.models.travel import (
    Attraction,
    BudgetBreakdown,
    DayItinerary,
    HotelRecommendation,
    ItineraryResult,
    MealRecommendation,
    RouteSegment,
    TravelRequest,
    WeatherForecastItem,
)
from backend.tools import (
    BudgetCalculatorTool,
    DestinationSearchTool,
    RoutePlanningTool,
    WeatherTool,
)


class AgentLoopResult:
    """Outcome container returned by the Think -> Act -> Look engine."""

    def __init__(
        self,
        session_id: str,
        status: str,  # COMPLETED, APPROVAL_REQUIRED, LIMIT_REACHED, ERROR, CANCELLED
        itinerary: Optional[ItineraryResult] = None,
        error_message: Optional[str] = None,
        pending_approval_prompt: Optional[str] = None,
        steps_taken: int = 0,
        plan: Optional[ExecutionPlan] = None,
    ) -> None:
        self.session_id = session_id
        self.status = status
        self.itinerary = itinerary
        self.error_message = error_message
        self.pending_approval_prompt = pending_approval_prompt
        self.steps_taken = steps_taken
        self.plan = plan

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "steps_taken": self.steps_taken,
            "error_message": self.error_message,
            "pending_approval_prompt": self.pending_approval_prompt,
            "plan": self.plan.to_dict() if self.plan else None,
            "itinerary": self.itinerary.model_dump() if self.itinerary else None,
        }


class TravelPlannerAgent:
    """Autonomous travel planner coordinating Think -> Act -> Look cycles."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        max_steps: int = 10,
        db_path: Optional[str] = None,
    ) -> None:
        self.session_id = session_id or str(uuid.uuid4())
        self.db_path = db_path
        self.logger = AgentExecutionLogger(self.session_id, db_path=db_path)
        self.safety = SafetyController(max_steps=max_steps)
        self.memory = MemoryManager(self.session_id, db_path=db_path)

        # Initialize tools
        self.search_tool = DestinationSearchTool()
        self.weather_tool = WeatherTool()
        self.route_tool = RoutePlanningTool()
        self.budget_tool = BudgetCalculatorTool()

    def run_planning_cycle(
        self,
        request: TravelRequest,
        simulate_weather_failure: bool = False,
        simulate_route_failure: bool = False,
        simulate_booking_action: bool = False,
        max_steps_override: Optional[int] = None,
    ) -> AgentLoopResult:
        """Execute the end-to-end autonomous travel planning loop."""
        if max_steps_override is not None:
            self.safety.max_steps = max_steps_override

        # Phase 0: Recall long-term memory & persistent user profile
        recalled_profile = self.memory.recall_user_profile()
        recalled_dict = recalled_profile.model_dump()

        # Phase 1: Planning Before Acting (PRD Req 5)
        now_str = datetime.now(timezone.utc).isoformat()
        plan = generate_travel_plan(self.session_id, request, recalled_dict, created_at=now_str)
        self.logger.log_step(
            step_number=0,
            phase="PLAN",
            thought=f"Created structured 7-step plan for {request.days}-day trip to {request.destination}.",
            tool_name="pre_planner",
            tool_input=request.model_dump(),
            tool_output=plan.to_dict(),
            status="SUCCESS",
        )

        # Record learned preferences into long-term memory
        self.memory.learn_from_request(
            destination=request.destination,
            interests=request.preferences.interests,
            dietary=request.preferences.dietary_preferences,
            transport=request.preferences.preferred_transport,
        )

        # ======================================================================
        # Loop Cycle: Think -> Act -> Look (PRD Req 1)
        # ======================================================================

        # Step 1: Destination Search
        can_continue, limit_msg = self.safety.check_step_limit()
        if not can_continue:
            return self._handle_limit_reached(limit_msg, plan)

        step_num = self.safety.record_step()
        plan.mark_step_in_progress(2)

        # --- THINK ---
        thought_1 = f"Need to search attractions, hotels, and food for destination '{request.destination}' matching interests {request.preferences.interests}."
        self.logger.log_step(step_num, phase="THINK", thought=thought_1)

        # --- ACT ---
        act_search = self.search_tool.execute(
            destination=request.destination,
            interests=request.preferences.interests,
            budget_tier=request.preferences.travel_style,
            max_budget=request.budget,
        )

        # --- LOOK ---
        if not act_search.success:
            self.logger.log_step(
                step_num,
                phase="LOOK",
                thought=f"Destination search failed: {act_search.error}",
                tool_name=self.search_tool.name,
                tool_output=act_search.to_summary_dict(),
                status="ERROR",
                error_message=act_search.error,
            )
            return AgentLoopResult(
                session_id=self.session_id,
                status="ERROR",
                error_message=act_search.error,
                steps_taken=self.safety.current_step_count,
                plan=plan,
            )

        self.memory.store_finding("search_data", act_search.data)
        self.logger.log_step(
            step_num,
            phase="LOOK",
            thought=f"Found {len(act_search.data.get('attractions', []))} attractions, {len(act_search.data.get('hotels', []))} hotels.",
            tool_name=self.search_tool.name,
            tool_output=act_search.to_summary_dict(),
            status="SUCCESS",
        )
        plan.mark_step_completed(2, summary=f"Found {len(act_search.data.get('attractions', []))} attractions.")

        # Step 2: Weather Forecast
        can_continue, limit_msg = self.safety.check_step_limit()
        if not can_continue:
            return self._handle_limit_reached(limit_msg, plan)

        step_num = self.safety.record_step()
        plan.mark_step_in_progress(3)

        # --- THINK ---
        thought_2 = f"Retrieve weather forecasts for '{request.destination}' from {request.start_date} for {request.days} days."
        self.logger.log_step(step_num, phase="THINK", thought=thought_2)

        # --- ACT ---
        act_weather = self.weather_tool.execute(
            destination=request.destination,
            start_date=request.start_date,
            days=request.days,
            simulate_failure=simulate_weather_failure,
        )

        # --- LOOK ---
        self.memory.store_finding("weather_data", act_weather.data)
        weather_status = "RECOVERED" if act_weather.is_fallback else "SUCCESS"
        self.logger.log_step(
            step_num,
            phase="LOOK",
            thought=f"Weather retrieved. Fallback={act_weather.is_fallback}. Warnings={act_weather.warning}",
            tool_name=self.weather_tool.name,
            tool_output=act_weather.to_summary_dict(),
            status=weather_status,
            error_message=act_weather.warning,
        )
        plan.mark_step_completed(3, summary="Weather forecasts processed.")

        # Step 3: Route Planning
        can_continue, limit_msg = self.safety.check_step_limit()
        if not can_continue:
            return self._handle_limit_reached(limit_msg, plan)

        step_num = self.safety.record_step()
        plan.mark_step_in_progress(4)

        # --- THINK ---
        attraction_names = [a["name"] for a in act_search.data.get("attractions", [])[:4]]
        thought_3 = f"Calculate transit routes from origin '{request.origin}' to '{request.destination}' and between attractions: {attraction_names}."
        self.logger.log_step(step_num, phase="THINK", thought=thought_3)

        # --- ACT ---
        act_route = self.route_tool.execute(
            origin=request.origin,
            destination=request.destination,
            stops=attraction_names,
            travel_mode=request.preferences.preferred_transport or "Drive",
            simulate_failure=simulate_route_failure,
        )

        # --- LOOK ---
        self.memory.store_finding("route_data", act_route.data)
        route_status = "RECOVERED" if act_route.is_fallback else "SUCCESS"
        self.logger.log_step(
            step_num,
            phase="LOOK",
            thought=f"Route planning complete. Distance: {act_route.data.get('total_distance_km')} km.",
            tool_name=self.route_tool.name,
            tool_output=act_route.to_summary_dict(),
            status=route_status,
            error_message=act_route.warning,
        )
        plan.mark_step_completed(4, summary=f"Total distance: {act_route.data.get('total_distance_km')} km.")

        # Step 4: Budget Calculation
        can_continue, limit_msg = self.safety.check_step_limit()
        if not can_continue:
            return self._handle_limit_reached(limit_msg, plan)

        step_num = self.safety.record_step()
        plan.mark_step_in_progress(5)

        # Estimate expense components
        est_transport = act_route.data.get("total_estimated_fare", 2000.0)
        hotel_list = act_search.data.get("hotels", [])
        nightly_rate = hotel_list[0]["price_per_night"] if hotel_list else 2000.0
        est_lodging = nightly_rate * max(1, request.days - 1)
        est_food = 600.0 * request.days * request.travellers
        raw_attractions = act_search.data.get("attractions", [])
        est_activities = sum(a.get("estimated_cost", 0.0) for a in raw_attractions[:request.days * 2]) * request.travellers

        # --- THINK ---
        thought_4 = f"Calculate total expenses against user budget ₹{request.budget:,.2f}."
        self.logger.log_step(step_num, phase="THINK", thought=thought_4)

        # --- ACT ---
        act_budget = self.budget_tool.execute(
            total_budget=request.budget,
            transportation_cost=est_transport,
            accommodation_cost=est_lodging,
            food_cost=est_food,
            activity_cost=est_activities,
            travellers=request.travellers,
        )

        # --- LOOK ---
        self.memory.store_finding("budget_data", act_budget.data)
        is_over = act_budget.data.get("is_over_budget", False)
        look_budget_thought = (
            f"Budget variance checked: Over budget = {is_over}. Remaining: ₹{act_budget.data.get('remaining_budget')}."
        )
        self.logger.log_step(
            step_num,
            phase="LOOK",
            thought=look_budget_thought,
            tool_name=self.budget_tool.name,
            tool_output=act_budget.to_summary_dict(),
            status="SUCCESS",
        )
        plan.mark_step_completed(5, summary=f"Expense computed. Over budget: {is_over}.")

        # Step 5: Check Simulated Booking Action (Safety Approval Gate - PRD Req 6.A)
        if simulate_booking_action:
            can_continue, limit_msg = self.safety.check_step_limit()
            if not can_continue:
                return self._handle_limit_reached(limit_msg, plan)

            step_num = self.safety.record_step()
            decision = self.safety.evaluate_action(
                action_name="book_hotel",
                action_payload={"hotel": hotel_list[0]["name"] if hotel_list else "Selected Hotel", "cost": est_lodging},
            )

            if decision.requires_user_approval:
                self.logger.log_step(
                    step_num,
                    phase="SAFETY",
                    thought="Booking action intercepted by Safety Controller. Awaiting user approval.",
                    status="APPROVAL_REQUIRED",
                    error_message=decision.approval_prompt,
                )
                return AgentLoopResult(
                    session_id=self.session_id,
                    status="APPROVAL_REQUIRED",
                    pending_approval_prompt=decision.approval_prompt,
                    steps_taken=self.safety.current_step_count,
                    plan=plan,
                )

        # Step 6: Assemble Final Itinerary
        plan.mark_step_in_progress(7)
        final_itinerary = self._synthesize_final_itinerary(
            request=request,
            search_data=act_search.data,
            weather_data=act_weather.data,
            route_data=act_route.data,
            budget_data=act_budget.data,
            steps_count=self.safety.current_step_count,
        )
        plan.mark_step_completed(7, summary="Final itinerary successfully compiled.")

        self.logger.log_step(
            step_number=self.safety.current_step_count + 1,
            phase="LOOK",
            thought="Trip planning completed successfully. All constraints validated.",
            status="SUCCESS",
        )

        return AgentLoopResult(
            session_id=self.session_id,
            status="COMPLETED",
            itinerary=final_itinerary,
            steps_taken=self.safety.current_step_count,
            plan=plan,
        )

    def _handle_limit_reached(self, limit_msg: Optional[str], plan: ExecutionPlan) -> AgentLoopResult:
        """Handle execution step limit termination (PRD Requirement 6.B)."""
        msg = limit_msg or "Execution step limit reached."
        self.logger.log_step(
            step_number=self.safety.current_step_count,
            phase="SAFETY",
            thought="Step limit reached. Halting loop to prevent overrun.",
            status="LIMIT_REACHED",
            error_message=msg,
        )
        return AgentLoopResult(
            session_id=self.session_id,
            status="LIMIT_REACHED",
            error_message=msg,
            steps_taken=self.safety.current_step_count,
            plan=plan,
        )

    def _synthesize_final_itinerary(
        self,
        request: TravelRequest,
        search_data: Dict[str, Any],
        weather_data: Dict[str, Any],
        route_data: Dict[str, Any],
        budget_data: Dict[str, Any],
        steps_count: int,
    ) -> ItineraryResult:
        """Compile verified tool observations into the final ItineraryResult model."""
        daily_schedule: List[DayItinerary] = []
        raw_attractions = search_data.get("attractions", [])
        raw_hotels = search_data.get("hotels", [])
        raw_restaurants = search_data.get("restaurants", [])
        raw_forecasts = weather_data.get("forecasts", [])

        # Distribute attractions across days
        att_per_day = max(1, len(raw_attractions) // request.days)
        hotel_rec = HotelRecommendation(**raw_hotels[0]) if raw_hotels else None

        for day_idx in range(request.days):
            day_num = day_idx + 1
            start_i = day_idx * att_per_day
            end_i = start_i + att_per_day
            day_attractions_raw = raw_attractions[start_i:end_i] if start_i < len(raw_attractions) else raw_attractions[:1]

            day_attractions = [
                Attraction(
                    name=a["name"],
                    description=a["description"],
                    recommended_time=a.get("recommended_time", "10:00 AM - 01:00 PM"),
                    duration_hours=float(a.get("duration_hours", 2.5)),
                    location=a.get("location", request.destination),
                    activities=a.get("activities", []),
                    estimated_cost=float(a.get("estimated_cost", 0.0)),
                    rating=float(a.get("rating", 4.5)),
                )
                for a in day_attractions_raw
            ]

            # Choose dining
            rest_idx = day_idx % max(1, len(raw_restaurants))
            dining = [
                MealRecommendation(
                    meal_type="Lunch",
                    restaurant_name=raw_restaurants[rest_idx]["name"] if raw_restaurants else "Local Cafe",
                    cuisine=raw_restaurants[rest_idx].get("cuisine", "Regional") if raw_restaurants else "Regional",
                    location=raw_restaurants[rest_idx].get("location", request.destination) if raw_restaurants else request.destination,
                    estimated_cost=float(raw_restaurants[rest_idx].get("estimated_cost", 300.0)) if raw_restaurants else 300.0,
                    rating=float(raw_restaurants[rest_idx].get("rating", 4.3)) if raw_restaurants else 4.3,
                )
            ]

            day_cost = sum(a.estimated_cost for a in day_attractions) + sum(m.estimated_cost for m in dining)

            daily_schedule.append(
                DayItinerary(
                    day_number=day_num,
                    date=raw_forecasts[day_idx]["date"] if day_idx < len(raw_forecasts) else request.start_date,
                    title=f"Day {day_num}: Discovering {request.destination}",
                    attractions=day_attractions,
                    meals=dining,
                    hotel=hotel_rec,
                    day_total_cost=round(day_cost, 2),
                )
            )

        # Budget Breakdown
        bk = budget_data.get("breakdown", {})
        budget_obj = BudgetBreakdown(
            transportation_cost=bk.get("transportation_cost", 0.0),
            accommodation_cost=bk.get("accommodation_cost", 0.0),
            food_cost=bk.get("food_cost", 0.0),
            tickets_activities_cost=bk.get("activity_cost", 0.0),
            contingency_cost=bk.get("contingency_cost", 0.0),
            total_estimated_cost=budget_data.get("total_estimated_cost", 0.0),
            total_budget=budget_data.get("total_budget", request.budget),
            remaining_budget=budget_data.get("remaining_budget", 0.0),
            cost_per_person=budget_data.get("cost_per_person", 0.0),
            is_over_budget=budget_data.get("is_over_budget", False),
            affordable_alternatives=budget_data.get("affordable_alternatives", []),
        )

        # Weather Forecasts
        weather_items = [
            WeatherForecastItem(
                date=f["date"],
                destination=f["destination"],
                temperature_celsius=f["temperature_celsius"],
                condition=f["condition"],
                rain_probability_pct=f["rain_probability_pct"],
                is_estimate=f.get("is_estimate", False),
                recommendation=f.get("recommendation"),
            )
            for f in raw_forecasts
        ]

        # Routes
        route_segments = [
            RouteSegment(
                from_location=s["from_location"],
                to_location=s["to_location"],
                travel_mode=s.get("travel_mode", "Drive"),
                distance_km=float(s["distance_km"]),
                duration_minutes=int(s["duration_minutes"]),
                estimated_fare=float(s.get("estimated_fare", 0.0)),
            )
            for s in route_data.get("segments", [])
        ]

        return ItineraryResult(
            itinerary_id=str(uuid.uuid4()),
            destination=request.destination,
            origin=request.origin,
            start_date=request.start_date,
            days=request.days,
            travellers=request.travellers,
            currency=request.currency,
            overview=search_data.get("overview", f"Customized trip to {request.destination}"),
            daily_schedule=daily_schedule,
            hotels=[HotelRecommendation(**h) for h in raw_hotels[:3]],
            budget=budget_obj,
            weather=weather_items,
            routes=route_segments,
            execution_steps_count=steps_count,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

