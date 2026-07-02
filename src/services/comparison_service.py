"""
Flight Comparison Service.

Compares available flights and recommends the best option
based on weighted scoring across multiple criteria.
"""


def compare_flights(flights: list[dict], preferences: dict | None = None) -> dict:
    """
    Compare and rank available flights.

    Ranking weights (customizable via preferences):
        - Price:          40%
        - Duration:       25%
        - Stops:          20%
        - Departure time: 15%

    Args:
        flights: List of flight dicts from FlightSearchService
        preferences: Optional dict to customize ranking weights

    Returns:
        dict with comparison results:
        {
            "success": bool,
            "ranked_flights": list[dict],  # flights with scores, sorted best-first
            "recommended": dict,            # top-ranked flight
            "recommendation_reason": str,
            "tags": dict,                   # "cheapest", "fastest", "fewest_stops" labels
            "error": str | None
        }
    """
    if not flights:
        return {
            "success": False,
            "ranked_flights": [],
            "recommended": {},
            "recommendation_reason": "",
            "tags": {},
            "error": "No flights available for comparison.",
        }

    if len(flights) == 1:
        flight = flights[0].copy()
        flight["score"] = 100.0
        flight["rank"] = 1
        return {
            "success": True,
            "ranked_flights": [flight],
            "recommended": flight,
            "recommendation_reason": "This is the only available flight on the requested date.",
            "tags": {flights[0]["flight_number"]: ["Only Option"]},
            "error": None,
        }

    # Default weights
    weights = {
        "price": 0.40,
        "duration": 0.25,
        "stops": 0.20,
        "departure_time": 0.15,
    }
    if preferences:
        weights.update(preferences)

    # ── Normalize values to 0-100 scale ───────────────────────
    prices = [f["price"] for f in flights]
    durations = [f["duration_hours"] for f in flights]
    stops_list = [f["stops"] for f in flights]

    min_price, max_price = min(prices), max(prices)
    min_dur, max_dur = min(durations), max(durations)
    min_stops, max_stops = min(stops_list), max(stops_list)

    def normalize(value, min_val, max_val, invert=True):
        """Normalize to 0-100. Invert=True means lower is better."""
        if max_val == min_val:
            return 100.0
        score = ((value - min_val) / (max_val - min_val)) * 100
        return (100 - score) if invert else score

    def departure_score(dep_time_str: str) -> float:
        """Score departure time — prefer 6AM-10AM and 4PM-8PM."""
        try:
            time_part = dep_time_str.split("T")[1] if "T" in dep_time_str else dep_time_str
            hour = int(time_part.split(":")[0])
        except (IndexError, ValueError):
            return 50.0

        # Preferred windows
        if 6 <= hour <= 10:
            return 90.0 + (10 - abs(hour - 8)) * 2  # Peak around 8 AM
        elif 16 <= hour <= 20:
            return 80.0 + (10 - abs(hour - 18)) * 2  # Peak around 6 PM
        elif 10 < hour < 16:
            return 60.0
        else:
            return 30.0  # Very early or very late

    # ── Score each flight ─────────────────────────────────────
    scored_flights = []
    for flight in flights:
        price_score = normalize(flight["price"], min_price, max_price, invert=True)
        duration_score = normalize(flight["duration_hours"], min_dur, max_dur, invert=True)
        stops_score = normalize(flight["stops"], min_stops, max_stops, invert=True)
        dep_score = departure_score(flight["departure_time"])

        total_score = (
            weights["price"] * price_score +
            weights["duration"] * duration_score +
            weights["stops"] * stops_score +
            weights["departure_time"] * dep_score
        )

        scored = flight.copy()
        scored["score"] = round(total_score, 1)
        scored["score_breakdown"] = {
            "price": round(price_score, 1),
            "duration": round(duration_score, 1),
            "stops": round(stops_score, 1),
            "departure_time": round(dep_score, 1),
        }
        scored_flights.append(scored)

    # Sort by total score (highest = best)
    scored_flights.sort(key=lambda f: f["score"], reverse=True)

    # Assign ranks
    for i, flight in enumerate(scored_flights):
        flight["rank"] = i + 1

    # ── Identify special tags ─────────────────────────────────
    tags = {}
    cheapest = min(scored_flights, key=lambda f: f["price"])
    fastest = min(scored_flights, key=lambda f: f["duration_hours"])
    fewest_stops = min(scored_flights, key=lambda f: f["stops"])

    def add_tag(flight_num, tag):
        if flight_num not in tags:
            tags[flight_num] = []
        tags[flight_num].append(tag)

    add_tag(cheapest["flight_number"], "💰 Cheapest")
    add_tag(fastest["flight_number"], "⚡ Fastest")
    if fewest_stops["stops"] < max_stops:
        add_tag(fewest_stops["flight_number"], "✈️ Fewest Stops")

    recommended = scored_flights[0]
    if recommended["flight_number"] not in tags:
        tags[recommended["flight_number"]] = []
    tags[recommended["flight_number"]].insert(0, "⭐ Recommended")

    # ── Build recommendation reason ───────────────────────────
    reasons = []
    rec_tags = tags.get(recommended["flight_number"], [])
    if "💰 Cheapest" in rec_tags:
        reasons.append("the most affordable option")
    if "⚡ Fastest" in rec_tags:
        reasons.append("the shortest flight duration")
    if "✈️ Fewest Stops" in rec_tags:
        reasons.append("a direct flight with no layovers")

    dep_time = recommended["departure_time"].split("T")[1][:5] if "T" in recommended["departure_time"] else ""
    reasons.append(f"a convenient departure at {dep_time}")

    reason_text = (
        f"{recommended['flight_number']} ({recommended['airline']}) is recommended because it offers "
        + ", ".join(reasons[:-1])
        + (f", and {reasons[-1]}" if len(reasons) > 1 else reasons[0])
        + f". Priced at ₹{recommended['price']:,.0f} with a flight time of {recommended['duration_display']}."
    )

    return {
        "success": True,
        "ranked_flights": scored_flights,
        "recommended": recommended,
        "recommendation_reason": reason_text,
        "tags": tags,
        "error": None,
    }


def calculate_fare_difference(original_price: float, new_price: float) -> dict:
    """
    Calculate the fare difference between the original and new flight.

    Returns:
        dict with:
            - fare_difference: Positive = more expensive, Negative = cheaper
            - additional_charge: Amount customer needs to pay (0 if new is cheaper)
            - savings: Amount saved (0 if new is more expensive)
    """
    diff = new_price - original_price

    return {
        "fare_difference": round(diff, 2),
        "additional_charge": round(max(0, diff), 2),
        "savings": round(abs(min(0, diff)), 2),
        "original_price": original_price,
        "new_price": new_price,
    }


# ── Standalone testing ────────────────────────────────────────
if __name__ == "__main__":
    from flight_search_service import search_flights

    print("\n🔍 Flight Comparison Test")
    print("=" * 60)

    # Get mock flights
    search_result = search_flights("DEL", "BOM", "2025-07-23", max_results=5)
    flights = search_result["flights"]

    # Compare them
    result = compare_flights(flights)

    print(f"\n📊 Ranked {len(result['ranked_flights'])} flights:\n")
    for f in result["ranked_flights"]:
        dep = f["departure_time"].split("T")[1][:5]
        tag_str = " | ".join(result["tags"].get(f["flight_number"], []))
        print(
            f"  #{f['rank']} Score: {f['score']:5.1f} | "
            f"{f['flight_number']:8s} | ₹{f['price']:>8,.0f} | "
            f"{f['duration_display']:6s} | {f['stops']} stops | "
            f"{dep} | {tag_str}"
        )

    print(f"\n🏆 Recommendation: {result['recommendation_reason']}")
