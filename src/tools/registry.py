from typing import Any, Callable, Dict, List

from src.tools import travel_tools

ToolFn = Callable[..., str]

TOOL_REGISTRY: Dict[str, ToolFn] = {
    "search_flights": travel_tools.search_flights,
    "get_hotel_rate": travel_tools.get_hotel_rate,
    "apply_promo": travel_tools.apply_promo,
    "search_attractions": travel_tools.search_attractions,
}

TOOL_SPECS: List[Dict[str, str]] = [
    {
        "name": "search_flights",
        "description": (
            "Lowest one-way fare in VND. "
            "Args: origin, destination (IATA 3-letter e.g. SGN, DAD — map HCM→SGN, Đà Nẵng→DAD), "
            "date (YYYY-MM-DD), passengers (int 1-9). "
            'Example: search_flights(origin="SGN", destination="DAD", date="2026-07-15", passengers=2)'
        ),
    },
    {
        "name": "get_hotel_rate",
        "description": (
            "Hotel price in VND. "
            "Args: city (IATA), check_in (YYYY-MM-DD), nights (int), guests (int), tier (standard|deluxe). "
            'Example: get_hotel_rate(city="DAD", check_in="2026-07-15", nights=2, guests=2)'
        ),
    },
    {
        "name": "apply_promo",
        "description": (
            "Apply discount code on subtotal VND. Codes: SUMMER (10%), FAMILY (500k fixed), NEWUSER (5%). "
            'Example: apply_promo(code="SUMMER", subtotal=8400000)'
        ),
    },
    {
        "name": "search_attractions",
        "description": (
            "Search SerpAPI for landmarks, attractions, and sightseeing places at a destination. "
            "Use when the user asks what to visit, where to go, or tourist spots. "
            "Args: destination (city/province/place), query (optional), limit (int 1-10). "
            'Example: search_attractions(destination="Đà Nẵng", query="địa danh khu tham quan Đà Nẵng", limit=5)'
        ),
    },
]


def get_tool_specs() -> List[Dict[str, str]]:
    return TOOL_SPECS


def execute_tool(tool_name: str, arg_string: str) -> str:
    fn = TOOL_REGISTRY.get(tool_name)
    if not fn:
        valid = ", ".join(TOOL_REGISTRY.keys())
        return f"Tool '{tool_name}' not found. Available: {valid}"

    try:
        kwargs = travel_tools.parse_tool_args(arg_string)
        return fn(**kwargs)
    except TypeError as e:
        return f"Tool argument error for {tool_name}: {e}"
    except Exception as e:
        return f"Tool execution failed: {e}"
