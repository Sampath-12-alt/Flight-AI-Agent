"""
Booking Service.

Retrieves booking information from the SQLite database.
Validates booking ID format and handles not-found cases.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.database.sqlite import get_booking, get_all_bookings


def lookup_booking(booking_id: str) -> dict:
    """
    Look up a booking by its ID.

    Args:
        booking_id: The booking identifier (e.g., "BK1024")

    Returns:
        dict with booking details and status information:
        {
            "success": bool,
            "booking": dict | None,
            "error": str | None
        }
    """
    # Validate booking ID format
    if not booking_id:
        return {
            "success": False,
            "booking": None,
            "error": "Booking ID is required.",
        }

    # Normalize: strip whitespace, uppercase
    booking_id = booking_id.strip().upper()

    # Validate format (BK followed by digits)
    if not re.match(r"^BK\d{4,}$", booking_id):
        return {
            "success": False,
            "booking": None,
            "error": f"Invalid Booking ID format: '{booking_id}'. Expected format: BK followed by 4+ digits (e.g., BK1024).",
        }

    # Query database
    booking = get_booking(booking_id)

    if booking is None:
        return {
            "success": False,
            "booking": None,
            "error": f"Booking '{booking_id}' not found in the system.",
        }

    return {
        "success": True,
        "booking": booking,
        "error": None,
    }


def list_bookings() -> list[dict]:
    """Return all bookings in the system."""
    return get_all_bookings()
