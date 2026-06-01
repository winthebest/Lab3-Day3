from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import os
from typing import Dict, Iterator, Optional


SIMULATION_NONE = "none"
SIMULATION_TOOL_TIMEOUT = "tool_timeout"
SIMULATION_FLIGHT_NOT_FOUND = "flight_not_found"
SIMULATION_HOTEL_NOT_FOUND = "hotel_not_found"
SIMULATION_PROMO_NOT_FOUND = "promo_not_found"

SIMULATION_OPTIONS: Dict[str, str] = {
    SIMULATION_NONE: "No simulated failure",
    SIMULATION_TOOL_TIMEOUT: "Tool timeout",
    SIMULATION_FLIGHT_NOT_FOUND: "Flight data not found",
    SIMULATION_HOTEL_NOT_FOUND: "Hotel data not found",
    SIMULATION_PROMO_NOT_FOUND: "Promo code not found",
}

_active_mode: ContextVar[str] = ContextVar(
    "travel_failure_simulation_mode",
    default=os.getenv("TRAVEL_FAILURE_SIMULATION", SIMULATION_NONE),
)


def normalize_mode(mode: Optional[str]) -> str:
    normalized = (mode or SIMULATION_NONE).strip().lower().replace("-", "_")
    aliases = {
        "off": SIMULATION_NONE,
        "disabled": SIMULATION_NONE,
        "timeout": SIMULATION_TOOL_TIMEOUT,
        "no_data": SIMULATION_FLIGHT_NOT_FOUND,
        "flight_no_data": SIMULATION_FLIGHT_NOT_FOUND,
        "hotel_no_data": SIMULATION_HOTEL_NOT_FOUND,
        "promo_no_data": SIMULATION_PROMO_NOT_FOUND,
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in SIMULATION_OPTIONS:
        valid = ", ".join(SIMULATION_OPTIONS)
        raise ValueError(f"Unknown failure simulation mode '{mode}'. Valid: {valid}")
    return normalized


def get_failure_simulation_mode() -> str:
    return normalize_mode(_active_mode.get())


@contextmanager
def failure_simulation(mode: Optional[str]) -> Iterator[str]:
    normalized = normalize_mode(mode)
    token = _active_mode.set(normalized)
    try:
        yield normalized
    finally:
        _active_mode.reset(token)


def simulated_observation(tool_name: str) -> Optional[str]:
    mode = get_failure_simulation_mode()
    if mode == SIMULATION_NONE:
        return None

    if mode == SIMULATION_TOOL_TIMEOUT:
        return (
            f"Simulated timeout: tool '{tool_name}' exceeded the allowed response time. "
            "Retry later or switch the failure simulation back to none."
        )

    if mode == SIMULATION_FLIGHT_NOT_FOUND and tool_name == "search_flights":
        return (
            "No flights found (simulated): the flight catalog returned empty data "
            "for this route/date."
        )

    if mode == SIMULATION_HOTEL_NOT_FOUND and tool_name == "get_hotel_rate":
        return (
            "No hotels found (simulated): the hotel catalog returned empty data "
            "for this city/check-in date."
        )

    if mode == SIMULATION_PROMO_NOT_FOUND and tool_name == "apply_promo":
        return (
            "Invalid promo code (simulated): the promo catalog did not contain "
            "the requested code."
        )

    return None
