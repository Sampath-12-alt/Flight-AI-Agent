"""
Tests for the NLU Service.

Tests spelling correction, city alias resolution, informal language
normalization, and clean query passthrough.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.services.nlu_service import normalize_query, _normalize_local


class TestSpellingCorrections:
    """Test common travel-related spelling mistakes."""

    def test_flight_misspellings(self):
        """NLU should correct common flight misspellings."""
        for misspelling in ["flite", "fligt", "flyt", "fligth", "flght"]:
            result = normalize_query(f"find {misspelling} to mumbai")
            assert "flight" in result["normalized"].lower(), \
                f"Failed to correct '{misspelling}'"
            assert len(result["corrections"]) > 0

    def test_reschedule_misspellings(self):
        """NLU should correct reschedule misspellings."""
        for misspelling in ["reschdule", "reshedule", "rescedule"]:
            result = normalize_query(f"{misspelling} booking BK1024")
            assert "reschedule" in result["normalized"].lower(), \
                f"Failed to correct '{misspelling}'"

    def test_booking_misspellings(self):
        """NLU should correct booking misspellings."""
        result = normalize_query("my boooking id is BK1024")
        assert "booking" in result["normalized"].lower()

    def test_city_misspellings(self):
        """NLU should correct misspelled city names."""
        test_cases = {
            "mumbii": "Mumbai",
            "banglore": "Bangalore",
            "hydrabad": "Hyderabad",
            "hyderbad": "Hyderabad",
            "chenai": "Chennai",
            "kolkatta": "Kolkata",
        }
        for misspelled, correct in test_cases.items():
            result = normalize_query(f"flights from delhi to {misspelled}")
            assert correct.lower() in result["normalized"].lower(), \
                f"Failed to correct city '{misspelled}' to '{correct}'. Got: '{result['normalized']}'"

    def test_cheapest_misspellings(self):
        """NLU should correct price-related misspellings."""
        for misspelling in ["cheepest", "cheapst", "cheepst"]:
            result = normalize_query(f"{misspelling} flight")
            assert "cheapest" in result["normalized"].lower(), \
                f"Failed to correct '{misspelling}'"

    def test_change_misspellings(self):
        """NLU should correct action word misspellings."""
        result = normalize_query("chnge my ticket to july 28")
        assert "change" in result["normalized"].lower()


class TestCityAliases:
    """Test city abbreviation and alias resolution."""

    def test_common_abbreviations(self):
        """NLU should expand common city abbreviations."""
        test_cases = {
            "hyd": "Hyderabad",
            "blr": "Bangalore",
            "mum": "Mumbai",
            "del": "Delhi",
            "maa": "Chennai",
            "ccu": "Kolkata",
        }
        for abbrev, full_name in test_cases.items():
            result = normalize_query(f"flights from {abbrev} to delhi")
            assert full_name.lower() in result["normalized"].lower(), \
                f"Failed to expand '{abbrev}' to '{full_name}'. Got: '{result['normalized']}'"
            assert len(result["city_mappings"]) > 0

    def test_historical_names(self):
        """NLU should recognize historical city names."""
        test_cases = {
            "madras": "Chennai",
            "calcutta": "Kolkata",
            "bombay": "Mumbai",
        }
        for old_name, new_name in test_cases.items():
            result = normalize_query(f"flights from {old_name}")
            assert new_name.lower() in result["normalized"].lower(), \
                f"Failed to map '{old_name}' to '{new_name}'. Got: '{result['normalized']}'"

    def test_vizag_alias(self):
        """NLU should recognize Vizag as Visakhapatnam."""
        result = normalize_query("flights from vizag to mumbai")
        assert "visakhapatnam" in result["normalized"].lower()


class TestInformalLanguage:
    """Test informal abbreviation normalization."""

    def test_date_abbreviations(self):
        """NLU should expand date abbreviations."""
        test_cases = {
            "nxt": "next",
            "tmrw": "tomorrow",
            "tmw": "tomorrow",
            "2morrow": "tomorrow",
        }
        for abbrev, expanded in test_cases.items():
            result = normalize_query(f"flight {abbrev} week")
            assert expanded in result["normalized"].lower(), \
                f"Failed to expand '{abbrev}' to '{expanded}'. Got: '{result['normalized']}'"

    def test_informal_prepositions(self):
        """NLU should expand informal prepositions."""
        result = normalize_query("flight frm delhi")
        assert "from" in result["normalized"].lower()


class TestMixedQueries:
    """Test complex queries with multiple issues."""

    def test_spelling_plus_abbreviation(self):
        """NLU should handle spelling + abbreviation in same query."""
        result = normalize_query("cheapest flight from hyd to mum nxt week")
        normalized_lower = result["normalized"].lower()
        assert "cheapest" in normalized_lower or "cheapest" in normalized_lower
        assert "hyderabad" in normalized_lower
        assert "mumbai" in normalized_lower
        assert "next" in normalized_lower
        assert len(result["corrections"]) >= 3

    def test_city_misspelling_plus_informal(self):
        """NLU should handle city misspelling + informal date."""
        result = normalize_query("find fligts hyd to mumbii tmrw")
        normalized_lower = result["normalized"].lower()
        assert "flight" in normalized_lower
        assert "hyderabad" in normalized_lower
        assert "mumbai" in normalized_lower
        assert "tomorrow" in normalized_lower

    def test_rescheduling_with_misspellings(self):
        """NLU should handle rescheduling with misspellings."""
        result = normalize_query("reschdule boooking BK1024 to july 28")
        normalized_lower = result["normalized"].lower()
        assert "reschedule" in normalized_lower
        assert "booking" in normalized_lower
        assert "BK1024" in result["normalized"]  # Booking ID preserved

    def test_move_flight_informal(self):
        """NLU should handle informal rescheduling requests."""
        result = normalize_query("mov my flite to friday")
        normalized_lower = result["normalized"].lower()
        assert "move" in normalized_lower
        assert "flight" in normalized_lower

    def test_booking_id_preserved(self):
        """Booking IDs should not be modified by NLU."""
        result = normalize_query("chnge boooking BK1024 to nxt week")
        assert "BK1024" in result["normalized"]


class TestCleanPassthrough:
    """Test that clean queries pass through unchanged."""

    def test_clean_search_query(self):
        """Clean search queries should not be modified."""
        clean_query = "Find flights from Delhi to Mumbai next week"
        result = normalize_query(clean_query)
        assert result["normalized"] == clean_query
        assert len(result["corrections"]) == 0
        assert result["method"] == "none"

    def test_clean_reschedule_query(self):
        """Clean reschedule queries should not be modified."""
        clean_query = "My booking ID is BK1024. Change my flight to July 23."
        result = normalize_query(clean_query)
        assert result["normalized"] == clean_query
        assert len(result["corrections"]) == 0

    def test_empty_query(self):
        """Empty queries should return safely."""
        result = normalize_query("")
        assert result["normalized"] == ""
        assert result["method"] == "none"

    def test_none_query(self):
        """None queries should return safely."""
        result = normalize_query(None)
        assert result["normalized"] == ""


class TestNormalizationMetadata:
    """Test that metadata is correctly populated."""

    def test_corrections_list_populated(self):
        """Corrections list should describe what was changed."""
        result = normalize_query("cheepest flite from hyd")
        assert len(result["corrections"]) >= 3
        # Each correction should be a descriptive string
        for correction in result["corrections"]:
            assert "→" in correction

    def test_city_mappings_populated(self):
        """City mappings should track alias resolutions."""
        result = normalize_query("flights from hyd to mum")
        assert "hyd" in result["city_mappings"]
        assert "mum" in result["city_mappings"]

    def test_method_is_local(self):
        """Local corrections should report method as 'local'."""
        result = normalize_query("flite from hyd")
        assert result["method"] == "local"

    def test_original_preserved(self):
        """Original query should always be preserved."""
        original = "find fligts hyd to mumbii"
        result = normalize_query(original)
        assert result["original"] == original
