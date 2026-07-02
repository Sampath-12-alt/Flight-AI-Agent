"""
FastAPI Routes for the AI Flight Search & Rescheduling Agent.

Endpoints:
    POST /agent/process        — Process a customer request (search or reschedule)
    GET  /booking/{id}         — Get booking details
    GET  /bookings             — List all bookings
    GET  /flights              — Search flights (standalone)
    GET  /logs                 — Get execution history
    GET  /health               — Health check
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.agent.graph import run_agent
from src.services.booking_service import lookup_booking, list_bookings
from src.services.flight_search_service import search_flights
from src.database.sqlite import get_all_logs


router = APIRouter()


class AgentRequest(BaseModel):
    query: str = Field(
        ...,
        description="Customer's natural language request",
        min_length=5,
        examples=[
            "I want to fly from Delhi to Mumbai next week. Find me the cheapest flight.",
            "My booking ID is BK1024. Change my flight to July 23.",
        ],
    )


class AgentResponse(BaseModel):
    status: str
    intent: str
    booking_id: str
    fee: float
    total_cost: float
    fare_difference: float
    recommended_flight: dict
    available_flights: list
    # Search-specific fields
    search_origin: str
    search_destination: str
    search_dates: list
    date_interpretation: str
    num_flights_found: int
    user_preferences: str
    # Response
    message: str
    steps: list[str]
    processing_time: float


@router.post("/agent/process", response_model=AgentResponse)
async def process_request(request: AgentRequest):
    """
    Process a customer request. The agent auto-detects the intent:
    - Flight Search: natural language flight discovery
    - Flight Rescheduling: modify an existing booking
    """
    try:
        result = run_agent(request.query)

        return AgentResponse(
            status=result.get("status", "Unknown"),
            intent=result.get("intent", ""),
            booking_id=result.get("booking_id", ""),
            fee=result.get("fee_amount", 0),
            total_cost=result.get("total_cost", 0),
            fare_difference=result.get("fare_difference", 0),
            recommended_flight=result.get("recommended_flight", {}),
            available_flights=result.get("ranked_flights", []),
            search_origin=result.get("search_origin", ""),
            search_destination=result.get("search_destination", ""),
            search_dates=result.get("search_dates", []),
            date_interpretation=result.get("date_interpretation", ""),
            num_flights_found=result.get("num_flights_found", 0),
            user_preferences=result.get("user_preferences", ""),
            message=result.get("response", "No response generated."),
            steps=result.get("steps_completed", []),
            processing_time=result.get("processing_time", 0),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent processing failed: {str(e)}")


@router.get("/booking/{booking_id}")
async def get_booking(booking_id: str):
    result = lookup_booking(booking_id)
    return {"success": result["success"], "booking": result["booking"], "error": result["error"]}


@router.get("/bookings")
async def get_all_bookings():
    bookings = list_bookings()
    return {"count": len(bookings), "bookings": bookings}


@router.get("/flights")
async def search_available_flights(
    origin: str = Query(..., description="Origin IATA code"),
    destination: str = Query(..., description="Destination IATA code"),
    date: str = Query(..., description="Travel date (YYYY-MM-DD)"),
    max_results: int = Query(5, description="Max results"),
):
    return search_flights(origin.upper(), destination.upper(), date, max_results)


@router.get("/logs")
async def get_logs():
    logs = get_all_logs()
    return {"count": len(logs), "logs": logs}


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AI Flight Search & Rescheduling Agent", "version": "3.0"}
