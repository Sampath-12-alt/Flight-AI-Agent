"""
LangGraph Agent — Dual-Intent Workflow Orchestrator (v3).

Supports two workflows via conditional routing:

FLIGHT SEARCH WORKFLOW:
    detect_intent → extract_search_entities → interpret_dates
    → search_multiple_flights → compare_flights
    → generate_search_response → log_execution → END

FLIGHT RESCHEDULING WORKFLOW:
    detect_intent → extract_entities → retrieve_booking
    → search_flights → compare_flights → retrieve_policy
    → calculate_fee → update_booking → generate_response
    → log_execution → END
"""

import json
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from langgraph.graph import StateGraph, END
from config import GOOGLE_API_KEY, LLM_MODEL

# ── Agent Components ──────────────────────────────────────────
from src.agent.state import AgentState
from src.agent.prompts import (
    INTENT_DETECTION_PROMPT,
    ENTITY_EXTRACTION_PROMPT,
    SEARCH_ENTITY_EXTRACTION_PROMPT,
    SEARCH_RESPONSE_PROMPT,
    UNSUPPORTED_INTENT_RESPONSE,
    MISSING_BOOKING_ID_RESPONSE,
    MISSING_NEW_DATE_RESPONSE,
    MISSING_SEARCH_INFO_RESPONSE,
)

# ── Business Services ────────────────────────────────────────
from src.services.booking_service import lookup_booking
from src.services.policy_service import get_airline_policy
from src.services.fee_service import calculate_rescheduling_fee, calculate_total_cost
from src.services.booking_update_service import update_booking
from src.services.response_service import generate_customer_response, generate_error_response
from src.services.logging_service import log_workflow_execution, log_step
from src.services.flight_search_service import search_flights, search_multiple_dates
from src.services.comparison_service import compare_flights, calculate_fare_difference
from src.services.date_parser_service import parse_flexible_dates


# ═══════════════════════════════════════════════════════════════
# SHARED NODE: INTENT DETECTION
# ═══════════════════════════════════════════════════════════════

def detect_intent(state: AgentState) -> dict:
    """
    Node 1: Analyze the customer request and detect intent.
    Routes to either Flight Search or Flight Rescheduling.
    """
    log_step("Intent Detection", "Analyzing customer request...")
    user_query = state["user_query"]

    try:
        if GOOGLE_API_KEY:
            import google.generativeai as genai
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel(LLM_MODEL)

            prompt = INTENT_DETECTION_PROMPT.format(user_query=user_query)
            response = model.generate_content(prompt)
            result_text = response.text.strip()

            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            result = json.loads(result_text)
            intent = result.get("intent", "Unsupported")
            confidence = result.get("confidence", "medium")
        else:
            intent = _keyword_intent_detection(user_query)
            confidence = "medium"

    except Exception as e:
        log_step("Intent Detection", f"LLM failed: {e}. Using keyword fallback.", "warning")
        intent = _keyword_intent_detection(user_query)
        confidence = "low"

    log_step("Intent Detection", f"Intent: {intent} (confidence: {confidence})")

    return {
        "intent": intent,
        "intent_confidence": confidence,
        "steps_completed": state.get("steps_completed", []) + ["✅ Intent: " + intent],
        "services_called": state.get("services_called", []) + ["IntentDetection"],
    }


# ═══════════════════════════════════════════════════════════════
# FLIGHT SEARCH WORKFLOW NODES
# ═══════════════════════════════════════════════════════════════

def extract_search_entities(state: AgentState) -> dict:
    """
    Search Node 1: Extract origin, destination, date phrase, and preferences.
    """
    log_step("Search Extraction", "Extracting travel search details...")
    user_query = state["user_query"]

    try:
        if GOOGLE_API_KEY:
            import google.generativeai as genai
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel(LLM_MODEL)

            prompt = SEARCH_ENTITY_EXTRACTION_PROMPT.format(user_query=user_query)
            response = model.generate_content(prompt)
            result_text = response.text.strip()

            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            result = json.loads(result_text)
            origin = result.get("origin", "").strip()
            origin_code = result.get("origin_code", "").strip().upper()
            destination = result.get("destination", "").strip()
            dest_code = result.get("destination_code", "").strip().upper()
            date_phrase = result.get("date_phrase", "").strip()
            preference = result.get("preference", "cheapest").strip().lower()
        else:
            origin, origin_code, destination, dest_code, date_phrase, preference = \
                _regex_search_extraction(user_query)

    except Exception as e:
        log_step("Search Extraction", f"LLM failed: {e}. Using regex.", "warning")
        origin, origin_code, destination, dest_code, date_phrase, preference = \
            _regex_search_extraction(user_query)

    log_step("Search Extraction",
             f"From: {origin}({origin_code}) To: {destination}({dest_code}) "
             f"When: '{date_phrase}' Pref: {preference}")

    return {
        "search_origin": origin,
        "search_origin_code": origin_code,
        "search_destination": destination,
        "search_destination_code": dest_code,
        "flexible_date_phrase": date_phrase,
        "user_preferences": preference,
        "steps_completed": state.get("steps_completed", []) + [
            f"✅ Search: {origin}({origin_code}) → {destination}({dest_code}) | "
            f"Date: '{date_phrase}' | Pref: {preference}"
        ],
        "services_called": state.get("services_called", []) + ["SearchEntityExtraction"],
    }


def interpret_dates_node(state: AgentState) -> dict:
    """
    Search Node 2: Convert flexible date phrase to concrete dates.
    """
    date_phrase = state.get("flexible_date_phrase", "")
    log_step("Date Interpretation", f"Interpreting: '{date_phrase}'")

    if not date_phrase:
        # Default to tomorrow
        from datetime import datetime, timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        return {
            "search_dates": [tomorrow],
            "date_interpretation": f"No date specified. Defaulting to tomorrow ({tomorrow}).",
            "num_search_dates": 1,
            "steps_completed": state.get("steps_completed", []) + [
                f"✅ Dates: Defaulting to tomorrow ({tomorrow})"
            ],
            "services_called": state.get("services_called", []) + ["DateParser"],
        }

    result = parse_flexible_dates(date_phrase)

    if not result["success"] or not result["dates"]:
        from datetime import datetime, timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        return {
            "search_dates": [tomorrow],
            "date_interpretation": f"Could not interpret '{date_phrase}'. Defaulting to tomorrow.",
            "num_search_dates": 1,
            "steps_completed": state.get("steps_completed", []) + [
                f"⚠️ Date interpretation failed. Using tomorrow ({tomorrow})"
            ],
            "services_called": state.get("services_called", []) + ["DateParser"],
        }

    # Limit to max 7 dates to avoid excessive API calls
    dates = result["dates"][:7]

    log_step("Date Interpretation",
             f"Resolved to {len(dates)} dates: {dates[0]} to {dates[-1]}")

    return {
        "search_dates": dates,
        "date_interpretation": result["interpretation"],
        "num_search_dates": len(dates),
        "steps_completed": state.get("steps_completed", []) + [
            f"✅ Dates: {result['interpretation']} → {len(dates)} days "
            f"({dates[0]} to {dates[-1]})"
        ],
        "services_called": state.get("services_called", []) + ["DateParser"],
    }


def search_multiple_flights_node(state: AgentState) -> dict:
    """
    Search Node 3: Search flights across all interpreted dates.
    """
    origin_code = state.get("search_origin_code", "")
    dest_code = state.get("search_destination_code", "")
    dates = state.get("search_dates", [])

    log_step("Multi-Date Search",
             f"Searching {len(dates)} dates: {origin_code} → {dest_code}")

    result = search_multiple_dates(origin_code, dest_code, dates, max_per_date=5)

    if not result["success"]:
        error_msg = result.get("error", "No flights found.")
        log_step("Multi-Date Search", f"Failed: {error_msg}", "warning")
        return {
            "flights_found": False,
            "available_flights": [],
            "num_flights_found": 0,
            "error": error_msg,
            "status": "Failed",
            "steps_completed": state.get("steps_completed", []) + [
                f"❌ Search: {error_msg}"
            ],
            "services_called": state.get("services_called", []) + ["FlightSearchService"],
        }

    log_step("Multi-Date Search",
             f"Found {result['num_results']} flights across {result['dates_with_results']} dates")

    return {
        "available_flights": result["flights"],
        "flights_found": True,
        "num_flights_found": result["num_results"],
        "flight_source": result["source"],
        "steps_completed": state.get("steps_completed", []) + [
            f"✅ Flights: {result['num_results']} found across "
            f"{result['dates_with_results']}/{result['dates_searched']} dates "
            f"({result['source'].replace('_', ' ').title()})"
        ],
        "services_called": state.get("services_called", []) + ["FlightSearchService"],
    }


def compare_flights_search_node(state: AgentState) -> dict:
    """
    Search Node 4: Compare and rank all flights found across dates.
    """
    flights = state.get("available_flights", [])
    preference = state.get("user_preferences", "cheapest")

    log_step("Flight Comparison", f"Comparing {len(flights)} flights (pref: {preference})")

    # Adjust weights based on user preference
    weights = None
    if preference == "fastest":
        weights = {"price": 0.20, "duration": 0.45, "stops": 0.20, "departure_time": 0.15}
    elif preference in ["nonstop", "direct"]:
        weights = {"price": 0.25, "duration": 0.20, "stops": 0.40, "departure_time": 0.15}
    elif preference == "earliest":
        weights = {"price": 0.20, "duration": 0.20, "stops": 0.15, "departure_time": 0.45}
    # Default (cheapest) uses the service's default weights

    result = compare_flights(flights, preferences=weights)

    if not result["success"]:
        return {
            "error": result["error"],
            "status": "Failed",
            "steps_completed": state.get("steps_completed", []) + [
                f"❌ Comparison: {result['error']}"
            ],
            "services_called": state.get("services_called", []) + ["ComparisonService"],
        }

    recommended = result["recommended"]
    dep_time = recommended["departure_time"].split("T")[1][:5] if "T" in recommended["departure_time"] else ""
    stops_str = "Direct" if recommended["stops"] == 0 else f"{recommended['stops']} stop(s)"
    flight_date = recommended.get("search_date", "")

    log_step("Flight Comparison",
             f"Recommended: {recommended['flight_number']} on {flight_date} @ ₹{recommended['price']:,.0f}")

    return {
        "ranked_flights": result["ranked_flights"],
        "recommended_flight": recommended,
        "recommendation_reason": result["recommendation_reason"],
        "flight_tags": result["tags"],
        "steps_completed": state.get("steps_completed", []) + [
            f"✅ Best: {recommended['flight_number']} ({recommended['airline']}) | "
            f"{flight_date} {dep_time} | {recommended['duration_display']} | "
            f"{stops_str} | ₹{recommended['price']:,.0f} | Score: {recommended['score']}"
        ],
        "services_called": state.get("services_called", []) + ["ComparisonService"],
    }


def generate_search_response_node(state: AgentState) -> dict:
    """
    Search Node 5: Generate the final search response.
    """
    log_step("Response Generation", "Generating search response...")

    recommended = state.get("recommended_flight", {})
    origin = state.get("search_origin", "")
    destination = state.get("search_destination", "")
    dates = state.get("search_dates", [])
    preference = state.get("user_preferences", "cheapest")
    total_flights = state.get("num_flights_found", 0)

    dep_time = recommended.get("departure_time", "").split("T")[1][:5] if "T" in recommended.get("departure_time", "") else ""
    arr_time = recommended.get("arrival_time", "").split("T")[1][:5] if "T" in recommended.get("arrival_time", "") else ""
    stops_str = "Direct" if recommended.get("stops", 0) == 0 else f"{recommended.get('stops')} stop(s)"
    flight_date = recommended.get("search_date", "")

    response_text = ""
    try:
        if GOOGLE_API_KEY:
            import google.generativeai as genai
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel(LLM_MODEL)

            prompt = SEARCH_RESPONSE_PROMPT.format(
                origin=f"{origin} ({state.get('search_origin_code', '')})",
                destination=f"{destination} ({state.get('search_destination_code', '')})",
                dates_searched=f"{len(dates)} dates ({dates[0]} to {dates[-1]})" if len(dates) > 1 else dates[0],
                total_flights=total_flights,
                preference=preference,
                flight_number=recommended.get("flight_number", "N/A"),
                airline=recommended.get("airline", "N/A"),
                flight_date=flight_date,
                departure_time=dep_time,
                arrival_time=arr_time,
                duration=recommended.get("duration_display", "N/A"),
                stops=stops_str,
                price=recommended.get("price", 0),
                reason=state.get("recommendation_reason", ""),
                num_alternatives=total_flights - 1,
            )

            result = model.generate_content(prompt)
            response_text = result.text.strip()
    except Exception as e:
        log_step("Response Generation", f"LLM failed: {e}. Using template.", "warning")

    if not response_text:
        # Template fallback
        dates_desc = f"{len(dates)} dates ({dates[0]} to {dates[-1]})" if len(dates) > 1 else dates[0]
        response_text = (
            f"Here are your flight search results!\n\n"
            f"Route: {origin} → {destination}\n"
            f"Dates Searched: {dates_desc}\n"
            f"Total Flights Found: {total_flights}\n\n"
            f"── Recommended Flight ──\n"
            f"Flight: {recommended.get('flight_number', 'N/A')} ({recommended.get('airline', 'N/A')})\n"
            f"Date: {flight_date}\n"
            f"Departure: {dep_time} | Arrival: {arr_time}\n"
            f"Duration: {recommended.get('duration_display', 'N/A')} | {stops_str}\n"
            f"Price: ₹{recommended.get('price', 0):,.0f}\n\n"
            f"Why Recommended: {state.get('recommendation_reason', 'Best overall score.')}\n\n"
            f"There are {total_flights - 1} other options available. "
            f"Let me know if you'd like to see all alternatives!"
        )

    log_step("Response Generation", "Search response generated.")

    return {
        "response": response_text,
        "response_generated": True,
        "status": "Completed",
        "steps_completed": state.get("steps_completed", []) + ["✅ Search Response Generated"],
        "services_called": state.get("services_called", []) + ["ResponseService"],
    }


# ═══════════════════════════════════════════════════════════════
# FLIGHT RESCHEDULING WORKFLOW NODES
# ═══════════════════════════════════════════════════════════════

def extract_entities(state: AgentState) -> dict:
    """Reschedule Node 1: Extract booking ID and new travel date."""
    log_step("Entity Extraction", "Extracting booking ID and travel date...")
    user_query = state["user_query"]

    try:
        if GOOGLE_API_KEY:
            import google.generativeai as genai
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel(LLM_MODEL)

            prompt = ENTITY_EXTRACTION_PROMPT.format(user_query=user_query)
            response = model.generate_content(prompt)
            result_text = response.text.strip()

            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            result = json.loads(result_text)
            booking_id = result.get("booking_id", "").strip().upper()
            new_date = result.get("new_date", "").strip()
        else:
            booking_id, new_date = _regex_entity_extraction(user_query)

    except Exception as e:
        log_step("Entity Extraction", f"LLM failed: {e}. Using regex.", "warning")
        booking_id, new_date = _regex_entity_extraction(user_query)

    log_step("Entity Extraction", f"Booking ID: {booking_id}, New Date: {new_date}")

    return {
        "booking_id": booking_id,
        "new_date": new_date,
        "steps_completed": state.get("steps_completed", []) + [
            f"✅ Extracted: Booking ID = {booking_id or 'Not found'}, Date = {new_date or 'Not found'}"
        ],
        "services_called": state.get("services_called", []) + ["EntityExtraction"],
    }


def retrieve_booking_node(state: AgentState) -> dict:
    """Reschedule Node 2: Retrieve booking details from the database."""
    booking_id = state.get("booking_id", "")
    log_step("Booking Retrieval", f"Looking up booking: {booking_id}")

    result = lookup_booking(booking_id)

    if not result["success"]:
        return {
            "booking_found": False,
            "error": result["error"],
            "status": "Failed",
            "steps_completed": state.get("steps_completed", []) + [f"❌ Booking: {result['error']}"],
            "services_called": state.get("services_called", []) + ["BookingService"],
        }

    booking = result["booking"]
    log_step("Booking Retrieval", f"Found: {booking['customer_name']} | {booking['airline']}")

    return {
        "booking": booking,
        "booking_found": True,
        "airline": booking["airline"],
        "steps_completed": state.get("steps_completed", []) + [
            f"✅ Booking: {booking['customer_name']} | {booking['airline']} | "
            f"{booking['origin']}({booking.get('origin_code','')}) → "
            f"{booking['destination']}({booking.get('destination_code','')}) | {booking['travel_date']}"
        ],
        "services_called": state.get("services_called", []) + ["BookingService"],
    }


def search_flights_node(state: AgentState) -> dict:
    """Reschedule Node 3: Search for flights on the new date."""
    booking = state.get("booking", {})
    new_date = state.get("new_date", "")
    origin_code = booking.get("origin_code", "")
    destination_code = booking.get("destination_code", "")

    log_step("Flight Search", f"Searching: {origin_code} → {destination_code} on {new_date}")

    result = search_flights(origin_code, destination_code, new_date, max_results=5)

    if not result["success"] or result["num_results"] == 0:
        error_msg = result.get("error", "No flights found.")
        return {
            "flights_found": False, "available_flights": [],
            "num_flights_found": 0, "error": error_msg, "status": "Failed",
            "steps_completed": state.get("steps_completed", []) + [f"❌ Flights: {error_msg}"],
            "services_called": state.get("services_called", []) + ["FlightSearchService"],
        }

    log_step("Flight Search", f"Found {result['num_results']} flights ({result['source']})")

    return {
        "available_flights": result["flights"],
        "flights_found": True,
        "num_flights_found": result["num_results"],
        "flight_source": result["source"],
        "steps_completed": state.get("steps_completed", []) + [
            f"✅ Flights: {result['num_results']} found ({result['source'].replace('_',' ').title()})"
        ],
        "services_called": state.get("services_called", []) + ["FlightSearchService"],
    }


def compare_flights_node(state: AgentState) -> dict:
    """Reschedule Node 4: Compare flights and recommend."""
    flights = state.get("available_flights", [])
    booking = state.get("booking", {})

    log_step("Flight Comparison", f"Comparing {len(flights)} flights...")

    result = compare_flights(flights)

    if not result["success"]:
        return {
            "error": result["error"], "status": "Failed",
            "steps_completed": state.get("steps_completed", []) + [f"❌ Compare: {result['error']}"],
            "services_called": state.get("services_called", []) + ["ComparisonService"],
        }

    recommended = result["recommended"]
    original_price = booking.get("ticket_price", 0)
    fare_diff = calculate_fare_difference(original_price, recommended["price"])

    dep_time = recommended["departure_time"].split("T")[1][:5] if "T" in recommended["departure_time"] else ""
    stops_str = "Direct" if recommended["stops"] == 0 else f"{recommended['stops']} stop(s)"

    log_step("Flight Comparison", f"Recommended: {recommended['flight_number']} @ ₹{recommended['price']:,.0f}")

    return {
        "ranked_flights": result["ranked_flights"],
        "recommended_flight": recommended,
        "recommendation_reason": result["recommendation_reason"],
        "flight_tags": result["tags"],
        "fare_difference": fare_diff["fare_difference"],
        "steps_completed": state.get("steps_completed", []) + [
            f"✅ Best: {recommended['flight_number']} ({recommended['airline']}) | "
            f"{dep_time} | {recommended['duration_display']} | {stops_str} | ₹{recommended['price']:,.0f}"
        ],
        "services_called": state.get("services_called", []) + ["ComparisonService"],
    }


def retrieve_policy_node(state: AgentState) -> dict:
    """Reschedule Node 5: Retrieve airline rescheduling policy via RAG."""
    airline = state.get("airline", "")
    log_step("Policy Retrieval", f"Searching policies for: {airline}")

    result = get_airline_policy(airline)

    if not result["success"]:
        return {
            "policy_retrieved": False, "error": result["error"], "status": "Failed",
            "steps_completed": state.get("steps_completed", []) + [f"❌ Policy: {result['error']}"],
            "services_called": state.get("services_called", []) + ["PolicyService"],
        }

    return {
        "policy_text": result["policy_text"],
        "policy_retrieved": True,
        "steps_completed": state.get("steps_completed", []) + [
            f"✅ Policy: {result['num_chunks']} sections for {airline}"
        ],
        "services_called": state.get("services_called", []) + ["PolicyService"],
    }


def calculate_fee_node(state: AgentState) -> dict:
    """Reschedule Node 6: Calculate rescheduling fee + fare difference."""
    booking = state.get("booking", {})
    new_date = state.get("new_date", "")
    recommended = state.get("recommended_flight", {})

    log_step("Fee Calculation", f"Calculating fee for {booking.get('airline', 'N/A')}")

    result = calculate_rescheduling_fee(booking, new_date)

    if not result["success"]:
        return {
            "fee_eligible": False, "error": result["error"], "status": "Failed",
            "steps_completed": state.get("steps_completed", []) + [f"❌ Fee: {result['error']}"],
            "services_called": state.get("services_called", []) + ["FeeService"],
        }

    new_price = recommended.get("price", booking.get("ticket_price", 0))
    cost = calculate_total_cost(result["fee_amount"], booking.get("ticket_price", 0), new_price)

    return {
        "fee_amount": result["fee_amount"],
        "fee_tier": result["fee_tier"],
        "fee_explanation": result["explanation"],
        "fee_eligible": True,
        "total_cost": cost["total_additional_cost"],
        "cost_breakdown": cost,
        "steps_completed": state.get("steps_completed", []) + [
            f"✅ Fee: ₹{result['fee_amount']:,.0f} ({result['fee_tier']}) | "
            f"Fare Diff: ₹{cost['fare_difference']:+,.0f} | Total: ₹{cost['total_additional_cost']:,.0f}"
        ],
        "services_called": state.get("services_called", []) + ["FeeService"],
    }


def update_booking_node(state: AgentState) -> dict:
    """Reschedule Node 7: Update the booking with the new date."""
    booking_id = state.get("booking_id", "")
    new_date = state.get("new_date", "")

    result = update_booking(booking_id, new_date)

    if not result["success"]:
        return {
            "booking_updated": False, "error": result["error"], "status": "Failed",
            "steps_completed": state.get("steps_completed", []) + [f"❌ Update: {result['error']}"],
            "services_called": state.get("services_called", []) + ["BookingUpdateService"],
        }

    return {
        "booking_updated": True,
        "previous_date": result["previous_date"],
        "steps_completed": state.get("steps_completed", []) + [
            f"✅ Updated: {result['previous_date']} → {result['new_date']}"
        ],
        "services_called": state.get("services_called", []) + ["BookingUpdateService"],
    }


def generate_response_node(state: AgentState) -> dict:
    """Reschedule Node 8: Generate the rescheduling confirmation response."""
    log_step("Response Generation", "Generating rescheduling response...")

    recommended = state.get("recommended_flight", {})
    cost = state.get("cost_breakdown", {})

    context = {
        "booking": state.get("booking", {}),
        "fee": {"fee_amount": state.get("fee_amount", 0), "fee_tier": state.get("fee_tier", "")},
        "update_result": {"previous_date": state.get("previous_date", ""), "new_date": state.get("new_date", "")},
        "recommended_flight": recommended,
        "cost_breakdown": cost,
        "recommendation_reason": state.get("recommendation_reason", ""),
        "status": "Success",
    }

    result = generate_customer_response(context)

    return {
        "response": result["response"],
        "response_generated": True,
        "status": "Completed",
        "steps_completed": state.get("steps_completed", []) + ["✅ Response Generated"],
        "services_called": state.get("services_called", []) + ["ResponseService"],
    }


# ═══════════════════════════════════════════════════════════════
# SHARED NODES
# ═══════════════════════════════════════════════════════════════

def log_execution_node(state: AgentState) -> dict:
    """Log the entire workflow execution."""
    processing_time = time.time() - state.get("_start_time", time.time())

    log_workflow_execution(
        booking_id=state.get("booking_id"),
        user_query=state.get("user_query", ""),
        detected_intent=state.get("intent"),
        services_called=state.get("services_called", []),
        execution_status=state.get("status", "Unknown"),
        processing_time=processing_time,
        response_summary=state.get("response", "")[:200],
        error_details=state.get("error", ""),
    )

    return {
        "processing_time": round(processing_time, 2),
        "steps_completed": state.get("steps_completed", []) + ["✅ Execution Logged"],
        "services_called": state.get("services_called", []) + ["LoggingService"],
    }


def handle_error_node(state: AgentState) -> dict:
    """Generate an error response and log the failure."""
    error = state.get("error", "An unexpected error occurred.")
    booking_id = state.get("booking_id", "")
    processing_time = time.time() - state.get("_start_time", time.time())

    response = generate_error_response(error, booking_id)

    log_workflow_execution(
        booking_id=booking_id,
        user_query=state.get("user_query", ""),
        detected_intent=state.get("intent"),
        services_called=state.get("services_called", []),
        execution_status="Failed",
        processing_time=processing_time,
        response_summary=response[:200],
        error_details=error,
    )

    return {
        "response": response, "response_generated": True, "status": "Failed",
        "processing_time": round(processing_time, 2),
        "steps_completed": state.get("steps_completed", []) + ["⚠️ Error Response Generated"],
    }


def handle_unsupported_node(state: AgentState) -> dict:
    """Handle unsupported intents."""
    processing_time = time.time() - state.get("_start_time", time.time())

    log_workflow_execution(
        booking_id=None,
        user_query=state.get("user_query", ""),
        detected_intent=state.get("intent", "Unsupported"),
        services_called=state.get("services_called", []),
        execution_status="Unsupported",
        processing_time=processing_time,
        response_summary=UNSUPPORTED_INTENT_RESPONSE[:200],
    )

    return {
        "response": UNSUPPORTED_INTENT_RESPONSE, "response_generated": True,
        "status": "Unsupported", "processing_time": round(processing_time, 2),
        "steps_completed": state.get("steps_completed", []) + ["ℹ️ Unsupported — Responded"],
    }


def handle_missing_info_node(state: AgentState) -> dict:
    """Handle cases where rescheduling info is missing."""
    booking_id = state.get("booking_id", "")
    new_date = state.get("new_date", "")

    if not booking_id:
        response = MISSING_BOOKING_ID_RESPONSE
    elif not new_date:
        response = MISSING_NEW_DATE_RESPONSE
    else:
        response = "Please provide both your Booking ID and the new travel date."

    return {
        "response": response, "response_generated": True, "status": "Incomplete",
        "steps_completed": state.get("steps_completed", []) + ["ℹ️ Missing Info — Requested"],
    }


def handle_missing_search_info_node(state: AgentState) -> dict:
    """Handle cases where flight search info is missing."""
    return {
        "response": MISSING_SEARCH_INFO_RESPONSE,
        "response_generated": True,
        "status": "Incomplete",
        "steps_completed": state.get("steps_completed", []) + ["ℹ️ Missing Search Info — Requested"],
    }


# ═══════════════════════════════════════════════════════════════
# ROUTING FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def route_after_intent(state: AgentState) -> str:
    intent = state.get("intent", "")
    if intent == "Flight Search":
        return "extract_search_entities"
    elif intent == "Flight Rescheduling":
        return "extract_entities"
    return "handle_unsupported"


def route_after_search_extraction(state: AgentState) -> str:
    origin = state.get("search_origin_code", "")
    dest = state.get("search_destination_code", "")
    if origin and dest:
        return "interpret_dates"
    return "handle_missing_search_info"


def route_after_dates(state: AgentState) -> str:
    dates = state.get("search_dates", [])
    if dates:
        return "search_multiple_flights"
    return "handle_error"


def route_after_multi_search(state: AgentState) -> str:
    if state.get("flights_found"):
        return "compare_flights_search"
    return "handle_error"


def route_after_search_comparison(state: AgentState) -> str:
    if state.get("recommended_flight"):
        return "generate_search_response"
    return "handle_error"


# ── Rescheduling routing ─────────────────────────────────────
def route_after_extraction(state: AgentState) -> str:
    if not state.get("booking_id") or not state.get("new_date"):
        return "handle_missing_info"
    return "retrieve_booking"


def route_after_booking(state: AgentState) -> str:
    if state.get("booking_found"):
        return "search_flights"
    return "handle_error"


def route_after_flights(state: AgentState) -> str:
    if state.get("flights_found"):
        return "compare_flights"
    return "handle_error"


def route_after_comparison(state: AgentState) -> str:
    if state.get("recommended_flight"):
        return "retrieve_policy"
    return "handle_error"


def route_after_policy(state: AgentState) -> str:
    if state.get("policy_retrieved"):
        return "calculate_fee"
    return "handle_error"


def route_after_fee(state: AgentState) -> str:
    if state.get("fee_eligible"):
        return "update_booking"
    return "handle_error"


def route_after_update(state: AgentState) -> str:
    if state.get("booking_updated"):
        return "generate_response"
    return "handle_error"


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def _keyword_intent_detection(query: str) -> str:
    """Fallback keyword-based intent detection."""
    query_lower = query.lower()

    # Check rescheduling first (more specific)
    reschedule_keywords = [
        "reschedule", "change my flight", "modify booking", "move my flight",
        "change date", "postpone", "prepone", "new date", "modify",
    ]
    for kw in reschedule_keywords:
        if kw in query_lower:
            return "Flight Rescheduling"

    # Check for booking ID pattern (BK followed by digits)
    import re
    if re.search(r"bk\d{4}", query_lower):
        return "Flight Rescheduling"

    # Check flight search
    search_keywords = [
        "search", "find", "look for", "show me flights", "i want to travel",
        "i need a flight", "flights from", "cheapest flight", "any flights",
        "available flights", "fly from", "want to fly", "book a flight",
        "find me", "looking for flights",
    ]
    for kw in search_keywords:
        if kw in query_lower:
            return "Flight Search"

    # Check for city-to-city patterns
    if re.search(r"from\s+\w+\s+to\s+\w+", query_lower):
        return "Flight Search"

    return "Unsupported"


def _regex_entity_extraction(query: str) -> tuple[str, str]:
    """Fallback regex-based entity extraction for rescheduling."""
    import re

    booking_match = re.search(r"BK\d{4,}", query, re.IGNORECASE)
    booking_id = booking_match.group(0).upper() if booking_match else ""

    new_date = ""
    date_match = re.search(r"\d{4}-\d{2}-\d{2}", query)
    if date_match:
        new_date = date_match.group(0)
    else:
        months = {
            "january": "01", "february": "02", "march": "03", "april": "04",
            "may": "05", "june": "06", "july": "07", "august": "08",
            "september": "09", "october": "10", "november": "11", "december": "12",
        }
        for month_name, month_num in months.items():
            match = re.search(rf"{month_name}\s+(\d{{1,2}})", query, re.IGNORECASE)
            if match:
                day = int(match.group(1))
                new_date = f"2026-{month_num}-{day:02d}"
                break
            match = re.search(rf"(\d{{1,2}})\s+{month_name}", query, re.IGNORECASE)
            if match:
                day = int(match.group(1))
                new_date = f"2026-{month_num}-{day:02d}"
                break

    return booking_id, new_date


def _regex_search_extraction(query: str) -> tuple:
    """Fallback regex-based extraction for flight search."""
    import re

    city_codes = {
        "delhi": "DEL", "mumbai": "BOM", "bangalore": "BLR", "bengaluru": "BLR",
        "hyderabad": "HYD", "chennai": "MAA", "kolkata": "CCU", "goa": "GOI",
        "jaipur": "JAI", "pune": "PNQ", "ahmedabad": "AMD", "kochi": "COK",
        "lucknow": "LKO", "chandigarh": "IXC",
    }

    query_lower = query.lower()

    origin = ""
    origin_code = ""
    destination = ""
    dest_code = ""
    date_phrase = ""
    preference = "cheapest"

    # Extract "from X to Y"
    route_match = re.search(r"from\s+(\w+)\s+to\s+(\w+)", query_lower)
    if route_match:
        origin = route_match.group(1).title()
        destination = route_match.group(2).title()
        origin_code = city_codes.get(origin.lower(), "")
        dest_code = city_codes.get(destination.lower(), "")

    # Extract date phrase
    date_patterns = [
        r"(tomorrow|today|next\s+week|this\s+week|next\s+weekend|this\s+weekend|"
        r"next\s+month|day\s+after\s+tomorrow)",
        r"((?:any\s+day\s+)?in\s+(?:january|february|march|april|may|june|"
        r"july|august|september|october|november|december))",
    ]
    for pattern in date_patterns:
        m = re.search(pattern, query_lower)
        if m:
            date_phrase = m.group(1)
            break

    # Extract preference
    if "cheapest" in query_lower or "cheap" in query_lower:
        preference = "cheapest"
    elif "fastest" in query_lower or "fast" in query_lower or "quickest" in query_lower:
        preference = "fastest"
    elif "nonstop" in query_lower or "non-stop" in query_lower or "direct" in query_lower:
        preference = "nonstop"
    elif "earliest" in query_lower or "early" in query_lower:
        preference = "earliest"

    return origin, origin_code, destination, dest_code, date_phrase, preference


# ═══════════════════════════════════════════════════════════════
# BUILD THE LANGGRAPH WORKFLOW
# ═══════════════════════════════════════════════════════════════

def build_agent_graph() -> StateGraph:
    """
    Construct the dual-intent LangGraph StateGraph.

    SEARCH:      detect → extract_search → interpret_dates → multi_search → compare → response → log
    RESCHEDULE:  detect → extract → booking → search → compare → policy → fee → update → response → log
    """
    graph = StateGraph(AgentState)

    # ── Add Nodes ─────────────────────────────────────────────
    # Shared
    graph.add_node("detect_intent", detect_intent)
    graph.add_node("log_execution", log_execution_node)
    graph.add_node("handle_error", handle_error_node)
    graph.add_node("handle_unsupported", handle_unsupported_node)

    # Flight Search workflow
    graph.add_node("extract_search_entities", extract_search_entities)
    graph.add_node("interpret_dates", interpret_dates_node)
    graph.add_node("search_multiple_flights", search_multiple_flights_node)
    graph.add_node("compare_flights_search", compare_flights_search_node)
    graph.add_node("generate_search_response", generate_search_response_node)
    graph.add_node("handle_missing_search_info", handle_missing_search_info_node)

    # Rescheduling workflow
    graph.add_node("extract_entities", extract_entities)
    graph.add_node("retrieve_booking", retrieve_booking_node)
    graph.add_node("search_flights", search_flights_node)
    graph.add_node("compare_flights", compare_flights_node)
    graph.add_node("retrieve_policy", retrieve_policy_node)
    graph.add_node("calculate_fee", calculate_fee_node)
    graph.add_node("update_booking", update_booking_node)
    graph.add_node("generate_response", generate_response_node)
    graph.add_node("handle_missing_info", handle_missing_info_node)

    # ── Entry Point ───────────────────────────────────────────
    graph.set_entry_point("detect_intent")

    # ── Intent Router (3-way split) ───────────────────────────
    graph.add_conditional_edges("detect_intent", route_after_intent, {
        "extract_search_entities": "extract_search_entities",
        "extract_entities": "extract_entities",
        "handle_unsupported": "handle_unsupported",
    })

    # ── Search Workflow Edges ─────────────────────────────────
    graph.add_conditional_edges("extract_search_entities", route_after_search_extraction, {
        "interpret_dates": "interpret_dates",
        "handle_missing_search_info": "handle_missing_search_info",
    })
    graph.add_conditional_edges("interpret_dates", route_after_dates, {
        "search_multiple_flights": "search_multiple_flights",
        "handle_error": "handle_error",
    })
    graph.add_conditional_edges("search_multiple_flights", route_after_multi_search, {
        "compare_flights_search": "compare_flights_search",
        "handle_error": "handle_error",
    })
    graph.add_conditional_edges("compare_flights_search", route_after_search_comparison, {
        "generate_search_response": "generate_search_response",
        "handle_error": "handle_error",
    })
    graph.add_edge("generate_search_response", "log_execution")

    # ── Rescheduling Workflow Edges ────────────────────────────
    graph.add_conditional_edges("extract_entities", route_after_extraction, {
        "retrieve_booking": "retrieve_booking",
        "handle_missing_info": "handle_missing_info",
    })
    graph.add_conditional_edges("retrieve_booking", route_after_booking, {
        "search_flights": "search_flights",
        "handle_error": "handle_error",
    })
    graph.add_conditional_edges("search_flights", route_after_flights, {
        "compare_flights": "compare_flights",
        "handle_error": "handle_error",
    })
    graph.add_conditional_edges("compare_flights", route_after_comparison, {
        "retrieve_policy": "retrieve_policy",
        "handle_error": "handle_error",
    })
    graph.add_conditional_edges("retrieve_policy", route_after_policy, {
        "calculate_fee": "calculate_fee",
        "handle_error": "handle_error",
    })
    graph.add_conditional_edges("calculate_fee", route_after_fee, {
        "update_booking": "update_booking",
        "handle_error": "handle_error",
    })
    graph.add_conditional_edges("update_booking", route_after_update, {
        "generate_response": "generate_response",
        "handle_error": "handle_error",
    })
    graph.add_edge("generate_response", "log_execution")

    # ── Terminal Edges ────────────────────────────────────────
    graph.add_edge("log_execution", END)
    graph.add_edge("handle_error", END)
    graph.add_edge("handle_unsupported", END)
    graph.add_edge("handle_missing_info", END)
    graph.add_edge("handle_missing_search_info", END)

    return graph.compile()


# ── Public Interface ──────────────────────────────────────────
def run_agent(user_query: str) -> AgentState:
    """Run the flight agent with a customer query."""
    agent = build_agent_graph()

    initial_state: AgentState = {
        "user_query": user_query,
        "intent": "", "intent_confidence": "",
        # Search fields
        "search_origin": "", "search_origin_code": "",
        "search_destination": "", "search_destination_code": "",
        "flexible_date_phrase": "", "user_preferences": "",
        "search_dates": [], "date_interpretation": "", "num_search_dates": 0,
        # Rescheduling fields
        "booking_id": "", "new_date": "",
        "booking": {}, "booking_found": False,
        "airline": "",
        # Shared
        "available_flights": [], "flights_found": False,
        "num_flights_found": 0, "flight_source": "",
        "ranked_flights": [], "recommended_flight": {},
        "recommendation_reason": "", "flight_tags": {},
        # Policy + Fee (rescheduling)
        "policy_text": "", "policy_retrieved": False,
        "fee_amount": 0.0, "fee_tier": "", "fee_explanation": "",
        "fee_eligible": False, "fare_difference": 0.0,
        "total_cost": 0.0, "cost_breakdown": {},
        "booking_updated": False, "previous_date": "",
        # Response
        "response": "", "response_generated": False,
        "status": "Processing", "error": "",
        "services_called": [], "processing_time": 0.0,
        "steps_completed": [],
        "_start_time": time.time(),
    }

    return agent.invoke(initial_state)


# ── Standalone testing ────────────────────────────────────────
if __name__ == "__main__":
    from src.database.sqlite import init_db, seed_sample_data
    init_db()
    seed_sample_data()

    print("\n" + "=" * 60)
    print("🤖 AI Flight Agent v3 — Dual Intent Test")
    print("=" * 60)

    # Test 1: Flight Search
    search_query = "I want to fly from Delhi to Mumbai next week. Find me the cheapest flight."
    print(f"\n📩 SEARCH: {search_query}\n")
    result = run_agent(search_query)
    print(f"   Status: {result.get('status')}")
    print(f"   Intent: {result.get('intent')}")
    rec = result.get("recommended_flight", {})
    if rec:
        print(f"   Recommended: {rec.get('flight_number')} @ ₹{rec.get('price', 0):,.0f}")
    print(f"   Steps: {len(result.get('steps_completed', []))}")
    print(f"\n   Response:\n   {result.get('response', '')[:200]}...")

    print("\n" + "-" * 60)

    # Test 2: Rescheduling
    resched_query = "My booking ID is BK1024. Change my flight to July 23."
    print(f"\n📩 RESCHEDULE: {resched_query}\n")
    result = run_agent(resched_query)
    print(f"   Status: {result.get('status')}")
    print(f"   Intent: {result.get('intent')}")
    print(f"   Fee: ₹{result.get('fee_amount', 0):,.0f}")
    print(f"\n   Response:\n   {result.get('response', '')[:200]}...")
