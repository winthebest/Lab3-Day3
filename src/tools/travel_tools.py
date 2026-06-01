import ast
import json
import os
import re
from typing import Any, Dict, List

import requests

from src.tools.failure_simulation import simulated_observation

_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "travel_data.json")
_SERPAPI_URL = "https://serpapi.com/search.json"


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
    simulated = simulated_observation("search_flights")
    if simulated:
        return simulated

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
    simulated = simulated_observation("get_hotel_rate")
    if simulated:
        return simulated

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
    simulated = simulated_observation("apply_promo")
    if simulated:
        return simulated

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


def estimate_trip_cost(
    origin: str,
    destination: str,
    depart_date: str,
    passengers: int = 1,
    nights: int = 2,
    guests: int = 1,
    hotel_tier: str = "standard",
    promo_code: str = "",
) -> str:
    """
    Ước tính tổng chi phí chuyến đi (vé + khách sạn + mã giảm giá) trong một lần gọi.
    destination cũng dùng làm city_code khách sạn. promo_code: tùy chọn (SUMMER, FAMILY, NEWUSER).
    """
    simulated = simulated_observation("estimate_trip_cost")
    if simulated:
        return simulated

    passengers = max(1, min(9, int(passengers)))
    nights = max(1, int(nights))
    guests = max(1, min(9, int(guests)))
    tier = hotel_tier.strip().lower()
    if tier not in ("standard", "deluxe"):
        tier = "standard"

    dest_code = normalize_city(destination)
    data = _load_data()
    orig = normalize_city(origin)
    route_key = f"{orig}-{dest_code}"
    route = data["routes"].get(route_key)
    if not route:
        return (
            f"No flights found for route {orig}→{dest_code}. "
            f"Available routes: {', '.join(data['routes'].keys())}"
        )

    flight_total = route["price_per_person_vnd"] * passengers
    hotel = data["hotels"].get(dest_code)
    if not hotel:
        return f"No hotels in catalog for city code {dest_code}."

    hotel_total = hotel[tier] * nights
    subtotal = flight_total + hotel_total

    lines = [
        f"Trip estimate {orig}→{dest_code}, depart {depart_date}:",
        f"- Flights: {route['price_per_person_vnd']:,} VND/person × {passengers} "
        f"= {flight_total:,} VND ({route['airline']})",
        f"- Hotel ({tier}): {hotel[tier]:,} VND/night × {nights} nights "
        f"= {hotel_total:,} VND ({guests} guest(s))",
        f"- Subtotal (before promo): {subtotal:,} VND",
    ]

    promo_code = (promo_code or "").strip()
    if promo_code:
        promo_out = apply_promo(promo_code, subtotal)
        lines.append(f"- {promo_out}")
        if "Invalid promo" in promo_out:
            return "\n".join(lines)
        final_match = re.search(r"=\s*([\d,]+)\s*VND\.?\s*$", promo_out)
        if final_match:
            lines.append(f"- Grand total after promo: {final_match.group(1)} VND")
    else:
        lines.append(f"- Grand total: {subtotal:,} VND (no promo applied)")

    return "\n".join(lines)


def get_weather_forecast(
    destination: str,
    start_date: str = "",
    days: int = 3,
) -> str:
    """
    Dự báo thời tiết mock tại điểm đến (không gọi API thật).

    destination: tên thành phố hoặc mã IATA (Đà Nẵng, DAD, HCM, ...).
    start_date: YYYY-MM-DD (tùy chọn); bỏ trống thì lấy từ ngày đầu trong catalog.
    days: số ngày dự báo (1–7).
    """
    simulated = simulated_observation("get_weather_forecast")
    if simulated:
        return simulated

    destination = destination.strip()
    if not destination:
        return "Weather error: destination is required."

    days = max(1, min(7, int(days)))
    city_code = normalize_city(destination)
    data = _load_data()
    weather_by_city = data.get("weather") or {}
    weather = weather_by_city.get(city_code)
    if not weather:
        available = ", ".join(
            f"{code} ({info.get('city_name', code)})"
            for code, info in weather_by_city.items()
        )
        return (
            f"No weather forecast (mock) for '{destination}' (code {city_code}). "
            f"Available cities: {available or 'none'}."
        )

    all_days: List[Dict[str, Any]] = list(weather.get("forecasts") or [])
    if not all_days:
        return f"No forecast days in catalog for {city_code}."

    start_date = start_date.strip()
    if start_date:
        start_idx = next(
            (i for i, row in enumerate(all_days) if row.get("date") == start_date),
            None,
        )
        if start_idx is None:
            sample_dates = ", ".join(row["date"] for row in all_days[:3])
            return (
                f"No mock forecast for {city_code} on {start_date}. "
                f"Sample dates in catalog: {sample_dates}."
            )
        slice_days = all_days[start_idx : start_idx + days]
    else:
        slice_days = all_days[:days]

    city_name = weather.get("city_name", city_code)
    lines = [
        f"Weather forecast (mock data) for {city_name} ({city_code}):",
        f"Overview: {weather.get('summary', 'N/A')}",
    ]
    for row in slice_days:
        lines.append(
            f"- {row['date']}: {row['condition']}, "
            f"{row['temp_min_c']}–{row['temp_max_c']}°C, "
            f"rain chance {row['rain_chance_pct']}%, humidity {row['humidity_pct']}%"
        )
    tip = weather.get("travel_tip")
    if tip:
        lines.append(f"Travel tip: {tip}")
    lines.append("(Source: lab mock catalog — not live weather API.)")
    return "\n".join(lines)


def search_attractions(destination: str, query: str = "", limit: int = 5) -> str:
    """
    Search SerpAPI for landmarks and tourist attractions at a destination.

    destination: city/province/place name. query: optional search intent.
    limit: number of results to summarize.
    """
    simulated = simulated_observation("search_attractions")
    if simulated:
        return simulated

    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return "SerpAPI error: missing SERPAPI_API_KEY in environment or .env file."

    destination = destination.strip()
    if not destination:
        return "SerpAPI error: destination is required."

    limit = max(1, min(10, int(limit)))
    search_query = query.strip() or f"địa danh khu tham quan du lịch {destination}"
    if destination.lower() not in search_query.lower():
        search_query = f"{search_query} {destination}"

    params = {
        "engine": "google",
        "q": search_query,
        "api_key": api_key,
        "hl": "vi",
        "gl": "vn",
    }
    response = requests.get(_SERPAPI_URL, params=params, timeout=12)
    response.raise_for_status()
    payload = response.json()

    results: List[Dict[str, Any]] = []
    for item in payload.get("local_results", {}).get("places", []):
        results.append(
            {
                "title": item.get("title"),
                "snippet": item.get("description") or item.get("type"),
                "link": item.get("website") or item.get("gps_coordinates"),
            }
        )

    for item in payload.get("organic_results", []):
        results.append(
            {
                "title": item.get("title"),
                "snippet": item.get("snippet"),
                "link": item.get("link"),
            }
        )

    clean = [r for r in results if r.get("title")][:limit]
    if not clean:
        return f"No attractions found by SerpAPI for destination '{destination}'."

    lines = [f"SerpAPI attractions for {destination}:"]
    for idx, item in enumerate(clean, start=1):
        snippet = f" - {item['snippet']}" if item.get("snippet") else ""
        link = f" ({item['link']})" if item.get("link") else ""
        lines.append(f"{idx}. {item['title']}{snippet}{link}")
    return "\n".join(lines)


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
