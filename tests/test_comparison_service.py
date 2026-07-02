"""
Tests for the Flight Comparison Service.

Tests ranking algorithm, tag assignment, and fare difference calculation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.services.comparison_service import compare_flights, calculate_fare_difference


class TestComparisonService:
    """Test cases for the ComparisonService."""

    @staticmethod
    def _make_flights():
        """Create sample flight data for testing."""
        return [
            {
                "flight_number": "AI101",
                "airline": "Air India",
                "airline_code": "AI",
                "origin": "DEL",
                "destination": "BOM",
                "departure_time": "2026-07-23T08:00:00",
                "arrival_time": "2026-07-23T10:15:00",
                "duration_hours": 2.25,
                "duration_display": "2h 15m",
                "stops": 0,
                "price": 6500,
                "currency": "INR",
                "source": "mock_data",
            },
            {
                "flight_number": "6E202",
                "airline": "IndiGo",
                "airline_code": "6E",
                "origin": "DEL",
                "destination": "BOM",
                "departure_time": "2026-07-23T14:30:00",
                "arrival_time": "2026-07-23T16:45:00",
                "duration_hours": 2.25,
                "duration_display": "2h 15m",
                "stops": 0,
                "price": 4800,
                "currency": "INR",
                "source": "mock_data",
            },
            {
                "flight_number": "SG303",
                "airline": "SpiceJet",
                "airline_code": "SG",
                "origin": "DEL",
                "destination": "BOM",
                "departure_time": "2026-07-23T06:00:00",
                "arrival_time": "2026-07-23T09:30:00",
                "duration_hours": 3.5,
                "duration_display": "3h 30m",
                "stops": 1,
                "price": 3500,
                "currency": "INR",
                "source": "mock_data",
            },
        ]

    def test_compare_returns_ranked_flights(self):
        """Should rank and return all flights with scores."""
        result = compare_flights(self._make_flights())
        assert result["success"] is True
        assert len(result["ranked_flights"]) == 3
        # All flights should have scores
        for f in result["ranked_flights"]:
            assert "score" in f
            assert "rank" in f
            assert f["score"] > 0

    def test_ranking_order(self):
        """Ranked flights should be sorted by score descending."""
        result = compare_flights(self._make_flights())
        scores = [f["score"] for f in result["ranked_flights"]]
        assert scores == sorted(scores, reverse=True)

    def test_recommended_is_top_ranked(self):
        """Recommended flight should be the highest-scored."""
        result = compare_flights(self._make_flights())
        recommended = result["recommended"]
        top_ranked = result["ranked_flights"][0]
        assert recommended["flight_number"] == top_ranked["flight_number"]

    def test_tags_assigned(self):
        """Cheapest, fastest, and recommended tags should be assigned."""
        result = compare_flights(self._make_flights())
        tags = result["tags"]
        # Should have at least cheapest and fastest tags
        all_tags = [tag for tag_list in tags.values() for tag in tag_list]
        assert any("Cheapest" in t for t in all_tags)
        assert any("Fastest" in t for t in all_tags)

    def test_recommendation_reason_not_empty(self):
        """Recommendation reason should be a non-empty string."""
        result = compare_flights(self._make_flights())
        assert len(result["recommendation_reason"]) > 20

    def test_single_flight(self):
        """Should handle a single flight correctly."""
        flights = [self._make_flights()[0]]
        result = compare_flights(flights)
        assert result["success"] is True
        assert result["recommended"]["flight_number"] == "AI101"
        assert result["ranked_flights"][0]["score"] == 100.0

    def test_empty_flights_list(self):
        """Should handle empty list."""
        result = compare_flights([])
        assert result["success"] is False
        assert "No flights" in result["error"]

    def test_score_breakdown_present(self):
        """Each ranked flight should have a score breakdown."""
        result = compare_flights(self._make_flights())
        for f in result["ranked_flights"]:
            assert "score_breakdown" in f
            breakdown = f["score_breakdown"]
            assert "price" in breakdown
            assert "duration" in breakdown
            assert "stops" in breakdown
            assert "departure_time" in breakdown


class TestFareDifference:
    """Test cases for fare difference calculation."""

    def test_more_expensive_new_flight(self):
        """New flight costs more than original."""
        result = calculate_fare_difference(5000, 7500)
        assert result["fare_difference"] == 2500
        assert result["additional_charge"] == 2500
        assert result["savings"] == 0

    def test_cheaper_new_flight(self):
        """New flight costs less than original."""
        result = calculate_fare_difference(8000, 5000)
        assert result["fare_difference"] == -3000
        assert result["additional_charge"] == 0
        assert result["savings"] == 3000

    def test_same_price(self):
        """Same price should result in zero difference."""
        result = calculate_fare_difference(6000, 6000)
        assert result["fare_difference"] == 0
        assert result["additional_charge"] == 0
        assert result["savings"] == 0
