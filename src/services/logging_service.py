"""
Logging Service.

Maintains an audit trail of every workflow execution.
Logs to both SQLite database and a log file.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import LOG_FILE, LOG_LEVEL
from src.database.sqlite import insert_log


# ── Configure File Logger ─────────────────────────────────────
logger = logging.getLogger("agent_logger")
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

# File handler
file_handler = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
file_handler.setFormatter(file_formatter)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(levelname)-8s | %(message)s")
console_handler.setFormatter(console_formatter)

# Avoid duplicate handlers
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def log_workflow_execution(
    booking_id: str | None,
    user_query: str,
    detected_intent: str | None,
    services_called: list[str],
    execution_status: str,
    processing_time: float,
    response_summary: str = "",
    error_details: str = "",
):
    """
    Log a complete workflow execution to both database and file.

    Args:
        booking_id: The booking ID involved (if any)
        user_query: The original customer query
        detected_intent: The detected intent (e.g., "Flight Rescheduling")
        services_called: List of services invoked during the workflow
        execution_status: Final status ("Success", "Failed", "Error")
        processing_time: Total processing time in seconds
        response_summary: Brief summary of the final response
        error_details: Error information if the workflow failed
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Log to database
    log_data = {
        "timestamp": timestamp,
        "booking_id": booking_id or "",
        "user_query": user_query,
        "detected_intent": detected_intent or "",
        "services_called": json.dumps(services_called),
        "execution_status": execution_status,
        "processing_time": round(processing_time, 2),
        "response_summary": response_summary[:500],  # Truncate for DB
        "error_details": error_details,
    }

    try:
        insert_log(log_data)
    except Exception as e:
        logger.error(f"Failed to write log to database: {e}")

    # Log to file
    log_message = (
        f"Query: {user_query[:100]} | "
        f"Intent: {detected_intent} | "
        f"Booking: {booking_id} | "
        f"Services: {', '.join(services_called)} | "
        f"Status: {execution_status} | "
        f"Time: {processing_time:.2f}s"
    )

    if execution_status == "Success":
        logger.info(log_message)
    elif execution_status == "Failed":
        logger.warning(f"{log_message} | Error: {error_details}")
    else:
        logger.error(f"{log_message} | Error: {error_details}")


def log_step(step_name: str, detail: str = "", level: str = "info"):
    """Log an individual workflow step for debugging."""
    message = f"[STEP] {step_name}"
    if detail:
        message += f" | {detail}"

    getattr(logger, level.lower(), logger.info)(message)
