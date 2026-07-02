"""
Tests for the Fee Calculation Service.

Tests fee calculation for each airline, edge cases, and error handling.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from datetime import datetime, timedelta
from src.services.fee_service import calculate_rescheduling_fee


class TestFeeService:
    """Test cases for the FeeService."""

    # ── Sample booking fixtures ─────────────────────────────

    @staticmethod
    def _make_booking(airline: str, travel_date: str = None, status: str = "Confirmed"):
        """Create a test booking dict."""
        if travel_date is None:
            # Default to 10 days from now
            travel_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        return {
            "booking_id": "BK_TEST",
            "customer_name": "Test User",
            "airline": airline,
            "origin": "Delhi",
            "destination": "Mumbai",
            "travel_date": travel_date,
            "status": status,
            "ticket_price": 8000.0,
        }

    # ── Air India Tests ─────────────────────────────────────

    def test_air_india_fee_more_than_7_days(self):
        """Air India: ₹500 when more than 7 days before departure."""
        future_date = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
        new_date = (datetime.now() + timedelta(days=18)).strftime("%Y-%m-%d")
        booking = self._make_booking("Air India", future_date)
        result = calculate_rescheduling_fee(booking, new_date)
        assert result["success"] is True
        assert result["fee_amount"] == 500

    def test_air_india_fee_3_to_7_days(self):
        """Air India: ₹1,500 when 3-7 days before departure."""
        future_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        new_date = (datetime.now() + timedelta(days=8)).strftime("%Y-%m-%d")
        booking = self._make_booking("Air India", future_date)
        result = calculate_rescheduling_fee(booking, new_date)
        assert result["success"] is True
        assert result["fee_amount"] == 1500

    def test_air_india_fee_1_to_3_days(self):
        """Air India: ₹2,500 when 1-3 days before departure."""
        future_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        new_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        booking = self._make_booking("Air India", future_date)
        result = calculate_rescheduling_fee(booking, new_date)
        assert result["success"] is True
        assert result["fee_amount"] == 2500

    # ── IndiGo Tests ────────────────────────────────────────

    def test_indigo_free_change_over_15_days(self):
        """IndiGo: Free date change when more than 15 days before departure."""
        future_date = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d")
        new_date = (datetime.now() + timedelta(days=25)).strftime("%Y-%m-%d")
        booking = self._make_booking("IndiGo", future_date)
        result = calculate_rescheduling_fee(booking, new_date)
        assert result["success"] is True
        assert result["fee_amount"] == 0

    # ── Error Cases ─────────────────────────────────────────

    def test_cancelled_booking_rejected(self):
        """FR-10: Cancelled bookings should not be eligible."""
        booking = self._make_booking("Air India", status="Cancelled")
        new_date = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
        result = calculate_rescheduling_fee(booking, new_date)
        assert result["success"] is False
        assert result["eligible"] is False
        assert "Cancelled" in result["error"]

    def test_same_date_rejected(self):
        """FR-10: Reject if new date equals current date."""
        future_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        booking = self._make_booking("Air India", future_date)
        result = calculate_rescheduling_fee(booking, future_date)
        assert result["success"] is False
        assert "same" in result["error"].lower()

    def test_invalid_date_format(self):
        """FR-10: Reject invalid date format."""
        booking = self._make_booking("Air India")
        result = calculate_rescheduling_fee(booking, "not-a-date")
        assert result["success"] is False
        assert "Invalid" in result["error"]

    def test_unsupported_airline(self):
        """FR-10: Handle unsupported airline."""
        booking = self._make_booking("Unknown Airline")
        new_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        result = calculate_rescheduling_fee(booking, new_date)
        assert result["success"] is False
        assert "not available" in result["error"].lower()

    def test_past_travel_date(self):
        """FR-10: Reject if original date has passed."""
        past_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        new_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        booking = self._make_booking("Air India", past_date)
        result = calculate_rescheduling_fee(booking, new_date)
        assert result["success"] is False
        assert "passed" in result["error"].lower()

    def test_date_range_exceeded(self):
        """FR-10: Reject if new date exceeds maximum range."""
        future_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        far_date = (datetime.now() + timedelta(days=200)).strftime("%Y-%m-%d")
        booking = self._make_booking("Air India", future_date)
        result = calculate_rescheduling_fee(booking, far_date)
        assert result["success"] is False
        assert "within" in result["error"].lower()

    def test_fee_result_has_explanation(self):
        """Successful fee calculation should include explanation."""
        future_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        new_date = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
        booking = self._make_booking("Vistara", future_date)
        result = calculate_rescheduling_fee(booking, new_date)
        assert result["success"] is True
        assert result["explanation"] != ""
        assert result["fee_tier"] != ""
