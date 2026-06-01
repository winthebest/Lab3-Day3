import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.registry import execute_tool
from src.tools.failure_simulation import failure_simulation
from src.tools.travel_tools import (
    apply_promo,
    get_hotel_rate,
    normalize_city,
    search_flights,
)


def test_normalize_city():
    assert normalize_city("HCM") == "SGN"
    assert normalize_city("Đà Nẵng") == "DAD"


def test_search_flights_sgn_dad():
    result = search_flights("SGN", "DAD", "2026-07-15", passengers=2)
    assert "3,000,000" in result or "3000000" in result.replace(",", "")


def test_execute_tool_promo():
    out = execute_tool('apply_promo', 'code="SUMMER", subtotal=10000000')
    assert "1,000,000" in out or "1000000" in out.replace(",", "")


def test_invalid_route():
    out = search_flights("SGN", "XXX", "2026-07-15", 1)
    assert "No flights" in out


def test_simulate_flight_not_found():
    with failure_simulation("flight_not_found"):
        out = search_flights("SGN", "DAD", "2026-07-15", passengers=2)
    assert "simulated" in out.lower()
    assert "No flights" in out


def test_simulate_hotel_not_found():
    with failure_simulation("hotel_not_found"):
        out = get_hotel_rate("DAD", "2026-07-15", nights=2, guests=2)
    assert "simulated" in out.lower()
    assert "No hotels" in out


def test_simulate_promo_not_found():
    with failure_simulation("promo_not_found"):
        out = apply_promo("SUMMER", 5400000)
    assert "simulated" in out.lower()
    assert "Invalid promo code" in out


def test_simulate_tool_timeout():
    with failure_simulation("tool_timeout"):
        out = execute_tool(
            "search_flights",
            'origin="SGN", destination="DAD", date="2026-07-15", passengers=2',
        )
    assert "timeout" in out.lower()
    assert "search_flights" in out
