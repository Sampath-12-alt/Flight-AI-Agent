"""
Flight Search Service.

Searches live flight availability using the Aviationstack API.
Falls back to realistic mock data when API credentials are unavailable.
"""

import sys
import random
import requests
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import AVIATIONSTACK_API_KEY


def search_flights(
    origin_code: str,
    destination_code: str,
    date: str,
    max_results: int = 5,
) -> dict:
    """
    Search for available flights on a given date.

    Args:
        origin_code: IATA airport code (e.g., "DEL")
        destination_code: IATA airport code (e.g., "BOM")
        date: Travel date in YYYY-MM-DD format
        max_results: Maximum number of flights to return

    Returns:
        dict with search results:
        {
            "success": bool,
            "flights": list[dict],
            "source": str ("aviationstack_api" or "mock_data"),
            "num_results": int,
            "error": str | None
        }
    """
    if not origin_code or not destination_code or not date:
        return {
            "success": False,
            "flights": [],
            "source": "none",
            "num_results": 0,
            "error": "Origin, destination, and date are required.",
        }

    # Try Aviationstack API first
    if AVIATIONSTACK_API_KEY:
        try:
            return _search_aviationstack(origin_code, destination_code, date, max_results)
        except Exception as e:
            print(f"⚠️  Aviationstack API failed: {e}. Falling back to mock data.")

    # Fallback to mock data
    return _search_mock(origin_code, destination_code, date, max_results)


def _search_aviationstack(
    origin: str, destination: str, date: str, max_results: int
) -> dict:
    """Search flights using Aviationstack API."""
    url = "http://api.aviationstack.com/v1/flights"
    params = {
        "access_key": AVIATIONSTACK_API_KEY,
        "dep_iata": origin,
        "arr_iata": destination,
        "limit": max_results * 2  # Fetch extra to filter out unhelpful ones
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    if "data" not in data:
        raise ValueError("Invalid response from Aviationstack")

    flights = []
    # Seed random for deterministic price generation based on flight number
    # Aviationstack gives real flights but doesn't provide ticket prices.
    
    for item in data.get("data", []):
        if len(flights) >= max_results:
            break
            
        airline = item.get("airline", {})
        flight_info = item.get("flight", {})
        dep = item.get("departure", {})
        arr = item.get("arrival", {})

        # Need scheduled departure and arrival
        dep_time_str = dep.get("scheduled")
        arr_time_str = arr.get("scheduled")
        
        if not dep_time_str or not arr_time_str:
            continue

        flight_num = flight_info.get("iata") or f"{airline.get('iata')}{flight_info.get('number')}"
        airline_name = airline.get("name", "Unknown Airline")
        airline_code = airline.get("iata", "XX")

        # Parse times to calculate duration
        try:
            # Aviationstack returns: "2026-07-02T17:30:00+00:00"
            dep_dt = datetime.fromisoformat(dep_time_str.replace("+00:00", ""))
            arr_dt = datetime.fromisoformat(arr_time_str.replace("+00:00", ""))
            
            # Simple duration calculation
            duration_secs = (arr_dt - dep_dt).total_seconds()
            if duration_secs < 0:
                duration_secs += 24 * 3600  # Crossed midnight
            duration_hours = round(duration_secs / 3600, 1)
        except Exception:
            duration_hours = 2.0

        # Deterministic pseudo-random price based on flight number
        random.seed(flight_num)
        base_price = random.randint(4000, 12000)
        price = round(base_price, -1)

        flight = {
            "flight_number": flight_num,
            "airline": airline_name,
            "airline_code": airline_code,
            "origin": origin,
            "destination": destination,
            "departure_time": dep_time_str,
            "arrival_time": arr_time_str,
            "duration_hours": duration_hours,
            "duration_display": _format_duration(duration_hours),
            "stops": 0,  # Aviationstack flights endpoint usually gives direct flights
            "price": price,
            "currency": "INR",
            "cabin_class": "ECONOMY",
            "source": "aviationstack_api",
        }
        flights.append(flight)

    # Sort by price
    flights.sort(key=lambda f: f["price"])

    return {
        "success": True,
        "flights": flights,
        "source": "aviationstack_api",
        "num_results": len(flights),
        "error": None,
    }


def _search_mock(
    origin: str, destination: str, date: str, max_results: int
) -> dict:
    """
    Generate realistic mock flight data when API is unavailable.
    Uses deterministic seeding based on route + date for consistency.
    """
    # Seed for consistent results per route+date combination
    seed_str = f"{origin}-{destination}-{date}"
    random.seed(hash(seed_str) % (2**32))

    # Airline options for Indian domestic routes
    airlines = [
        {"code": "AI", "name": "Air India"},
        {"code": "6E", "name": "IndiGo"},
        {"code": "SG", "name": "SpiceJet"},
        {"code": "UK", "name": "Vistara"},
        {"code": "I5", "name": "AirAsia India"},
        {"code": "G8", "name": "Go First"},
    ]

    # Base price ranges by route distance (simplified)
    route_key = f"{origin}-{destination}"
    base_prices = {
        "DEL-BOM": (4500, 12000),
        "BOM-DEL": (4500, 12000),
        "BLR-DEL": (5000, 13000),
        "DEL-BLR": (5000, 13000),
        "BOM-GOI": (2500, 7000),
        "GOI-BOM": (2500, 7000),
        "HYD-MAA": (3000, 8000),
        "MAA-HYD": (3000, 8000),
        "CCU-DEL": (5500, 14000),
        "DEL-CCU": (5500, 14000),
        "DEL-JAI": (2000, 5500),
        "JAI-DEL": (2000, 5500),
        "BOM-BLR": (3500, 9500),
        "BLR-BOM": (3500, 9500),
        "PNQ-CCU": (5000, 12000),
        "CCU-PNQ": (5000, 12000),
    }

    price_range = base_prices.get(route_key, (4000, 10000))

    # Generate departure times spread across the day
    departure_hours = sorted(random.sample(range(5, 23), min(max_results + 1, 8)))

    flights = []
    selected_airlines = random.sample(airlines, min(len(airlines), max_results + 1))

    for i in range(min(max_results, len(departure_hours))):
        al = selected_airlines[i % len(selected_airlines)]
        dep_hour = departure_hours[i]
        dep_min = random.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])

        # Flight duration based on route (1.5-3.5 hours for domestic)
        duration = round(random.uniform(1.5, 3.5), 1)
        stops = random.choices([0, 1], weights=[75, 25])[0]
        if stops > 0:
            duration += random.uniform(1.0, 2.0)
            duration = round(duration, 1)

        # Price with some variation
        price = round(random.uniform(*price_range), -1)  # Round to nearest 10

        # Calculate arrival time
        dep_datetime = datetime.strptime(f"{date} {dep_hour:02d}:{dep_min:02d}", "%Y-%m-%d %H:%M")
        arr_datetime = dep_datetime + timedelta(hours=duration)

        flight_num = f"{al['code']}{random.randint(100, 999)}"

        flights.append({
            "flight_number": flight_num,
            "airline": al["name"],
            "airline_code": al["code"],
            "origin": origin,
            "destination": destination,
            "departure_time": dep_datetime.strftime("%Y-%m-%dT%H:%M:%S"),
            "arrival_time": arr_datetime.strftime("%Y-%m-%dT%H:%M:%S"),
            "duration_hours": duration,
            "duration_display": _format_duration(duration),
            "stops": stops,
            "price": price,
            "currency": "INR",
            "cabin_class": "ECONOMY",
            "source": "mock_data",
        })

    # Sort by price (cheapest first)
    flights.sort(key=lambda f: f["price"])

    # Reset random seed
    random.seed()

    return {
        "success": True,
        "flights": flights,
        "source": "mock_data",
        "num_results": len(flights),
        "error": None,
    }


# ── Helper Functions ──────────────────────────────────────────

def _format_duration(hours: float) -> str:
    """Format duration in hours to 'Xh Ym' display string."""
    h = int(hours)
    m = int((hours - h) * 60)
    if h > 0 and m > 0:
        return f"{h}h {m}m"
    elif h > 0:
        return f"{h}h"
    else:
        return f"{m}m"


def search_multiple_dates(
    origin_code: str,
    destination_code: str,
    dates: list[str],
    max_per_date: int = 5,
) -> dict:
    """
    Search flights across multiple dates and aggregate results.

    Args:
        origin_code: IATA airport code
        destination_code: IATA airport code
        dates: List of dates in YYYY-MM-DD format
        max_per_date: Max flights per date

    Returns:
        dict with aggregated search results:
        {
            "success": bool,
            "flights": list[dict],       # All flights across all dates
            "dates_searched": int,
            "dates_with_results": int,
            "source": str,
            "num_results": int,
            "error": str | None
        }
    """
    if not dates:
        return {
            "success": False, "flights": [], "dates_searched": 0,
            "dates_with_results": 0, "source": "none",
            "num_results": 0, "error": "No dates provided.",
        }

    all_flights = []
    dates_with_results = 0
    source = "mock_data"

    for date in dates:
        result = search_flights(origin_code, destination_code, date, max_per_date)
        if result["success"] and result["num_results"] > 0:
            # Add the search date to each flight for multi-day display
            for flight in result["flights"]:
                flight["search_date"] = date
            all_flights.extend(result["flights"])
            dates_with_results += 1
            source = result["source"]

    # Sort all flights by price
    all_flights.sort(key=lambda f: f["price"])

    return {
        "success": len(all_flights) > 0,
        "flights": all_flights,
        "dates_searched": len(dates),
        "dates_with_results": dates_with_results,
        "source": source,
        "num_results": len(all_flights),
        "error": None if all_flights else "No flights found on any of the searched dates.",
    }


# ── Standalone testing ────────────────────────────────────────
if __name__ == "__main__":
    print("\n✈️  Flight Search Test (Aviationstack)")
    print("=" * 60)

    # Single date test
    result = search_flights("DEL", "BOM", "2026-07-23", max_results=5)
    print(f"\nSingle Date — Source: {result['source']}, Found: {result['num_results']} flights\n")

    for i, f in enumerate(result["flights"], 1):
        dep = f["departure_time"].split("T")[1][:5] if "T" in f["departure_time"] else f["departure_time"]
        arr = f["arrival_time"].split("T")[1][:5] if "T" in f["arrival_time"] else f["arrival_time"]
        stops_str = "Direct" if f["stops"] == 0 else f"{f['stops']} stop(s)"
        print(
            f"  {i}. {f['flight_number']:8s} | {f['airline']:15s} | "
            f"{dep} → {arr} | {f['duration_display']:6s} | "
            f"{stops_str:10s} | ₹{f['price']:,.0f}"
        )

    # Multi-date test
    print("\n" + "=" * 60)
    print("Multi-Date Search (3 days):")
    multi = search_multiple_dates("HYD", "BOM", ["2026-07-10", "2026-07-11", "2026-07-12"], max_per_date=3)
    print(f"Dates searched: {multi['dates_searched']}, Results: {multi['num_results']}")
    for i, f in enumerate(multi["flights"][:5], 1):
        dep = f["departure_time"].split("T")[1][:5] if "T" in f["departure_time"] else ""
        print(f"  {i}. {f.get('search_date','')} | {f['flight_number']:8s} | {f['airline']:15s} | ₹{f['price']:,.0f}")

