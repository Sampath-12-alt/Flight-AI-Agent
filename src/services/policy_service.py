"""
Policy Service.

Wraps the RAG retriever to provide airline policy information
as a structured service for the agent.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.rag.retriever import retrieve_policy, list_available_airlines


def get_airline_policy(airline: str) -> dict:
    """
    Retrieve the rescheduling policy for a given airline.

    Args:
        airline: Airline name (e.g., "Air India", "IndiGo")

    Returns:
        dict with policy information:
        {
            "success": bool,
            "airline": str,
            "policy_text": str,
            "num_chunks": int,
            "error": str | None
        }
    """
    if not airline:
        return {
            "success": False,
            "airline": "",
            "policy_text": "",
            "num_chunks": 0,
            "error": "Airline name is required.",
        }

    # Normalize airline name
    airline = airline.strip()

    # Map common variations to canonical names
    airline_aliases = {
        "air india": "Air India",
        "airindia": "Air India",
        "indigo": "IndiGo",
        "6e": "IndiGo",
        "spicejet": "SpiceJet",
        "spice jet": "SpiceJet",
        "vistara": "Vistara",
        "uk": "Vistara",
    }

    canonical = airline_aliases.get(airline.lower(), airline)

    # Retrieve policy from RAG
    result = retrieve_policy(canonical)

    if not result["found"]:
        available = list_available_airlines()
        return {
            "success": False,
            "airline": canonical,
            "policy_text": "",
            "num_chunks": 0,
            "error": f"No policy found for '{canonical}'. Available airlines: {', '.join(available)}",
        }

    return {
        "success": True,
        "airline": canonical,
        "policy_text": result["policy_text"],
        "num_chunks": len(result["chunks"]),
        "error": None,
    }
