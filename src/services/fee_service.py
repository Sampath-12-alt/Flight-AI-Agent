"""
Fee Calculation Service.

Calculates rescheduling fees based on airline policies and booking details.
Uses deterministic business rules extracted from policy documents.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


# ── Fee Structures by Airline ─────────────────────────────────
# These are deterministic rules derived from the policy documents.
# In production, these could be loaded from a database or config file.

AIRLINE_FEE_RULES = {
    "Air India": {
        "tiers": [
            {"min_days": 7, "max_days": 999, "fee": 500, "label": "More than 7 days before departure"},
            {"min_days": 3, "max_days": 7, "fee": 1500, "label": "3 to 7 days before departure"},
            {"min_days": 1, "max_days": 3, "fee": 2500, "label": "24 hours to 3 days before departure"},
        ],
        "min_hours_before": 24,
        "max_date_range_days": 90,
    },
    "IndiGo": {
        "tiers": [
            {"min_days": 15, "max_days": 999, "fee": 0, "label": "More than 15 days before departure (free)"},
            {"min_days": 7, "max_days": 15, "fee": 750, "label": "7 to 15 days before departure"},
            {"min_days": 3, "max_days": 7, "fee": 1750, "label": "3 to 7 days before departure"},
            {"min_days": 0, "max_days": 3, "fee": 3000, "label": "Less than 3 days before departure"},
        ],
        "min_hours_before": 2,
        "max_date_range_days": 60,
    },
    "SpiceJet": {
        "tiers": [
            {"min_days": 10, "max_days": 999, "fee": 500, "label": "More than 10 days before departure"},
            {"min_days": 4, "max_days": 10, "fee": 1250, "label": "4 to 10 days before departure"},
            {"min_days": 1, "max_days": 4, "fee": 2000, "label": "24 hours to 4 days before departure"},
            {"min_days": 0, "max_days": 1, "fee": 3500, "label": "6 hours to 24 hours before departure"},
        ],
        "min_hours_before": 6,
        "max_date_range_days": 45,
    },
    "Vistara": {
        "tiers": [
            {"min_days": 14, "max_days": 999, "fee": 250, "label": "More than 14 days before departure"},
            {"min_days": 7, "max_days": 14, "fee": 1000, "label": "7 to 14 days before departure"},
            {"min_days": 3, "max_days": 7, "fee": 2000, "label": "3 to 7 days before departure"},
            {"min_days": 0, "max_days": 3, "fee": 3000, "label": "Less than 3 days before departure"},
        ],
        "min_hours_before": 4,
        "max_date_range_days": 120,
    },
}


def calculate_rescheduling_fee(booking: dict, new_date: str) -> dict:
    """
    Calculate the rescheduling fee for a booking.

    Args:
        booking: Booking details dict (from BookingService)
        new_date: Requested new travel date (YYYY-MM-DD format)

    Returns:
        dict with fee calculation result:
        {
            "success": bool,
            "fee_amount": float,
            "fee_tier": str,
            "explanation": str,
            "eligible": bool,
            "error": str | None
        }
    """
    airline = booking.get("airline", "")

    # Check if airline is supported
    if airline not in AIRLINE_FEE_RULES:
        return {
            "success": False,
            "fee_amount": 0,
            "fee_tier": "",
            "explanation": "",
            "eligible": False,
            "error": f"Fee rules not available for airline: {airline}",
        }

    # Check if booking is eligible (must be Confirmed)
    if booking.get("status", "").lower() != "confirmed":
        return {
            "success": False,
            "fee_amount": 0,
            "fee_tier": "",
            "explanation": "",
            "eligible": False,
            "error": f"Booking status is '{booking.get('status')}'. Only confirmed bookings can be rescheduled.",
        }

    # Parse dates
    try:
        current_date = datetime.strptime(booking["travel_date"], "%Y-%m-%d")
    except (ValueError, KeyError):
        return {
            "success": False,
            "fee_amount": 0,
            "fee_tier": "",
            "explanation": "",
            "eligible": False,
            "error": f"Invalid current travel date in booking: {booking.get('travel_date')}",
        }

    try:
        requested_date = datetime.strptime(new_date, "%Y-%m-%d")
    except ValueError:
        return {
            "success": False,
            "fee_amount": 0,
            "fee_tier": "",
            "explanation": "",
            "eligible": False,
            "error": f"Invalid requested date format: '{new_date}'. Use YYYY-MM-DD format.",
        }

    # Check if new date is same as current
    if current_date == requested_date:
        return {
            "success": False,
            "fee_amount": 0,
            "fee_tier": "",
            "explanation": "",
            "eligible": False,
            "error": "The requested date is the same as the current travel date.",
        }

    rules = AIRLINE_FEE_RULES[airline]

    # Check date range restriction
    date_diff = abs((requested_date - current_date).days)
    if date_diff > rules["max_date_range_days"]:
        return {
            "success": False,
            "fee_amount": 0,
            "fee_tier": "",
            "explanation": "",
            "eligible": False,
            "error": (
                f"The new travel date must be within {rules['max_date_range_days']} days "
                f"of the original date. Requested change: {date_diff} days."
            ),
        }

    # Calculate days until departure (from today)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    days_until_departure = (current_date - today).days

    if days_until_departure < 0:
        return {
            "success": False,
            "fee_amount": 0,
            "fee_tier": "",
            "explanation": "",
            "eligible": False,
            "error": "The original travel date has already passed. Rescheduling is not possible.",
        }

    # Determine fee tier
    applicable_fee = None
    applicable_tier = None

    for tier in rules["tiers"]:
        if tier["min_days"] <= days_until_departure < tier["max_days"]:
            applicable_fee = tier["fee"]
            applicable_tier = tier["label"]
            break

    if applicable_fee is None:
        # Default to highest fee tier
        last_tier = rules["tiers"][-1]
        applicable_fee = last_tier["fee"]
        applicable_tier = last_tier["label"]

    # Build explanation
    explanation = (
        f"Airline: {airline}\n"
        f"Days until departure: {days_until_departure}\n"
        f"Fee tier: {applicable_tier}\n"
        f"Rescheduling fee: ₹{applicable_fee:,.0f}\n"
        f"Original date: {booking['travel_date']}\n"
        f"New date: {new_date}"
    )

    return {
        "success": True,
        "fee_amount": applicable_fee,
        "fee_tier": applicable_tier,
        "explanation": explanation,
        "eligible": True,
        "error": None,
    }


def calculate_total_cost(
    rescheduling_fee: float,
    original_price: float,
    new_flight_price: float,
) -> dict:
    """
    Calculate the total cost including rescheduling fee and fare difference.

    Args:
        rescheduling_fee: The policy-based rescheduling fee
        original_price: Original ticket price from the booking
        new_flight_price: Price of the recommended new flight

    Returns:
        dict with cost breakdown:
        {
            "rescheduling_fee": float,
            "fare_difference": float,
            "additional_fare_charge": float,
            "savings": float,
            "total_additional_cost": float,
            "explanation": str
        }
    """
    fare_diff = new_flight_price - original_price
    additional_fare = max(0, fare_diff)
    savings = abs(min(0, fare_diff))
    total = rescheduling_fee + additional_fare

    explanation_parts = [
        f"Rescheduling Fee: ₹{rescheduling_fee:,.0f}",
    ]

    if fare_diff > 0:
        explanation_parts.append(
            f"Fare Difference: +₹{fare_diff:,.0f} "
            f"(New fare ₹{new_flight_price:,.0f} vs Original ₹{original_price:,.0f})"
        )
    elif fare_diff < 0:
        explanation_parts.append(
            f"Fare Savings: -₹{abs(fare_diff):,.0f} "
            f"(New fare ₹{new_flight_price:,.0f} vs Original ₹{original_price:,.0f})"
        )
    else:
        explanation_parts.append("No fare difference.")

    explanation_parts.append(f"Total Additional Cost: ₹{total:,.0f}")

    return {
        "rescheduling_fee": rescheduling_fee,
        "fare_difference": round(fare_diff, 2),
        "additional_fare_charge": round(additional_fare, 2),
        "savings": round(savings, 2),
        "total_additional_cost": round(total, 2),
        "explanation": "\n".join(explanation_parts),
    }

