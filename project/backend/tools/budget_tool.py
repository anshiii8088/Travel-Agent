"""Tool 4: Budget Calculator Tool (FR-04, PRD Section 5.2).

Calculates total and category expenses, determines budget surplus or deficit,
and suggests affordable alternatives if expenses exceed user budget.
"""

from typing import Any, Dict, List, Optional
from backend.tools.base import BaseTool, ToolResult


class BudgetCalculatorTool(BaseTool):
    """Deterministic budget calculation and cost-optimization tool."""

    name: str = "budget_calculator"
    description: str = (
        "Calculate total travel expenses across transport, lodging, food, and activities. "
        "Evaluates whether the trip fits the user budget and generates cost-reduction recommendations."
    )

    def execute(
        self,
        total_budget: float,
        transportation_cost: float = 0.0,
        accommodation_cost: float = 0.0,
        food_cost: float = 0.0,
        activity_cost: float = 0.0,
        contingency_pct: float = 5.0,
        travellers: int = 1,
        **kwargs: Any,
    ) -> ToolResult:
        """Calculate expense breakdown and verify budget feasibility."""
        if total_budget <= 0:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error="Total budget must be greater than zero.",
            )

        num_travellers = max(1, travellers)

        # Calculate subtotal
        subtotal = (
            float(transportation_cost)
            + float(accommodation_cost)
            + float(food_cost)
            + float(activity_cost)
        )

        # Buffer for miscellaneous emergencies
        contingency = subtotal * (contingency_pct / 100.0)
        total_estimated = subtotal + contingency

        remaining = total_budget - total_estimated
        is_over = total_estimated > total_budget
        cost_per_person = total_estimated / num_travellers

        # Generate actionable alternatives if over-budget
        alternatives: List[str] = []
        if is_over:
            deficit = total_estimated - total_budget
            alternatives.append(
                f"Trip exceeds budget by ₹{deficit:,.2f}. Below are suggested optimizations:"
            )

            # Accommodation optimization
            if accommodation_cost > (total_budget * 0.4):
                potential_saving = accommodation_cost * 0.35
                alternatives.append(
                    f"• Accommodation: Switch from luxury/resort to budget stay or boutique hostel (Save ~₹{potential_saving:,.0f})."
                )

            # Transport optimization
            if transportation_cost > (total_budget * 0.25):
                potential_saving = transportation_cost * 0.50
                alternatives.append(
                    f"• Transport: Utilize state express buses or train instead of private chauffeured cab (Save ~₹{potential_saving:,.0f})."
                )

            # Food optimization
            if food_cost > (total_budget * 0.25):
                potential_saving = food_cost * 0.30
                alternatives.append(
                    f"• Dining: Enjoy highly-rated local authentic eateries rather than fine-dining restaurants (Save ~₹{potential_saving:,.0f})."
                )

            # Activities optimization
            if activity_cost > (total_budget * 0.20):
                alternatives.append(
                    "• Sightseeing: Prioritize scenic viewpoints, tea garden walks, and public lakes with low or zero entrance fees."
                )

        return ToolResult(
            tool_name=self.name,
            success=True,
            data={
                "total_budget": round(total_budget, 2),
                "travellers": num_travellers,
                "breakdown": {
                    "transportation_cost": round(transportation_cost, 2),
                    "accommodation_cost": round(accommodation_cost, 2),
                    "food_cost": round(food_cost, 2),
                    "activity_cost": round(activity_cost, 2),
                    "contingency_cost": round(contingency, 2),
                },
                "total_estimated_cost": round(total_estimated, 2),
                "remaining_budget": round(remaining, 2),
                "cost_per_person": round(cost_per_person, 2),
                "is_over_budget": is_over,
                "affordable_alternatives": alternatives,
            },
        )

