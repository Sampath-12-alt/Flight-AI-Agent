"""
Response Generation Service.

Generates professional, customer-facing responses using the LLM.
Falls back to a template-based response if the LLM is unavailable.
Enhanced with flight recommendation details and cost breakdown.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import GOOGLE_API_KEY, LLM_MODEL


def generate_customer_response(context: dict) -> dict:
    """
    Generate a professional customer response based on the workflow context.

    Args:
        context: Dict containing workflow results including booking, fee,
                 recommended flight, and cost breakdown.

    Returns:
        dict with the generated response:
        {
            "success": bool,
            "response": str,
            "method": str  ("llm" or "template")
        }
    """
    # Try LLM-based generation first
    if GOOGLE_API_KEY:
        try:
            return _generate_with_llm(context)
        except Exception as e:
            print(f"⚠️  LLM response generation failed: {e}. Falling back to template.")

    # Fallback to template-based generation
    return _generate_with_template(context)


def _generate_with_llm(context: dict) -> dict:
    """Generate response using Google Gemini LLM."""
    import google.generativeai as genai

    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(LLM_MODEL)

    booking = context.get("booking", {})
    fee = context.get("fee", {})
    update = context.get("update_result", {})
    recommended = context.get("recommended_flight", {})
    cost = context.get("cost_breakdown", {})

    # Format flight times
    dep_time = ""
    arr_time = ""
    if recommended:
        dep_time = recommended.get("departure_time", "").split("T")[1][:5] if "T" in recommended.get("departure_time", "") else ""
        arr_time = recommended.get("arrival_time", "").split("T")[1][:5] if "T" in recommended.get("arrival_time", "") else ""

    prompt = f"""You are a professional customer support agent for a travel company.
Generate a clear, friendly, and professional response to confirm a flight rescheduling.

Details:
- Customer Name: {booking.get('customer_name', 'Customer')}
- Booking ID: {booking.get('booking_id', 'N/A')}
- Airline: {booking.get('airline', 'N/A')}
- Route: {booking.get('origin', '')} to {booking.get('destination', '')}
- Previous Travel Date: {update.get('previous_date', booking.get('travel_date', 'N/A'))}
- New Travel Date: {update.get('new_date', 'N/A')}
- Recommended Flight: {recommended.get('flight_number', 'N/A')} ({recommended.get('airline', '')})
- Departure: {dep_time}
- Arrival: {arr_time}
- Duration: {recommended.get('duration_display', 'N/A')}
- Stops: {"Direct" if recommended.get('stops', 0) == 0 else f"{recommended.get('stops')} stop(s)"}
- Original Fare: ₹{booking.get('ticket_price', 0):,.0f}
- New Flight Price: ₹{recommended.get('price', 0):,.0f}
- Rescheduling Fee: ₹{fee.get('fee_amount', 0):,.0f}
- Fare Difference: ₹{cost.get('fare_difference', 0):,.0f}
- Total Additional Cost: ₹{cost.get('total_additional_cost', 0):,.0f}

Requirements:
- Address the customer by name.
- Confirm the date change and mention the new flight details.
- Clearly state the cost breakdown (rescheduling fee + fare difference).
- Keep it concise (5-7 sentences).
- Be professional and courteous.
- End with a helpful closing.
- Do NOT use markdown formatting.
"""

    response = model.generate_content(prompt)
    return {
        "success": True,
        "response": response.text.strip(),
        "method": "llm",
    }


def _generate_with_template(context: dict) -> dict:
    """Generate response using a predefined template (fallback)."""
    booking = context.get("booking", {})
    fee = context.get("fee", {})
    update = context.get("update_result", {})
    recommended = context.get("recommended_flight", {})
    cost = context.get("cost_breakdown", {})

    customer_name = booking.get("customer_name", "Valued Customer")
    booking_id = booking.get("booking_id", "N/A")
    airline = booking.get("airline", "N/A")
    origin = booking.get("origin", "")
    destination = booking.get("destination", "")
    previous_date = update.get("previous_date", booking.get("travel_date", "N/A"))
    new_date = update.get("new_date", "N/A")
    fee_amount = fee.get("fee_amount", 0)

    # Flight details
    flight_number = recommended.get("flight_number", "N/A")
    flight_airline = recommended.get("airline", airline)
    dep_time = ""
    arr_time = ""
    if recommended:
        dep_time = recommended.get("departure_time", "").split("T")[1][:5] if "T" in recommended.get("departure_time", "") else ""
        arr_time = recommended.get("arrival_time", "").split("T")[1][:5] if "T" in recommended.get("arrival_time", "") else ""
    duration = recommended.get("duration_display", "N/A")
    stops = recommended.get("stops", 0)
    stops_str = "Direct" if stops == 0 else f"{stops} stop(s)"
    new_price = recommended.get("price", 0)

    # Cost breakdown
    fare_diff = cost.get("fare_difference", 0)
    total_additional = cost.get("total_additional_cost", 0)

    response_parts = [
        f"Dear {customer_name},",
        "",
        f"Your flight rescheduling request has been successfully processed.",
        "",
        f"Booking ID: {booking_id}",
        f"Route: {origin} → {destination}",
        f"Previous Date: {previous_date}",
        f"New Date: {new_date}",
        "",
    ]

    if recommended:
        response_parts.extend([
            "── New Flight Details ──",
            f"Flight: {flight_number} ({flight_airline})",
            f"Departure: {dep_time} | Arrival: {arr_time}",
            f"Duration: {duration} | {stops_str}",
            f"New Fare: ₹{new_price:,.0f}",
            "",
        ])

    response_parts.extend([
        "── Cost Breakdown ──",
        f"Rescheduling Fee: ₹{fee_amount:,.0f}",
    ])

    if fare_diff > 0:
        response_parts.append(f"Fare Difference: +₹{fare_diff:,.0f}")
    elif fare_diff < 0:
        response_parts.append(f"Fare Savings: -₹{abs(fare_diff):,.0f}")

    response_parts.extend([
        f"Total Additional Cost: ₹{total_additional:,.0f}",
        "",
        "Your updated itinerary has been generated successfully. "
        "If you have any further questions, please don't hesitate to reach out.",
        "",
        "Thank you for choosing our services.",
        "Best regards,",
        "Travel Support Team",
    ])

    return {
        "success": True,
        "response": "\n".join(response_parts),
        "method": "template",
    }


def generate_error_response(error_message: str, booking_id: str = "") -> str:
    """Generate a professional error response."""
    if booking_id:
        return (
            f"We were unable to process the rescheduling request for booking {booking_id}.\n\n"
            f"Reason: {error_message}\n\n"
            f"Please verify your booking details and try again, or contact our support team "
            f"for further assistance."
        )
    return (
        f"We were unable to process your request.\n\n"
        f"Reason: {error_message}\n\n"
        f"Please provide a valid booking ID and try again."
    )
