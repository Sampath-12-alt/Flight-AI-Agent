"""
Tests for the Date Parser Service.

Tests keyword parsing, flexible date interpretation, and edge cases.
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.services.date_parser_service import parse_flexible_dates


class TestDateParserService:
    """Test cases for the DateParserService."""

    # Use a fixed reference date for deterministic tests
    REF = datetime(2026, 7, 2, 10, 0, 0)  # Thursday, July 2, 2026

    def test_tomorrow(self):
        """Should return tomorrow's date."""
        result = parse_flexible_dates("tomorrow", self.REF)
        assert result["success"] is True
        assert result["dates"] == ["2026-07-03"]
        assert result["method"] == "keyword"

    def test_today(self):
        """Should return today's date."""
        result = parse_flexible_dates("today", self.REF)
        assert result["success"] is True
        assert result["dates"] == ["2026-07-02"]

    def test_day_after_tomorrow(self):
        """Should return the day after tomorrow."""
        result = parse_flexible_dates("day after tomorrow", self.REF)
        assert result["success"] is True
        assert result["dates"] == ["2026-07-04"]

    def test_next_week(self):
        """Should return 7 dates for next week (Mon-Sun)."""
        result = parse_flexible_dates("next week", self.REF)
        assert result["success"] is True
        assert len(result["dates"]) == 7
        # First date should be next Monday
        assert result["dates"][0] == "2026-07-06"
        # Last date should be next Sunday
        assert result["dates"][6] == "2026-07-12"

    def test_this_weekend(self):
        """Should return Saturday and Sunday."""
        result = parse_flexible_dates("this weekend", self.REF)
        assert result["success"] is True
        assert len(result["dates"]) == 2
        # Saturday July 4 and Sunday July 5
        assert result["dates"][0] == "2026-07-04"
        assert result["dates"][1] == "2026-07-05"

    def test_next_weekend(self):
        """Should return next Saturday and Sunday."""
        result = parse_flexible_dates("next weekend", self.REF)
        assert result["success"] is True
        assert len(result["dates"]) == 2
        assert result["dates"][0] == "2026-07-11"
        assert result["dates"][1] == "2026-07-12"

    def test_specific_date_month_day(self):
        """Should parse 'July 15'."""
        result = parse_flexible_dates("July 15", self.REF)
        assert result["success"] is True
        assert result["dates"] == ["2026-07-15"]

    def test_specific_date_iso(self):
        """Should parse YYYY-MM-DD format."""
        result = parse_flexible_dates("2026-08-10", self.REF)
        assert result["success"] is True
        assert result["dates"] == ["2026-08-10"]

    def test_any_day_in_month(self):
        """Should return all days in the specified month."""
        result = parse_flexible_dates("any day in august", self.REF)
        assert result["success"] is True
        assert len(result["dates"]) == 31  # August has 31 days
        assert result["dates"][0] == "2026-08-01"

    def test_next_month(self):
        """Should return all days in next month."""
        result = parse_flexible_dates("next month", self.REF)
        assert result["success"] is True
        assert len(result["dates"]) == 31  # August has 31 days

    def test_empty_phrase(self):
        """Should fail with empty phrase."""
        result = parse_flexible_dates("", self.REF)
        assert result["success"] is False

    def test_interpretation_not_empty(self):
        """Should always return an interpretation."""
        result = parse_flexible_dates("next week", self.REF)
        assert len(result["interpretation"]) > 5

    def test_method_is_keyword(self):
        """Common phrases should use keyword method (no API call)."""
        for phrase in ["tomorrow", "next week", "this weekend", "July 15"]:
            result = parse_flexible_dates(phrase, self.REF)
            assert result["method"] == "keyword", f"'{phrase}' should use keyword method"
