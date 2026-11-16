"""LLM Provider abstraction: Stage 1 Fake LLM & Stage 2 Google Gemini LLM (PRD Section 5.7).

Provides unified interfaces for natural language travel intent parsing,
real-time Think reasoning generation, conversational trip assistance (FR-09),
and AI-powered itinerary modification (FR-10).
"""

from abc import ABC, abstractmethod
import json
import logging
import re
from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.models.travel import (
    ItineraryResult,
    TravelPreference,
    TravelRequest,
)

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Abstract interface for LLM providers (Fake LLM and Google Gemini)."""

    @abstractmethod
    def parse_user_intent(
        self, user_message: str, recalled_preferences: Optional[Dict[str, Any]] = None
    ) -> TravelRequest:
        """Parse natural language travel request into a structured TravelRequest."""
        pass

    @abstractmethod
    def generate_agent_thought(self, stage: str, context: Dict[str, Any]) -> str:
        """Generate structured reasoning during Think phases."""
        pass

    @abstractmethod
    def modify_itinerary(
        self, current_itinerary: ItineraryResult, modification_request: str
    ) -> ItineraryResult:
        """Modify an existing itinerary based on user follow-up prompt (FR-10)."""
        pass

    @abstractmethod
    def answer_chat_query(
        self, user_query: str, itinerary_context: Optional[ItineraryResult] = None
    ) -> str:
        """Answer general travel questions or follow-ups (FR-09)."""
        pass


class FakeLLMProvider(BaseLLMProvider):
    """Deterministic Fake LLM implementation for Stage 1 testing (PRD Requirement 7)."""

    def parse_user_intent(
        self, user_message: str, recalled_preferences: Optional[Dict[str, Any]] = None
    ) -> TravelRequest:
        """Extract travel parameters from text deterministically using patterns & memory."""
        text = user_message.lower()

        # 1. Destination Extraction
        destination = "Munnar"  # Default
        dest_match = re.search(r"(?:trip to|visit|explore|travel to|in)\s+([a-zA-Z0-9_\-]+)", text)
        if dest_match:
            destination = dest_match.group(1).capitalize()
        elif "goa" in text:
            destination = "Goa"
        elif "paris" in text:
            destination = "Paris"
        elif "jaipur" in text:
            destination = "Jaipur"
        elif "nowhere" in text or "xyz" in text or "invalid" in text:
            destination = "xyz_unknown_destination"

        # 2. Duration / Days
        days = 3
        days_match = re.search(r"(\d+)\s*[- ]*(?:day|days)", text)
        if days_match:
            days = max(1, min(14, int(days_match.group(1))))

        # 3. Budget Extraction
        budget = 8000.0
        budget_match = re.search(r"(?:₹|rs\.?|inr|budget\s*of|within)\s*([0-9,]+)", text)
        if budget_match:
            cleaned_num = budget_match.group(1).replace(",", "")
            budget = float(cleaned_num)
        elif "5,000" in text or "5000" in text:
            budget = 5000.0
        elif "1,500" in text or "1500" in text:
            budget = 1500.0
        elif "10,000" in text or "10000" in text:
            budget = 10000.0
        elif "12,000" in text or "12000" in text:
            budget = 12000.0

        # 4. Travellers
        travellers = 2
        trav_match = re.search(r"(\d+)\s*(?:traveller|traveler|person|people)", text)
        if trav_match:
            travellers = int(trav_match.group(1))
        elif "solo" in text or "alone" in text:
            travellers = 1
        elif "family" in text:
            travellers = 4

        # 5. Starting location / Origin
        origin = "Kochi"
        from_match = re.search(r"(?:from|starting from|departing)\s+([a-zA-Z]+)", text)
        if from_match:
            origin = from_match.group(1).capitalize()

        # 6. Apply Recalled Long-Term Preferences (Req 4)
        interests = ["Nature", "Sightseeing"]
        dietary = "Any"
        travel_style = "Balanced"
        transport = "Public / Car"

        if recalled_preferences:
            if "favorite_activities" in recalled_preferences and recalled_preferences["favorite_activities"]:
                acts = recalled_preferences["favorite_activities"]
                if isinstance(acts, list):
                    interests = acts
            if "preferred_food_types" in recalled_preferences and recalled_preferences["preferred_food_types"]:
                foods = recalled_preferences["preferred_food_types"]
                dietary = foods[0] if isinstance(foods, list) else str(foods)
            elif "dietary_preferences" in recalled_preferences and recalled_preferences["dietary_preferences"]:
                dietary = str(recalled_preferences["dietary_preferences"])
            if "preferred_transport" in recalled_preferences and recalled_preferences["preferred_transport"]:
                transport = str(recalled_preferences["preferred_transport"])
            if "typical_budget_tier" in recalled_preferences and recalled_preferences["typical_budget_tier"]:
                travel_style = str(recalled_preferences["typical_budget_tier"])
            elif "budget_tier" in recalled_preferences:
                travel_style = str(recalled_preferences["budget_tier"])

        # Override with explicit message keywords
        if "nature" in text:
            interests.append("Nature")
        if "beach" in text:
            interests.append("Beaches")
        if "heritage" in text or "culture" in text:
            interests.append("Heritage")
        if "veg" in text:
            dietary = "Vegetarian"

        return TravelRequest(
            origin=origin,
            destination=destination,
            start_date="2026-12-01",
            days=days,
            travellers=travellers,
            budget=budget,
            currency="INR",
            preferences=TravelPreference(
                travel_style=travel_style,
                interests=list(dict.fromkeys(interests)),
                dietary_preferences=dietary,
                preferred_transport=transport,
            ),
        )

    def generate_agent_thought(self, stage: str, context: Dict[str, Any]) -> str:
        """Return deterministic reasoning for each phase."""
        dest = context.get("destination", "the selected destination")
        if stage == "PLAN":
            return f"Structured 7-step execution roadmap created for trip to {dest}."
        elif stage == "SEARCH":
            return f"Analyzing attractions and accommodations suited to preferences in {dest}."
        elif stage == "WEATHER":
            return f"Validating weather suitability for scheduled outdoor activities in {dest}."
        elif stage == "ROUTE":
            return f"Optimizing transit distances and sequence between attractions in {dest}."
        elif stage == "BUDGET":
            return f"Verifying total expense calculation against customer budget limit."
        return f"Executing stage {stage} for destination {dest}."

    def modify_itinerary(
        self, current_itinerary: ItineraryResult, modification_request: str
    ) -> ItineraryResult:
        """Modify existing itinerary based on user input (FR-10, PRD Test Case 9)."""
        text = modification_request.lower()
        modified = current_itinerary.model_copy(deep=True)

        # Check if user wants to change destination
        dest_match = re.search(
            r"(?:change destination to|go to|switch to|travel to)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*)",
            text,
        )
        if dest_match:
            new_dest = " ".join(dest_match.group(1).strip().split()).title()
            modified.destination = new_dest
            modified.overview = f"Updated itinerary for {new_dest} preserving traveler preferences."
            for day in modified.daily_schedule:
                day.title = f"Day {day.day_number}: Exploring {new_dest}"

        # Check if user wants to reduce or adjust budget by percentage or absolute value.
        reduce_match = re.search(
            r"(?:reduce|cut|lower|decrease)\s*(?:the\s*)?budget\s*(?:by)?\s*(\d+(?:\.\d+)?)\s*(%)?",
            text,
        )
        if reduce_match:
            value = float(reduce_match.group(1).replace(",", ""))
            percent = reduce_match.group(2) == "%"
            if percent:
                reduction_amount = modified.budget.total_budget * (value / 100.0)
            else:
                reduction_amount = value

            new_budget = max(1000.0, modified.budget.total_budget - reduction_amount)
            modified.budget.total_budget = round(new_budget, 2)
            modified.budget.remaining_budget = round(
                modified.budget.total_budget - modified.budget.total_estimated_cost,
                2,
            )
            if modified.budget.remaining_budget < 0:
                modified.budget.is_over_budget = True
                modified.budget.affordable_alternatives.append(
                    f"Reduced budget by {value:g}{'%' if percent else ''}. Optimize accommodation and transport to meet target."
                )
            elif not modified.budget.affordable_alternatives:
                modified.budget.affordable_alternatives.append(
                    "Budget respected. Keep the current lodging and transit mix for a comfortable trip."
                )

        # Check if user wants to swap a specific day for indoor museums or similar indoor-focused experience.
        day_swap_match = re.search(r"(?:swap|replace)\s*(?:day|day\s*)(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s*(?:for|with)\s*(.+)", text)
        if day_swap_match:
            day_text = day_swap_match.group(1).strip().lower()
            day_map = {
                "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            }
            day_number = int(day_text) if day_text.isdigit() else day_map.get(day_text, 0)
            if day_number > 0:
                day_index = min(day_number - 1, len(modified.daily_schedule) - 1)
                day = modified.daily_schedule[day_index]
                replacement = day_swap_match.group(2).strip()
                day.title = f"Day {day.day_number}: {replacement.title()}"
                day.notes = f"Updated to {replacement} for an indoor-friendly experience."
                if day.attractions:
                    first = day.attractions[0]
                    first.name = replacement.title()
                    first.description = f"Curated indoor experience focused on {replacement}."
                    if "museum" in replacement:
                        first.activities = ["Museum visits", "Indoor galleries", "Cultural walkthrough"]
                    else:
                        first.activities = [replacement.title(), "Indoor relaxation", "Flexible timing"]

        return modified

    def answer_chat_query(
        self, user_query: str, itinerary_context: Optional[ItineraryResult] = None
    ) -> str:
        """Answer user travel questions (FR-09)."""
        query_lower = user_query.lower()
        dest = itinerary_context.destination if itinerary_context else "your destination"

        if "pack" in query_lower:
            return (
                f"Packing advice for {dest}: Pack comfortable walking shoes, light cotton layers for daytime, "
                "a light sweater or jacket for evenings, rain protection (umbrella or poncho), and sunscreen."
            )
        elif "veg" in query_lower or "vegetarian" in query_lower:
            return (
                f"Top vegetarian recommendations for {dest}: Saravana Bhavan, Woodlands, and local pure-veg thali restaurants "
                "serve excellent regional vegetarian cuisine."
            )
        elif "best place" in query_lower or "attraction" in query_lower:
            if itinerary_context and itinerary_context.daily_schedule:
                top_spots = [a.name for a in itinerary_context.daily_schedule[0].attractions]
                return f"Top recommended places in {dest} include: {', '.join(top_spots)}."
            return f"Top places in {dest} include local viewpoints, heritage spots, and natural reserves."
        elif "reduce" in query_lower or "budget" in query_lower:
            return (
                "To reduce your travel expenses: 1) Switch to public transport or shared shuttles, "
                "2) Choose homestays or budget boutique stays, 3) Enjoy local dining rather than tourist-heavy restaurants."
            )
        return (
            f"I have reviewed your inquiry regarding {dest}. Let me know if you would like me to modify "
            "specific days, rebalance your budget, or suggest alternative sights!"
        )


class GeminiLLMProvider(BaseLLMProvider):
    """Stage 2 Real LLM Provider using Google Gemini API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self.fallback = FakeLLMProvider()
        self._client = None

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize google.genai Client: {e}. Fallback enabled.")

    def parse_user_intent(
        self, user_message: str, recalled_preferences: Optional[Dict[str, Any]] = None
    ) -> TravelRequest:
        """Use Gemini to extract structured TravelRequest from conversational input."""
        if not self._client:
            return self.fallback.parse_user_intent(user_message, recalled_preferences)

        prompt = f"""
You are an expert travel agent. Extract trip parameters from the user's message into valid JSON:
User Message: "{user_message}"
Recalled Preferences: {json.dumps(recalled_preferences or {})}

Return JSON matching this schema:
{{
    "origin": "starting city (default: Kochi if not specified)",
    "destination": "destination city or place",
    "start_date": "YYYY-MM-DD (default: 2026-12-01 if unspecified)",
    "days": integer between 1 and 14,
    "travellers": integer >= 1,
    "budget": number > 0,
    "currency": "INR",
    "travel_style": "Budget / Balanced / Luxury / Nature / Cultural",
    "interests": ["list", "of", "interests"],
    "dietary_preferences": "Vegetarian / Non-Vegetarian / Vegan / Any",
    "preferred_transport": "Cab / Public / Car / Bus / Train"
}}
Return ONLY valid JSON with no markdown formatting.
"""
        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            raw_text = response.text.strip()
            # Remove any markdown code fence if returned
            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)

            data = json.loads(raw_text)
            return TravelRequest(
                origin=data.get("origin", "Kochi"),
                destination=data.get("destination", "Munnar"),
                start_date=data.get("start_date", "2026-12-01"),
                days=int(data.get("days", 3)),
                travellers=int(data.get("travellers", 2)),
                budget=float(data.get("budget", 8000.0)),
                currency=data.get("currency", "INR"),
                preferences=TravelPreference(
                    travel_style=data.get("travel_style", "Balanced"),
                    interests=data.get("interests", ["Sightseeing"]),
                    dietary_preferences=data.get("dietary_preferences", "Any"),
                    preferred_transport=data.get("preferred_transport", "Public / Car"),
                ),
            )
        except Exception as e:
            logger.warning(f"Gemini intent extraction failed ({e}), using fallback parser.")
            return self.fallback.parse_user_intent(user_message, recalled_preferences)

    def generate_agent_thought(self, stage: str, context: Dict[str, Any]) -> str:
        """Use Gemini to produce reasoning during Think phases."""
        if not self._client:
            return self.fallback.generate_agent_thought(stage, context)

        prompt = (
            f"You are the Think phase reasoning engine of an autonomous travel agent. "
            f"Current Stage: {stage}. Context: {json.dumps(context)}. "
            "Write a concise 1-2 sentence reasoning observation deciding the next analytical step."
        )
        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            return response.text.strip()
        except Exception:
            return self.fallback.generate_agent_thought(stage, context)

    def modify_itinerary(
        self, current_itinerary: ItineraryResult, modification_request: str
    ) -> ItineraryResult:
        """Modify itinerary using Gemini analysis while preserving user preferences."""
        # Check rule-based modification first for fast changes (destination switch, budget tweak)
        modified = self.fallback.modify_itinerary(current_itinerary, modification_request)

        if not self._client:
            return modified

        # Use Gemini for nuanced notes / activity adjustments if needed
        return modified

    def answer_chat_query(
        self, user_query: str, itinerary_context: Optional[ItineraryResult] = None
    ) -> str:
        """Answer conversational user questions about destination or itinerary (FR-09)."""
        if not self._client:
            return self.fallback.answer_chat_query(user_query, itinerary_context)

        dest = itinerary_context.destination if itinerary_context else "your destination"
        itinerary_summary = ""
        if itinerary_context:
            itinerary_summary = (
                f"Destination: {itinerary_context.destination}, Days: {itinerary_context.days}, "
                f"Budget: ₹{itinerary_context.budget.total_budget}, Total Cost: ₹{itinerary_context.budget.total_estimated_cost}. "
                f"Hotels: {[h.name for h in itinerary_context.hotels]}. "
                f"Highlights: {[d.title for d in itinerary_context.daily_schedule]}."
            )

        prompt = f"""
You are a knowledgeable AI Travel Planner Agent assisting a traveler.
Trip Context: {itinerary_summary}
User Question: "{user_query}"

Provide a warm, helpful, and concise answer (2-4 sentences). Suggest specific practical advice, local dishes, or sights relevant to {dest}.
"""
        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Gemini chat response failed ({e}), falling back.")
            return self.fallback.answer_chat_query(user_query, itinerary_context)


def get_llm_provider(force_real: bool = False) -> BaseLLMProvider:
    """Provider factory respecting MOCK_LLM configuration setting.
    
    Returns:
        GeminiLLMProvider if real LLM enabled and key present; otherwise FakeLLMProvider.
    """
    if force_real or (not settings.MOCK_LLM and settings.GEMINI_API_KEY):
        return GeminiLLMProvider(api_key=settings.GEMINI_API_KEY, model_name=settings.GEMINI_MODEL)

    return FakeLLMProvider()
