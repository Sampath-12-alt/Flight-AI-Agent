"""
Tests for the Agent Graph.

Tests the end-to-end workflow and helper functions.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.agent.graph import (
    _keyword_intent_detection,
    _regex_entity_extraction,
    _regex_search_extraction,
)
from src.database.sqlite import init_db, seed_sample_data


@pytest.fixture(autouse=True, scope="module")
def setup_database():
    """Initialize and seed the database before tests."""
    init_db()
    seed_sample_data()


class TestKeywordIntentDetection:
    """Test the fallback keyword-based intent detection."""

    # ── Rescheduling ──────────────────────────────────────────
    def test_reschedule_keyword(self):
        assert _keyword_intent_detection("I want to reschedule my flight") == "Flight Rescheduling"

    def test_change_keyword(self):
        assert _keyword_intent_detection("Can you change my flight date?") == "Flight Rescheduling"

    def test_move_keyword(self):
        assert _keyword_intent_detection("Please move my flight to next week") == "Flight Rescheduling"

    def test_modify_keyword(self):
        assert _keyword_intent_detection("I need to modify my booking date") == "Flight Rescheduling"

    def test_new_date_keyword(self):
        assert _keyword_intent_detection("I need a new date for my booking") == "Flight Rescheduling"

    def test_booking_id_pattern(self):
        assert _keyword_intent_detection("BK1024 change to July 23") == "Flight Rescheduling"

    # ── Flight Search ─────────────────────────────────────────
    def test_search_find_keyword(self):
        assert _keyword_intent_detection("Find flights from Delhi to Mumbai") == "Flight Search"

    def test_search_cheapest_keyword(self):
        assert _keyword_intent_detection("I want the cheapest flight to Goa") == "Flight Search"

    def test_search_travel_keyword(self):
        assert _keyword_intent_detection("I want to travel from Hyderabad to Mumbai") == "Flight Search"

    def test_search_show_me_keyword(self):
        assert _keyword_intent_detection("Show me flights from Chennai to Delhi") == "Flight Search"

    def test_search_from_to_pattern(self):
        assert _keyword_intent_detection("from Delhi to Bangalore tomorrow") == "Flight Search"

    # ── Unsupported ───────────────────────────────────────────
    def test_unsupported_cancel(self):
        assert _keyword_intent_detection("I want to cancel my flight") == "Unsupported"

    def test_unsupported_refund(self):
        assert _keyword_intent_detection("I need a refund") == "Unsupported"

    def test_unsupported_random(self):
        assert _keyword_intent_detection("What is the weather today?") == "Unsupported"


class TestRegexEntityExtraction:
    """Test the fallback regex-based entity extraction for rescheduling."""

    def test_extract_booking_id(self):
        booking_id, _ = _regex_entity_extraction("My booking ID is BK1024")
        assert booking_id == "BK1024"

    def test_extract_booking_id_lowercase(self):
        booking_id, _ = _regex_entity_extraction("booking bk1025 needs change")
        assert booking_id == "BK1025"

    def test_extract_date_month_day(self):
        _, new_date = _regex_entity_extraction("Change to July 23")
        assert new_date == "2026-07-23"

    def test_extract_date_day_month(self):
        _, new_date = _regex_entity_extraction("Move to 23 July")
        assert new_date == "2026-07-23"

    def test_extract_date_iso_format(self):
        _, new_date = _regex_entity_extraction("Change to 2026-08-15")
        assert new_date == "2026-08-15"

    def test_extract_both(self):
        booking_id, new_date = _regex_entity_extraction(
            "My booking ID is BK1024. Change my flight to July 23."
        )
        assert booking_id == "BK1024"
        assert new_date == "2026-07-23"

    def test_no_booking_id(self):
        booking_id, _ = _regex_entity_extraction("Change my flight to July 23")
        assert booking_id == ""

    def test_no_date(self):
        _, new_date = _regex_entity_extraction("My booking is BK1024")
        assert new_date == ""


class TestRegexSearchExtraction:
    """Test the fallback regex-based extraction for flight search."""

    def test_extract_from_to(self):
        origin, code_o, dest, code_d, _, _ = _regex_search_extraction(
            "Find flights from Delhi to Mumbai"
        )
        assert origin == "Delhi"
        assert code_o == "DEL"
        assert dest == "Mumbai"
        assert code_d == "BOM"

    def test_extract_date_phrase(self):
        _, _, _, _, date_phrase, _ = _regex_search_extraction(
            "Flights from Hyderabad to Chennai next week"
        )
        assert date_phrase == "next week"

    def test_extract_tomorrow(self):
        _, _, _, _, date_phrase, _ = _regex_search_extraction(
            "I want to fly from Delhi to Goa tomorrow"
        )
        assert date_phrase == "tomorrow"

    def test_extract_preference_cheapest(self):
        _, _, _, _, _, pref = _regex_search_extraction(
            "Find the cheapest flight from Delhi to Mumbai"
        )
        assert pref == "cheapest"

    def test_extract_preference_fastest(self):
        _, _, _, _, _, pref = _regex_search_extraction(
            "Find the fastest flight from Delhi to Mumbai"
        )
        assert pref == "fastest"

    def test_extract_preference_nonstop(self):
        _, _, _, _, _, pref = _regex_search_extraction(
            "Find a nonstop flight from Delhi to Mumbai"
        )
        assert pref == "nonstop"

