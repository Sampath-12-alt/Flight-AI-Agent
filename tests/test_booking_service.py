"""
Tests for the Booking Service.

Tests booking lookup, ID validation, and error handling.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.database.sqlite import init_db, seed_sample_data
from src.services.booking_service import lookup_booking


@pytest.fixture(autouse=True, scope="module")
def setup_database():
    """Initialize and seed the database before tests."""
    init_db()
    seed_sample_data()


class TestBookingService:
    """Test cases for the BookingService."""

    def test_valid_booking_lookup(self):
        """FR-04: Successfully retrieve a valid booking."""
        result = lookup_booking("BK1024")
        assert result["success"] is True
        assert result["booking"] is not None
        assert result["booking"]["booking_id"] == "BK1024"
        assert result["booking"]["customer_name"] == "Rahul Sharma"
        assert result["booking"]["airline"] == "Air India"
        assert result["error"] is None

    def test_booking_not_found(self):
        """FR-10: Handle non-existent booking ID."""
        result = lookup_booking("BK9999")
        assert result["success"] is False
        assert result["booking"] is None
        assert "not found" in result["error"].lower()

    def test_invalid_booking_id_format(self):
        """FR-10: Reject invalid booking ID format."""
        result = lookup_booking("INVALID123")
        assert result["success"] is False
        assert "Invalid Booking ID format" in result["error"]

    def test_empty_booking_id(self):
        """FR-10: Handle empty booking ID."""
        result = lookup_booking("")
        assert result["success"] is False
        assert "required" in result["error"].lower()

    def test_booking_id_normalization(self):
        """Booking IDs should be case-insensitive."""
        result = lookup_booking("bk1024")
        assert result["success"] is True
        assert result["booking"]["booking_id"] == "BK1024"

    def test_booking_has_required_fields(self):
        """FR-04: Booking should contain all required fields."""
        result = lookup_booking("BK1024")
        booking = result["booking"]
        required_fields = [
            "booking_id", "customer_name", "airline",
            "origin", "origin_code", "destination", "destination_code",
            "travel_date", "status", "ticket_price",
        ]
        for field in required_fields:
            assert field in booking, f"Missing field: {field}"

    def test_cancelled_booking_retrieval(self):
        """Should retrieve cancelled bookings (fee service handles eligibility)."""
        result = lookup_booking("BK1033")
        assert result["success"] is True
        assert result["booking"]["status"] == "Cancelled"
