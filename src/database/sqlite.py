"""
SQLite Database Module for the AI Flight Rescheduling Agent.

Manages the bookings table and execution_logs table.
Provides initialization, seeding, and query utilities.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    """Create and return a database connection with row factory."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Initialize the database schema.
    Creates bookings and execution_logs tables if they don't exist.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Drop old bookings table if it exists (to update schema with IATA codes)
    cursor.execute("DROP TABLE IF EXISTS bookings")

    # ── Bookings Table ────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id       TEXT PRIMARY KEY,
            customer_name    TEXT NOT NULL,
            airline          TEXT NOT NULL,
            origin           TEXT NOT NULL,
            origin_code      TEXT NOT NULL,
            destination      TEXT NOT NULL,
            destination_code TEXT NOT NULL,
            travel_date      TEXT NOT NULL,
            status           TEXT NOT NULL DEFAULT 'Confirmed',
            ticket_price     REAL NOT NULL,
            last_updated     TEXT NOT NULL
        )
    """)

    # ── Execution Logs Table ──────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS execution_logs (
            log_id           INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp        TEXT NOT NULL,
            booking_id       TEXT,
            user_query       TEXT NOT NULL,
            detected_intent  TEXT,
            services_called  TEXT,
            execution_status TEXT NOT NULL,
            processing_time  REAL,
            response_summary TEXT,
            error_details    TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully.")


def seed_sample_data():
    """
    Insert sample booking records for demonstration.
    Skips insertion if data already exists.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM bookings")
    count = cursor.fetchone()[0]
    if count > 0:
        print(f"ℹ️  Database already contains {count} bookings. Skipping seed.")
        conn.close()
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sample_bookings = [
        {
            "booking_id": "BK1024",
            "customer_name": "Rahul Sharma",
            "airline": "Air India",
            "origin": "Delhi",
            "origin_code": "DEL",
            "destination": "Mumbai",
            "destination_code": "BOM",
            "travel_date": "2026-07-20",
            "status": "Confirmed",
            "ticket_price": 8500.00,
            "last_updated": now,
        },
        {
            "booking_id": "BK1025",
            "customer_name": "Priya Patel",
            "airline": "IndiGo",
            "origin": "Bangalore",
            "origin_code": "BLR",
            "destination": "Delhi",
            "destination_code": "DEL",
            "travel_date": "2026-07-22",
            "status": "Confirmed",
            "ticket_price": 6200.00,
            "last_updated": now,
        },
        {
            "booking_id": "BK1026",
            "customer_name": "Amit Kumar",
            "airline": "SpiceJet",
            "origin": "Mumbai",
            "origin_code": "BOM",
            "destination": "Goa",
            "destination_code": "GOI",
            "travel_date": "2026-08-01",
            "status": "Confirmed",
            "ticket_price": 4500.00,
            "last_updated": now,
        },
        {
            "booking_id": "BK1027",
            "customer_name": "Sneha Reddy",
            "airline": "Vistara",
            "origin": "Hyderabad",
            "origin_code": "HYD",
            "destination": "Chennai",
            "destination_code": "MAA",
            "travel_date": "2026-07-25",
            "status": "Confirmed",
            "ticket_price": 7800.00,
            "last_updated": now,
        },
        {
            "booking_id": "BK1028",
            "customer_name": "Karan Singh",
            "airline": "Air India",
            "origin": "Kolkata",
            "origin_code": "CCU",
            "destination": "Delhi",
            "destination_code": "DEL",
            "travel_date": "2026-08-10",
            "status": "Confirmed",
            "ticket_price": 9200.00,
            "last_updated": now,
        },
        {
            "booking_id": "BK1029",
            "customer_name": "Ananya Gupta",
            "airline": "IndiGo",
            "origin": "Chennai",
            "origin_code": "MAA",
            "destination": "Hyderabad",
            "destination_code": "HYD",
            "travel_date": "2026-07-18",
            "status": "Confirmed",
            "ticket_price": 5100.00,
            "last_updated": now,
        },
        {
            "booking_id": "BK1030",
            "customer_name": "Vikram Mehta",
            "airline": "SpiceJet",
            "origin": "Delhi",
            "origin_code": "DEL",
            "destination": "Jaipur",
            "destination_code": "JAI",
            "travel_date": "2026-08-05",
            "status": "Confirmed",
            "ticket_price": 3800.00,
            "last_updated": now,
        },
        {
            "booking_id": "BK1031",
            "customer_name": "Meera Nair",
            "airline": "Vistara",
            "origin": "Mumbai",
            "origin_code": "BOM",
            "destination": "Bangalore",
            "destination_code": "BLR",
            "travel_date": "2026-07-30",
            "status": "Confirmed",
            "ticket_price": 8100.00,
            "last_updated": now,
        },
        {
            "booking_id": "BK1032",
            "customer_name": "Arjun Desai",
            "airline": "Air India",
            "origin": "Pune",
            "origin_code": "PNQ",
            "destination": "Kolkata",
            "destination_code": "CCU",
            "travel_date": "2026-08-15",
            "status": "Confirmed",
            "ticket_price": 10500.00,
            "last_updated": now,
        },
        {
            "booking_id": "BK1033",
            "customer_name": "Divya Iyer",
            "airline": "IndiGo",
            "origin": "Goa",
            "origin_code": "GOI",
            "destination": "Mumbai",
            "destination_code": "BOM",
            "travel_date": "2026-07-28",
            "status": "Cancelled",
            "ticket_price": 4800.00,
            "last_updated": now,
        },
    ]

    for booking in sample_bookings:
        cursor.execute(
            """
            INSERT INTO bookings
                (booking_id, customer_name, airline, origin, origin_code,
                 destination, destination_code, travel_date, status,
                 ticket_price, last_updated)
            VALUES
                (:booking_id, :customer_name, :airline, :origin, :origin_code,
                 :destination, :destination_code, :travel_date, :status,
                 :ticket_price, :last_updated)
            """,
            booking,
        )

    conn.commit()
    conn.close()
    print(f"✅ Seeded {len(sample_bookings)} sample bookings.")


def get_booking(booking_id: str) -> dict | None:
    """Retrieve a booking by its ID. Returns None if not found."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None
    return dict(row)


def update_booking_date(booking_id: str, new_date: str) -> dict | None:
    """
    Update the travel date for a booking.
    Returns the updated booking or None if not found.
    """
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """
        UPDATE bookings
        SET travel_date = ?, last_updated = ?
        WHERE booking_id = ?
        """,
        (new_date, now, booking_id),
    )

    if cursor.rowcount == 0:
        conn.close()
        return None

    conn.commit()
    conn.close()
    return get_booking(booking_id)


def insert_log(log_data: dict):
    """Insert an execution log entry."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO execution_logs
            (timestamp, booking_id, user_query, detected_intent,
             services_called, execution_status, processing_time,
             response_summary, error_details)
        VALUES
            (:timestamp, :booking_id, :user_query, :detected_intent,
             :services_called, :execution_status, :processing_time,
             :response_summary, :error_details)
        """,
        log_data,
    )

    conn.commit()
    conn.close()


def get_all_logs() -> list[dict]:
    """Retrieve all execution logs, most recent first."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM execution_logs ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_bookings() -> list[dict]:
    """Retrieve all bookings."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookings ORDER BY booking_id")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ── Standalone execution for setup ────────────────────────────
if __name__ == "__main__":
    init_db()
    seed_sample_data()
    print("\n📋 Current Bookings:")
    for b in get_all_bookings():
        print(f"  {b['booking_id']} | {b['customer_name']:20s} | {b['airline']:10s} | "
              f"{b['origin']}({b['origin_code']}) → {b['destination']}({b['destination_code']}) | "
              f"{b['travel_date']} | ₹{b['ticket_price']:,.0f}")
