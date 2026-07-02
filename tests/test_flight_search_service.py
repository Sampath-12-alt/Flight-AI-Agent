"""
Tests for the Flight Search Service.

Tests mock data generation and result structure.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.services.flight_search_service import search_flights


class TestFlightSearchService:
    """Test cases for the FlightSearchService (mock mode)."""

    def test_search_returns_flights(self):
        """Should return flights for a valid route and date."""
        result = search_flights("DEL", "BOM", "2026-07-23", max_results=5)
        assert result["success"] is True
        assert result["num_results"] > 0
        assert len(result["flights"]) <= 5

    def test_search_returns_correct_structure(self):
        """Each flight should have all required fields."""
        result = search_flights("DEL", "BOM", "2026-07-23", max_results=3)
        required_fields = [
            "flight_number", "airline", "airline_code", "origin",
            "destination", "departure_time", "arrival_time",
            "duration_hours", "duration_display", "stops",
            "price", "currency", "source",
        ]
        for flight in result["flights"]:
            for field in required_fields:
                assert field in flight, f"Missing field: {field}"

    def test_mock_source_label(self):
        """Mock results should be labeled correctly."""
        result = search_flights("DEL", "BOM", "2026-07-23")
        assert result["source"] in ["mock_data", "aviationstack_api"]
        for flight in result["flights"]:
            assert flight["source"] in ["mock_data", "aviationstack_api"]

    def test_deterministic_results(self):
        """Same route+date should return consistent results."""
        r1 = search_flights("DEL", "BOM", "2026-07-23", max_results=3)
        r2 = search_flights("DEL", "BOM", "2026-07-23", max_results=3)
        # Same number of results
        assert r1["num_results"] == r2["num_results"]
        # Same prices (deterministic seeding)
        prices1 = [f["price"] for f in r1["flights"]]
        prices2 = [f["price"] for f in r2["flights"]]
        assert prices1 == prices2

    def test_different_routes_give_different_results(self):
        """Different routes should produce different flight sets."""
        r1 = search_flights("DEL", "BOM", "2026-07-23", max_results=3)
        r2 = search_flights("BLR", "MAA", "2026-07-23", max_results=3)
        prices1 = [f["price"] for f in r1["flights"]]
        prices2 = [f["price"] for f in r2["flights"]]
        assert prices1 != prices2

    def test_flight_prices_are_positive(self):
        """All flight prices should be positive."""
        result = search_flights("BOM", "GOI", "2026-08-01")
        for flight in result["flights"]:
            assert flight["price"] > 0

    def test_duration_is_reasonable(self):
        """Flight duration should be between 0.5 and 8 hours for domestic."""
        result = search_flights("DEL", "BOM", "2026-07-23")
        for flight in result["flights"]:
            assert 0.5 <= flight["duration_hours"] <= 8

    def test_empty_origin_rejected(self):
        """Should fail with empty origin."""
        result = search_flights("", "BOM", "2026-07-23")
        assert result["success"] is False

    def test_empty_date_rejected(self):
        """Should fail with empty date."""
        result = search_flights("DEL", "BOM", "")
        assert result["success"] is False

    def test_max_results_respected(self):
        """Should not return more than max_results flights."""
        result = search_flights("DEL", "BOM", "2026-07-23", max_results=2)
        assert len(result["flights"]) <= 2
