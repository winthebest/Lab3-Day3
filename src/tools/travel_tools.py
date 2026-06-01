import ast
import json
import os
import re
from typing import Any, Dict

_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "travel_data.json")


def _load_data() -> Dict[str, Any]:
    with open(_DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def normalize_city(code_or_name: str) -> str:
    """Map tên thành phố / IATA → mã 3 chữ (SGN, DAD, HAN)."""
    key = code_or_name.strip().upper()
    data = _load_data()
    return data["city_codes"].get(key, key)


def search_flights(
    origin: str,
    destination: str,
    date: str,
    passengers: int = 1,
) -> str:
    """
    origin/destination: IATA hoặc tên thành phố (SGN, DAD, HCM, Đà Nẵng).
    date: YYYY-MM-DD. passengers: 1–9.
    """
    passengers = max(1, min(9, int(passengers)))
    orig = normalize_city(origin)
    dest = normalize_city(destination)
    route_key = f"{orig}-{dest}"

    data = _load_data()
    route = data["routes"].get(route_key)
    if not route:
        return (
            f"No flights found for route {orig}→{dest}. "
            f"Available routes: {', '.join(data['routes'].keys())}"
        )

    per_person = route["price_per_person_vnd"]
    total = per_person * passengers
    return (
        f"Flight {orig}→{dest} on {date}: {route['airline']}, "
        f"{route['duration_minutes']} min. "
        f"Price {per_person:,} VND/person × {passengers} = {total:,} VND total."
    )


def get_hotel_rate(
    city: str,
    check_in: str,
    nights: int,
    guests: int = 1,
    tier: str = "standard",
) -> str:
    """city: IATA hoặc tên. nights: số đêm. tier: standard | deluxe."""
    nights = max(1, int(nights))
    guests = max(1, min(9, int(guests)))
    tier = tier.strip().lower()
    if tier not in ("standard", "deluxe"):
        tier = "standard"

    city_code = normalize_city(city)
    data = _load_data()
    hotel = data["hotels"].get(city_code)
    if not hotel:
        return f"No hotels in catalog for city code {city_code}."

    per_night = hotel[tier]
    room_total = per_night * nights
    return (
        f"Hotel {city_code} ({tier}): {per_night:,} VND/night × {nights} nights "
        f"= {room_total:,} VND (check-in {check_in}, {guests} guest(s) noted)."
    )


def apply_promo(code: str, subtotal: int) -> str:
    """code: SUMMER, FAMILY, NEWUSER. subtotal: VND trước giảm."""
    subtotal = int(subtotal)
    data = _load_data()
    promo = data["promos"].get(code.strip().upper())
    if not promo:
        return f"Invalid promo code '{code}'. Valid: {', '.join(data['promos'].keys())}"

    if promo["type"] == "percent":
        discount = int(subtotal * promo["value"] / 100)
    else:
        discount = int(promo["value"])

    final = max(0, subtotal - discount)
    return (
        f"Promo {code.upper()}: {promo['description']}. "
        f"Subtotal {subtotal:,} VND − discount {discount:,} VND = {final:,} VND."
    )


def parse_tool_args(arg_string: str) -> Dict[str, Any]:
    """Parse Action args: JSON dict hoặc key=value."""
    arg_string = arg_string.strip()
    if not arg_string:
        return {}

    if arg_string.startswith("{"):
        return ast.literal_eval(arg_string)

    result: Dict[str, Any] = {}
    for match in re.finditer(
        r'(\w+)\s*=\s*("([^"]*)"|\'([^\']*)\'|(\d+))',
        arg_string,
    ):
        key = match.group(1)
        value = match.group(3) or match.group(4) or match.group(5)
        result[key] = int(value) if value.isdigit() else value
    return result
