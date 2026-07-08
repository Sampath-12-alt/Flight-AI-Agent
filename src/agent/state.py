"""
Agent State Definition.

Defines the TypedDict that flows through the LangGraph workflow.
Each node reads from and writes to this shared state.

Supports dual workflows:
    - Flight Search (new natural language flight discovery)
    - Flight Rescheduling (existing booking modification)
"""

from typing import TypedDict, Optional


class AgentState(TypedDict, total=False):
    """
    Shared state object that flows through the LangGraph workflow.

    Each node in the graph reads relevant fields and writes its results
    back to the state, enabling the next node to access them.
    """

    # ── Input ─────────────────────────────────────────────────
    user_query: str               # Original customer request

    # ── NLU Preprocessing ─────────────────────────────────────
    original_query: str           # Original user input (before normalization)
    normalized_query: str         # Cleaned/corrected query
    nlu_corrections: list         # List of corrections applied
    nlu_method: str               # "local", "llm", "hybrid", or "none"

    # ── Intent Detection ──────────────────────────────────────
    intent: str                   # "Flight Search" or "Flight Rescheduling"
    intent_confidence: str        # Confidence level ("high", "medium", "low")

    # ══════════════════════════════════════════════════════════
    # FLIGHT SEARCH WORKFLOW FIELDS
    # ══════════════════════════════════════════════════════════

    # ── Search Entity Extraction ──────────────────────────────
    search_origin: str            # Origin city name (e.g., "Hyderabad")
    search_origin_code: str       # IATA code (e.g., "HYD")
    search_destination: str       # Destination city name (e.g., "Mumbai")
    search_destination_code: str  # IATA code (e.g., "BOM")
    flexible_date_phrase: str     # Raw date phrase (e.g., "next week")
    user_preferences: str         # Preference (e.g., "cheapest", "fastest")

    # ── Date Interpretation ───────────────────────────────────
    search_dates: list            # Resolved dates (e.g., ["2026-07-06", ...])
    date_interpretation: str      # Human-readable (e.g., "Next week (7 days)")
    num_search_dates: int         # Number of dates to search

    # ══════════════════════════════════════════════════════════
    # RESCHEDULING WORKFLOW FIELDS
    # ══════════════════════════════════════════════════════════

    # ── Entity Extraction (Rescheduling) ──────────────────────
    booking_id: str               # Extracted booking ID
    new_date: str                 # Extracted requested travel date (YYYY-MM-DD)

    # ── Booking Retrieval ─────────────────────────────────────
    booking: dict                 # Booking details from database
    booking_found: bool           # Whether the booking was found

    # ── Policy Retrieval ──────────────────────────────────────
    airline: str                  # Identified airline
    policy_text: str              # Retrieved airline policy text
    policy_retrieved: bool        # Whether policy was successfully retrieved

    # ── Fee Calculation ───────────────────────────────────────
    fee_amount: float             # Calculated rescheduling fee
    fee_tier: str                 # Fee tier description
    fee_explanation: str          # Detailed fee explanation
    fee_eligible: bool            # Whether rescheduling is eligible

    # ── Fare Difference ───────────────────────────────────────
    fare_difference: float        # New fare - original fare
    total_cost: float             # rescheduling_fee + fare_difference
    cost_breakdown: dict          # Detailed cost breakdown

    # ── Booking Update ────────────────────────────────────────
    booking_updated: bool         # Whether the booking was updated
    previous_date: str            # Previous travel date (before update)

    # ══════════════════════════════════════════════════════════
    # SHARED FIELDS (used by both workflows)
    # ══════════════════════════════════════════════════════════

    # ── Live Flight Search ────────────────────────────────────
    available_flights: list       # List of flights from API/mock
    flights_found: bool           # Whether any flights were found
    num_flights_found: int        # Number of available flights
    flight_source: str            # "aviationstack_api" or "mock_data"

    # ── Flight Comparison ─────────────────────────────────────
    ranked_flights: list          # Flights ranked by score
    recommended_flight: dict      # Best recommended flight
    recommendation_reason: str    # Why this flight was recommended
    flight_tags: dict             # Tags like "Cheapest", "Fastest"

    # ── Response ──────────────────────────────────────────────
    response: str                 # Final customer-facing response
    response_generated: bool      # Whether a response was generated

    # ── Workflow Status ───────────────────────────────────────
    status: str                   # "Processing", "Completed", "Failed"
    error: str                    # Error message if something failed
    services_called: list         # List of services invoked
    processing_time: float        # Total processing time in seconds

    # ── Debug / Workflow Steps ────────────────────────────────
    steps_completed: list         # Ordered list of completed steps for UI
