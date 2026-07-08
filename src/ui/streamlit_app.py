"""
Streamlit UI — AI Flight Agent.

Professional SaaS dashboard for flight search and rescheduling.
Light theme with clean typography and consistent spacing.
"""

import time
import sys
import html as html_lib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import requests
import pandas as pd

from config import FASTAPI_URL

# ── Page Config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Flight Agent",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design Tokens ─────────────────────────────────────────────
C_BG = "#F8FAFC"
C_SURFACE = "#FFFFFF"
C_PRIMARY = "#2563EB"
C_PRIMARY_LIGHT = "#EFF6FF"
C_TEXT = "#0F172A"
C_TEXT_SEC = "#64748B"
C_BORDER = "#E2E8F0"
C_SUCCESS = "#22C55E"
C_SUCCESS_LIGHT = "#F0FDF4"
C_WARNING = "#F59E0B"
C_WARNING_LIGHT = "#FFFBEB"
C_ERROR = "#EF4444"
C_ERROR_LIGHT = "#FEF2F2"
RADIUS = "10px"
SHADOW = "0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)"

# ── Global Styles ─────────────────────────────────────────────
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Base */
    .stApp {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: {C_BG};
    }}
    #MainMenu, footer, header {{ visibility: hidden; }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background: {C_SURFACE};
        border-right: 1px solid {C_BORDER};
    }}
    section[data-testid="stSidebar"] .stRadio label {{
        font-size: 14px;
        color: {C_TEXT};
    }}

    /* Typography */
    h1, h2, h3, h4, h5, h6 {{
        font-family: 'Inter', sans-serif;
        color: {C_TEXT};
    }}
    p, li, span, div {{
        font-family: 'Inter', sans-serif;
    }}

    /* Native Streamlit overrides */
    .stTextArea textarea {{
        border: 1px solid {C_BORDER};
        border-radius: 8px;
        font-size: 14px;
        background: {C_SURFACE};
        color: {C_TEXT};
    }}
    .stTextArea textarea:focus {{
        border-color: {C_PRIMARY};
        box-shadow: 0 0 0 3px rgba(37,99,235,0.1);
    }}
    .stButton > button[kind="primary"] {{
        background: {C_PRIMARY};
        border: none;
        border-radius: 8px;
        font-weight: 600;
        font-size: 14px;
        padding: 8px 20px;
        transition: background 0.15s ease;
    }}
    .stButton > button[kind="primary"]:hover {{
        background: #1D4ED8;
    }}
    .stButton > button:not([kind="primary"]) {{
        background: {C_SURFACE};
        border: 1px solid {C_BORDER};
        border-radius: 8px;
        color: {C_TEXT};
        font-size: 13px;
        font-weight: 500;
        padding: 6px 14px;
        transition: all 0.15s ease;
    }}
    .stButton > button:not([kind="primary"]):hover {{
        background: {C_BG};
        border-color: #CBD5E1;
    }}
    div[data-testid="stDataFrame"] {{
        border: 1px solid {C_BORDER};
        border-radius: {RADIUS};
        overflow: hidden;
    }}
    .stExpander {{
        border: 1px solid {C_BORDER};
        border-radius: {RADIUS};
    }}

    /* Custom component classes */
    .page-title {{
        font-size: 22px;
        font-weight: 700;
        color: {C_TEXT};
        margin: 0 0 4px 0;
        line-height: 1.3;
    }}
    .page-subtitle {{
        font-size: 14px;
        color: {C_TEXT_SEC};
        margin: 0 0 24px 0;
        line-height: 1.5;
    }}
    .section-label {{
        font-size: 12px;
        font-weight: 600;
        color: {C_TEXT_SEC};
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin: 0 0 12px 0;
    }}
    .card {{
        background: {C_SURFACE};
        border: 1px solid {C_BORDER};
        border-radius: {RADIUS};
        padding: 20px 24px;
        box-shadow: {SHADOW};
    }}
    .kpi {{
        background: {C_SURFACE};
        border: 1px solid {C_BORDER};
        border-radius: {RADIUS};
        padding: 16px 20px;
        box-shadow: {SHADOW};
    }}
    .kpi-value {{
        font-size: 24px;
        font-weight: 700;
        color: {C_TEXT};
        margin: 0;
        line-height: 1.2;
    }}
    .kpi-label {{
        font-size: 11px;
        font-weight: 600;
        color: {C_TEXT_SEC};
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin: 4px 0 0 0;
    }}
    .flight-row {{
        background: {C_SURFACE};
        border: 1px solid {C_BORDER};
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 8px;
        transition: box-shadow 0.15s ease;
    }}
    .flight-row:hover {{
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }}
    .flight-row.recommended {{
        border-color: {C_SUCCESS};
        background: {C_SUCCESS_LIGHT};
    }}
    .flight-num {{
        font-size: 14px;
        font-weight: 600;
        color: {C_TEXT};
    }}
    .flight-airline {{
        font-size: 13px;
        color: {C_TEXT_SEC};
        margin-left: 8px;
    }}
    .flight-price {{
        font-size: 16px;
        font-weight: 700;
        color: {C_TEXT};
    }}
    .flight-meta {{
        font-size: 13px;
        color: {C_TEXT_SEC};
        margin-top: 6px;
    }}
    .tag {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        margin-right: 6px;
    }}
    .tag-rec {{ background: {C_SUCCESS_LIGHT}; color: #15803D; }}
    .tag-cheap {{ background: {C_WARNING_LIGHT}; color: #B45309; }}
    .tag-fast {{ background: {C_PRIMARY_LIGHT}; color: #1D4ED8; }}
    .tag-direct {{ background: #F0F9FF; color: #0369A1; }}
    .response-box {{
        background: {C_SURFACE};
        border: 1px solid {C_BORDER};
        border-radius: {RADIUS};
        padding: 20px 24px;
        box-shadow: {SHADOW};
        font-size: 14px;
        line-height: 1.75;
        color: {C_TEXT};
    }}
    .step-item {{
        padding: 8px 12px;
        margin-bottom: 4px;
        border-radius: 6px;
        font-size: 13px;
        color: {C_TEXT};
        background: {C_BG};
        border-left: 3px solid {C_BORDER};
    }}
    .step-ok {{ border-left-color: {C_SUCCESS}; }}
    .step-err {{ border-left-color: {C_ERROR}; }}
    .step-info {{ border-left-color: {C_PRIMARY}; }}
    .cost-line {{
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        font-size: 14px;
        color: {C_TEXT};
    }}
    .cost-total {{
        border-top: 1px solid {C_BORDER};
        margin-top: 4px;
        padding-top: 10px;
        font-weight: 700;
    }}
    .nav-label {{
        font-size: 11px;
        font-weight: 600;
        color: {C_TEXT_SEC};
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin: 0 0 8px 0;
    }}
    .sidebar-footer {{
        font-size: 11px;
        color: #94A3B8;
        text-align: center;
        padding: 16px 0;
    }}
</style>
""", unsafe_allow_html=True)


# ── Mode Detection ────────────────────────────────────────────
# Supports two modes:
#   1. DIRECT: Import agent directly (for Streamlit Cloud deployment)
#   2. API:    Call FastAPI backend (for local dev with separate backend)

def _check_api_available() -> bool:
    """Check if the FastAPI backend is reachable."""
    try:
        r = requests.get(f"{FASTAPI_URL}/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False

USE_API_MODE = _check_api_available()

if not USE_API_MODE:
    # Direct mode: import agent and database directly
    from src.agent.graph import run_agent
    from src.database.sqlite import init_db, seed_sample_data, get_all_bookings, get_all_logs

    # Initialize database on first run
    if "_db_initialized" not in st.session_state:
        init_db()
        seed_sample_data()
        st.session_state["_db_initialized"] = True


# ── Data Helpers ──────────────────────────────────────────────

def call_agent(query: str) -> dict | None:
    """Process a query — via API or directly."""
    if USE_API_MODE:
        try:
            r = requests.post(
                f"{FASTAPI_URL}/agent/process",
                json={"query": query},
                timeout=120,
            )
            return r.json() if r.status_code == 200 else None
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend. Run `python main.py` first.")
            return None
        except Exception as e:
            st.error(f"Request failed: {e}")
            return None
    else:
        # Direct mode: call agent in-process
        try:
            result = run_agent(query)
            # Map agent state to the API response format
            return {
                "status": result.get("status", "Unknown"),
                "intent": result.get("intent", ""),
                "booking_id": result.get("booking_id", ""),
                "fee": result.get("fee_amount", 0),
                "total_cost": result.get("total_cost", 0),
                "fare_difference": result.get("fare_difference", 0),
                "recommended_flight": result.get("recommended_flight", {}),
                "available_flights": result.get("ranked_flights", []),
                "search_origin": result.get("search_origin", ""),
                "search_destination": result.get("search_destination", ""),
                "search_dates": result.get("search_dates", []),
                "date_interpretation": result.get("date_interpretation", ""),
                "num_flights_found": result.get("num_flights_found", 0),
                "user_preferences": result.get("user_preferences", ""),
                "message": result.get("response", "No response generated."),
                "steps": result.get("steps_completed", []),
                "processing_time": result.get("processing_time", 0),
                # NLU fields
                "original_query": result.get("original_query", ""),
                "normalized_query": result.get("normalized_query", ""),
                "nlu_corrections": result.get("nlu_corrections", []),
                "nlu_method": result.get("nlu_method", ""),
            }
        except Exception as e:
            st.error(f"Agent error: {e}")
            return None


def fetch_bookings() -> list:
    if USE_API_MODE:
        try:
            r = requests.get(f"{FASTAPI_URL}/bookings", timeout=10)
            return r.json().get("bookings", []) if r.status_code == 200 else []
        except Exception:
            return []
    else:
        try:
            return get_all_bookings()
        except Exception:
            return []


def fetch_logs() -> list:
    if USE_API_MODE:
        try:
            r = requests.get(f"{FASTAPI_URL}/logs", timeout=10)
            return r.json().get("logs", []) if r.status_code == 200 else []
        except Exception:
            return []
    else:
        try:
            return get_all_logs()
        except Exception:
            return []



# ── Render Helpers ────────────────────────────────────────────

def render_kpi(value: str, label: str):
    """Render a compact KPI card."""
    st.markdown(
        f'<div class="kpi">'
        f'<p class="kpi-value">{value}</p>'
        f'<p class="kpi-label">{label}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_flight(flight: dict, is_rec: bool = False, show_date: bool = False):
    """Render a single flight row."""
    dep = flight.get("departure_time", "")
    dep = dep.split("T")[1][:5] if "T" in dep else dep
    arr = flight.get("arrival_time", "")
    arr = arr.split("T")[1][:5] if "T" in arr else arr
    stops = "Direct" if flight.get("stops", 0) == 0 else f"{flight['stops']} stop"
    price = flight.get("price", 0)
    date_str = flight.get("search_date", "") if show_date else ""

    # Tags
    tags_html = ""
    if is_rec:
        tags_html += '<span class="tag tag-rec">Recommended</span>'
    all_f = st.session_state.get("_flights", [])
    if all_f:
        if price <= min(f["price"] for f in all_f):
            tags_html += '<span class="tag tag-cheap">Lowest price</span>'
        if flight.get("duration_hours", 99) <= min(f.get("duration_hours", 99) for f in all_f):
            tags_html += '<span class="tag tag-fast">Fastest</span>'
        if flight.get("stops", 1) == 0 and not is_rec:
            tags_html += '<span class="tag tag-direct">Nonstop</span>'

    cls = "flight-row recommended" if is_rec else "flight-row"
    date_part = f'<span style="color:{C_TEXT_SEC};font-size:12px;margin-left:10px;">{date_str}</span>' if date_str else ""
    tags_div = f'<div style="margin-top:6px;">{tags_html}</div>' if tags_html else ""

    st.markdown(
        f'<div class="{cls}">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<div><span class="flight-num">{flight.get("flight_number","")}</span>'
        f'<span class="flight-airline">{flight.get("airline","")}</span>'
        f'{date_part}</div>'
        f'<span class="flight-price">₹{price:,.0f}</span>'
        f'</div>'
        f'<div class="flight-meta">{dep} → {arr}  ·  {flight.get("duration_display","")}  ·  {stops}</div>'
        f'{tags_div}'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_step(text: str):
    """Render a workflow step."""
    cls = "step-ok" if "✅" in text else "step-err" if "❌" in text else "step-info"
    clean = text.replace("✅ ", "").replace("❌ ", "").replace("ℹ️ ", "").replace("⚠️ ", "")
    st.markdown(f'<div class="step-item {cls}">{clean}</div>', unsafe_allow_html=True)


def format_response(text: str) -> str:
    """Sanitize and format agent response text for HTML display."""
    safe = html_lib.escape(text)
    safe = safe.replace("\n\n", "<br><br>").replace("\n", "<br>")
    safe = safe.replace("──", "—")
    return safe


# ── Sidebar ───────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        f'<div style="padding:8px 0 16px;">'
        f'<span style="font-size:18px;font-weight:700;color:{C_TEXT};">Flight Agent</span>'
        f'<span style="font-size:11px;color:{C_TEXT_SEC};margin-left:8px;">v3.0</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<p class="nav-label">Navigation</p>', unsafe_allow_html=True)
    page = st.radio(
        "nav",
        ["Agent", "Bookings", "Logs"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown('<p class="nav-label">Stack</p>', unsafe_allow_html=True)
    stack_items = ["LangGraph", "Gemini LLM", "Aviationstack API", "FastAPI", "ChromaDB", "SQLite"]
    for item in stack_items:
        st.markdown(
            f'<div style="font-size:13px;color:{C_TEXT_SEC};padding:2px 0;">{item}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown(
        f'<p class="sidebar-footer">Dual intent · Live search<br>Built with LangGraph</p>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════
# AGENT PAGE
# ══════════════════════════════════════════════════════════════

if page == "Agent":
    st.markdown('<p class="page-title">Flight Agent</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-subtitle">'
        'Search for flights or reschedule existing bookings using natural language.'
        '</p>',
        unsafe_allow_html=True,
    )

    # ── Input Area ────────────────────────────────────────────
    col_in, col_ex = st.columns([3, 2], gap="large")

    with col_in:
        st.markdown('<p class="section-label">Your request</p>', unsafe_allow_html=True)
        user_query = st.text_area(
            "query",
            height=96,
            placeholder="e.g. Find the cheapest flight from Delhi to Mumbai next week",
            label_visibility="collapsed",
        )
        process_btn = st.button("Process request", type="primary", use_container_width=True)

    with col_ex:
        st.markdown('<p class="section-label">Examples</p>', unsafe_allow_html=True)

        examples = [
            ("Search", "Find flights from Hyderabad to Mumbai next week. Cheapest option."),
            ("Search", "I want to travel from Delhi to Bangalore tomorrow."),
            ("Search", "Show me flights from Chennai to Delhi this weekend."),
            ("Reschedule", "My booking BK1024, change to July 25."),
            ("Reschedule", "Reschedule booking BK1025 to August 5th."),
        ]
        for i, (kind, text) in enumerate(examples):
            label = text[:55] + ("..." if len(text) > 55 else "")
            if st.button(label, key=f"ex_{i}", use_container_width=True):
                st.session_state["_sample"] = text
                st.rerun()

    if "_sample" in st.session_state:
        user_query = st.session_state.pop("_sample")

    # ── Process ───────────────────────────────────────────────
    if process_btn and user_query:
        with st.spinner("Processing..."):
            t0 = time.time()
            result = call_agent(user_query)
            elapsed = time.time() - t0

        if not result:
            st.stop()

        intent = result.get("intent", "Unknown")
        is_search = intent == "Flight Search"
        is_resched = intent == "Flight Rescheduling"
        status = result.get("status", "Unknown")

        st.markdown("---")

        # ── KPI Row ───────────────────────────────────────────
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            render_kpi(
                "Completed" if status == "Completed" else status,
                "Status",
            )
        with k2:
            render_kpi(
                "Search" if is_search else "Reschedule" if is_resched else intent[:12],
                "Intent",
            )
        with k3:
            render_kpi(str(result.get("num_flights_found", 0)), "Flights found")
        with k4:
            render_kpi(f"{result.get('processing_time', elapsed):.1f}s", "Processing time")

        st.markdown("")

        # ── Completed Results ─────────────────────────────────
        if status == "Completed":
            flights = result.get("available_flights", [])
            recommended = result.get("recommended_flight", {})
            st.session_state["_flights"] = flights

            col_left, col_right = st.columns([1, 1], gap="large")

            # ── Left: Flights ─────────────────────────────────
            with col_left:
                if flights:
                    count_label = f"{len(flights)} flights"
                    if is_search and result.get("search_dates"):
                        count_label += f" across {len(result['search_dates'])} days"
                    st.markdown(
                        f'<p class="section-label">Available flights · {count_label}</p>',
                        unsafe_allow_html=True,
                    )

                    for flight in flights[:8]:
                        is_rec = (
                            flight.get("flight_number") == recommended.get("flight_number", "")
                        )
                        render_flight(flight, is_rec=is_rec, show_date=is_search)

                    if len(flights) > 8:
                        st.caption(f"+{len(flights) - 8} more flights available")

                # ── Cost Breakdown (rescheduling) ─────────────
                if is_resched:
                    st.markdown("")
                    st.markdown('<p class="section-label">Cost breakdown</p>', unsafe_allow_html=True)
                    fee = result.get("fee", 0)
                    fare_diff = result.get("fare_difference", 0)
                    total = result.get("total_cost", 0)

                    cost_html = '<div class="card">'
                    cost_html += f'<div class="cost-line"><span>Rescheduling fee</span><span>₹{fee:,.0f}</span></div>'
                    if fare_diff > 0:
                        cost_html += (
                            f'<div class="cost-line"><span>Fare difference</span>'
                            f'<span style="color:{C_ERROR};">+₹{fare_diff:,.0f}</span></div>'
                        )
                    elif fare_diff < 0:
                        cost_html += (
                            f'<div class="cost-line"><span>Fare savings</span>'
                            f'<span style="color:{C_SUCCESS};">−₹{abs(fare_diff):,.0f}</span></div>'
                        )
                    cost_html += (
                        f'<div class="cost-line cost-total">'
                        f'<span>Total additional cost</span>'
                        f'<span>₹{total:,.0f}</span></div>'
                    )
                    cost_html += '</div>'
                    st.markdown(cost_html, unsafe_allow_html=True)

            # ── Right: Response + Steps ───────────────────────
            with col_right:
                st.markdown('<p class="section-label">Agent response</p>', unsafe_allow_html=True)
                resp_html = format_response(result.get("message", ""))
                st.markdown(
                    f'<div class="response-box">{resp_html}</div>',
                    unsafe_allow_html=True,
                )

                steps = result.get("steps", [])
                if steps:
                    st.markdown("")
                    st.markdown(
                        f'<p class="section-label">Workflow · {len(steps)} steps</p>',
                        unsafe_allow_html=True,
                    )
                    with st.expander("View execution steps", expanded=False):
                        for step in steps:
                            render_step(step)

        # ── Non-completed states ──────────────────────────────
        elif status in ("Failed", "Incomplete", "Unsupported"):
            resp_html = format_response(result.get("message", ""))
            st.markdown(
                f'<div class="response-box">{resp_html}</div>',
                unsafe_allow_html=True,
            )
            steps = result.get("steps", [])
            if steps:
                with st.expander("View execution steps"):
                    for step in steps:
                        render_step(step)

    elif process_btn and not user_query:
        st.warning("Enter a request to get started.")


# ══════════════════════════════════════════════════════════════
# BOOKINGS PAGE
# ══════════════════════════════════════════════════════════════

elif page == "Bookings":
    st.markdown('<p class="page-title">Bookings</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-subtitle">'
        'All customer bookings. Reference booking IDs when requesting rescheduling.'
        '</p>',
        unsafe_allow_html=True,
    )

    bookings = fetch_bookings()
    if bookings:
        df = pd.DataFrame(bookings)
        display_cols = [
            "booking_id", "customer_name", "airline",
            "origin", "origin_code", "destination", "destination_code",
            "travel_date", "status", "ticket_price",
        ]
        df = df[[c for c in display_cols if c in df.columns]]
        rename = {
            "booking_id": "Booking ID",
            "customer_name": "Customer",
            "airline": "Airline",
            "origin": "From",
            "origin_code": "IATA",
            "destination": "To",
            "destination_code": "IATA ",
            "travel_date": "Date",
            "status": "Status",
            "ticket_price": "Price (₹)",
        }
        df = df.rename(columns=rename)

        st.markdown(
            f'<p class="section-label">{len(df)} bookings</p>',
            unsafe_allow_html=True,
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No bookings found. Make sure the backend is running.")


# ══════════════════════════════════════════════════════════════
# LOGS PAGE
# ══════════════════════════════════════════════════════════════

elif page == "Logs":
    st.markdown('<p class="page-title">Execution Logs</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="page-subtitle">'
        'Audit trail of all agent workflow executions.'
        '</p>',
        unsafe_allow_html=True,
    )

    logs = fetch_logs()
    if logs:
        df = pd.DataFrame(logs)
        display_cols = [
            "timestamp", "booking_id", "detected_intent",
            "execution_status", "processing_time", "user_query",
        ]
        df = df[[c for c in display_cols if c in df.columns]]
        rename = {
            "timestamp": "Time",
            "booking_id": "Booking",
            "detected_intent": "Intent",
            "execution_status": "Status",
            "processing_time": "Duration",
            "user_query": "Query",
        }
        df = df.rename(columns=rename)

        st.markdown(
            f'<p class="section-label">{len(df)} executions</p>',
            unsafe_allow_html=True,
        )
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("")
        st.markdown('<p class="section-label">Details</p>', unsafe_allow_html=True)
        for i, log in enumerate(logs[:10]):
            ts = log.get("timestamp", "")
            intent = log.get("detected_intent", "")
            status = log.get("execution_status", "")
            with st.expander(f"{ts}  ·  {intent}  ·  {status}"):
                st.json(log)
    else:
        st.info("No logs yet. Process a request first.")
