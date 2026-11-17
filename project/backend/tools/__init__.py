"""AI Smart Travel & Itinerary Planner Tools Package.

Exports the 4 core tools specified in PRD Section 5.2:
1. DestinationSearchTool
2. WeatherTool
3. RoutePlanningTool
4. BudgetCalculatorTool
"""

from backend.tools.base import BaseTool, ToolResult
from backend.tools.search_tool import DestinationSearchTool
from backend.tools.weather_tool import WeatherTool
from backend.tools.route_tool import RoutePlanningTool
from backend.tools.budget_tool import BudgetCalculatorTool

__all__ = [
    "BaseTool",
    "ToolResult",
    "DestinationSearchTool",
    "WeatherTool",
    "RoutePlanningTool",
    "BudgetCalculatorTool",
]
