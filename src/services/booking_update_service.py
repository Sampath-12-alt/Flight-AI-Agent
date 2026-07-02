"""
Booking Update Service.

Updates the booking record in the database with the new travel date.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.database.sqlite import update_booking_date, get_booking


def update_booking(booking_id: str, new_date: str) -> dict:
    """
    Update a booking with a new travel date.

    Args:
        booking_id: The booking identifier
        new_date: New travel date in YYYY-MM-DD format

    Returns:
        dict with update result:
        {
            "success": bool,
            "booking_id": str,
            "previous_date": str,
            "new_date": str,
            "updated_booking": dict | None,
            "error": str | None
        }
    """
    if not booking_id or not new_date:
        return {
            "success": False,
            "booking_id": booking_id,
            "previous_date": "",
            "new_date": new_date,
            "updated_booking": None,
            "error": "Both booking_id and new_date are required.",
        }

    # Get current booking for previous date
    current = get_booking(booking_id)
    if current is None:
        return {
            "success": False,
            "booking_id": booking_id,
            "previous_date": "",
            "new_date": new_date,
            "updated_booking": None,
            "error": f"Booking '{booking_id}' not found.",
        }

    previous_date = current["travel_date"]

    # Perform the update
    updated = update_booking_date(booking_id, new_date)

    if updated is None:
        return {
            "success": False,
            "booking_id": booking_id,
            "previous_date": previous_date,
            "new_date": new_date,
            "updated_booking": None,
            "error": "Failed to update booking. Database error.",
        }

    return {
        "success": True,
        "booking_id": booking_id,
        "previous_date": previous_date,
        "new_date": new_date,
        "updated_booking": updated,
        "error": None,
    }
