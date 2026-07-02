"""
Streamlit UI for the AI Flight Search & Rescheduling Agent v3.

Features:
- Dual-intent: Flight Search AND Flight Rescheduling
- Multi-day flight search results with date grouping
- Recommended flight highlight with comparison badges
- Cost breakdown for rescheduling
- Step-by-step workflow visualization
- Bookings and Logs browsers
"""

import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import requests
import pandas as pd

from config import FASTAPI_URL

# ══════════════════════════════════════════════════════════════
# PAGE CONFIGURATION
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="AI Flight Agent",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════
# CUSTOM CSS
# ══════════════════════════════════════════════════════════════
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    .stApp { font-family: 'Inter', sans-serif; }

    .main-header {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        padding: 2rem 2.5rem; border-radius: 16px; margin-bottom: 2rem;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .main-header h1 { color: #fff; font-size: 2rem; font-weight: 700; margin: 0; }
    .main-header p { color: rgba(255,255,255,0.65); font-size: 0.95rem; margin-top: 0.5rem; }

    .badge {
        display: inline-block; padding: 0.25rem 0.75rem; border-radius: 20px;
        font-size: 0.75rem; font-weight: 600; letter-spacing: 0.04em;
        margin-right: 0.5rem; margin-bottom: 0.75rem;
    }
    .badge-ai { background: rgba(99,102,241,0.2); color: #818cf8; border: 1px solid rgba(99,102,241,0.3); }
    .badge-rag { background: rgba(16,185,129,0.2); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
    .badge-agent { background: rgba(245,158,11,0.2); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
    .badge-live { background: rgba(239,68,68,0.2); color: #f87171; border: 1px solid rgba(239,68,68,0.3); }
    .badge-search { background: rgba(59,130,246,0.2); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); }

    .step-card {
        background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px; padding: 0.75rem 1rem; margin-bottom: 0.5rem;
        font-size: 0.9rem; transition: all 0.3s ease;
    }
    .step-card:hover { background: rgba(255,255,255,0.06); }
    .step-success { border-left: 3px solid #10b981; }
    .step-error { border-left: 3px solid #ef4444; }
    .step-info { border-left: 3px solid #3b82f6; }

    .stat-card {
        background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px; padding: 1rem 1.25rem; text-align: center;
    }
    .stat-card h2 { color: #818cf8; font-size: 1.5rem; margin: 0; }
    .stat-card p { color: rgba(255,255,255,0.5); font-size: 0.75rem; margin: 0.25rem 0 0;
        text-transform: uppercase; letter-spacing: 0.06em; }

    .flight-card {
        background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px; padding: 1rem 1.25rem; margin-bottom: 0.75rem;
    }
    .flight-card:hover { background: rgba(255,255,255,0.06); }
    .flight-recommended {
        background: linear-gradient(135deg, rgba(16,185,129,0.08), rgba(59,130,246,0.08));
        border: 1px solid rgba(16,185,129,0.3);
        box-shadow: 0 4px 16px rgba(16,185,129,0.1);
    }

    .flight-tag {
        display: inline-block; padding: 0.15rem 0.5rem; border-radius: 12px;
        font-size: 0.7rem; font-weight: 600; margin-right: 0.4rem;
        background: rgba(99,102,241,0.15); color: #a5b4fc;
        border: 1px solid rgba(99,102,241,0.2);
    }
    .tag-recommended { background: rgba(16,185,129,0.2); color: #34d399; border-color: rgba(16,185,129,0.3); }
    .tag-cheapest { background: rgba(245,158,11,0.2); color: #fbbf24; border-color: rgba(245,158,11,0.3); }
    .tag-fastest { background: rgba(59,130,246,0.2); color: #60a5fa; border-color: rgba(59,130,246,0.3); }

    .response-card {
        background: linear-gradient(135deg, rgba(16,185,129,0.08), rgba(59,130,246,0.08));
        border: 1px solid rgba(16,185,129,0.2); border-radius: 16px;
        padding: 1.5rem 2rem; margin-top: 1rem; line-height: 1.7;
    }
    .response-card h3 { color: #34d399; font-size: 1.1rem; margin-bottom: 1rem; }

    .cost-card {
        background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px; padding: 1rem 1.5rem;
    }
    .cost-row { display: flex; justify-content: space-between; padding: 0.4rem 0; font-size: 0.9rem; }
    .cost-row.total { border-top: 1px solid rgba(255,255,255,0.1); padding-top: 0.6rem; margin-top: 0.4rem; font-weight: 700; }

    .sidebar-section {
        background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px; padding: 1rem; margin-bottom: 1rem;
    }

    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def call_agent_api(query: str) -> dict | None:
    try:
        r = requests.post(f"{FASTAPI_URL}/agent/process", json={"query": query}, timeout=120)
        return r.json() if r.status_code == 200 else None
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Cannot connect to backend. Start it with: `python main.py`")
        return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None


def get_bookings():
    try:
        r = requests.get(f"{FASTAPI_URL}/bookings", timeout=10)
        return r.json().get("bookings", []) if r.status_code == 200 else []
    except: return []


def get_logs():
    try:
        r = requests.get(f"{FASTAPI_URL}/logs", timeout=10)
        return r.json().get("logs", []) if r.status_code == 200 else []
    except: return []


def render_step(step_text):
    css = "step-success" if "✅" in step_text else "step-error" if "❌" in step_text else "step-info"
    st.markdown(f'<div class="step-card {css}">{step_text}</div>', unsafe_allow_html=True)


def render_flight_card(flight, is_recommended=False, show_date=False):
    """Render a flight card using Streamlit-native components."""
    dep = flight.get("departure_time", "").split("T")[1][:5] if "T" in flight.get("departure_time", "") else ""
    arr = flight.get("arrival_time", "").split("T")[1][:5] if "T" in flight.get("arrival_time", "") else ""
    stops_str = "Direct" if flight.get("stops", 0) == 0 else f"{flight.get('stops')} stop(s)"
    date_str = flight.get("search_date", "") if show_date else ""
    price = flight.get("price", 0)

    # Build tags
    tags = []
    if is_recommended:
        tags.append("⭐ Recommended")
    all_flights = st.session_state.get("_current_flights", [])
    if all_flights:
        if price == min(f["price"] for f in all_flights):
            tags.append("💰 Cheapest")
        if flight.get("duration_hours") == min(f.get("duration_hours", 99) for f in all_flights):
            tags.append("⚡ Fastest")
        if flight.get("stops", 1) == 0:
            tags.append("✈️ Direct")

    border_color = "#10b981" if is_recommended else "rgba(255,255,255,0.08)"
    bg = "rgba(16,185,129,0.06)" if is_recommended else "rgba(255,255,255,0.02)"

    # Build compact HTML that Streamlit renders reliably
    tags_str = " &nbsp;".join(
        f'<span style="background:rgba(99,102,241,0.15);color:#a5b4fc;padding:2px 8px;'
        f'border-radius:12px;font-size:0.7rem;font-weight:600;">{t}</span>'
        for t in tags
    )

    date_part = f' <span style="color:rgba(255,255,255,0.4);font-size:0.8rem;">| {date_str}</span>' if date_str else ""

    html = (
        f'<div style="background:{bg};border:1px solid {border_color};border-radius:12px;'
        f'padding:12px 16px;margin-bottom:8px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<div><b>{flight.get("flight_number","")}</b>'
        f' <span style="color:rgba(255,255,255,0.5);">{flight.get("airline","")}</span>'
        f'{date_part}</div>'
        f'<div style="font-size:1.2rem;font-weight:700;color:#818cf8;">₹{price:,.0f}</div>'
        f'</div>'
        f'<div style="color:rgba(255,255,255,0.6);font-size:0.85rem;margin-top:6px;">'
        f'{dep} → {arr} &nbsp;|&nbsp; {flight.get("duration_display","")} &nbsp;|&nbsp; {stops_str}'
        f'</div>'
    )
    if tags_str:
        html += f'<div style="margin-top:6px;">{tags_str}</div>'
    html += '</div>'

    st.markdown(html, unsafe_allow_html=True)


def format_response_html(text: str) -> str:
    """Convert plain text response to HTML with proper line breaks."""
    import html as html_lib
    safe = html_lib.escape(text)
    # Convert newlines to <br>
    safe = safe.replace("\n\n", "<br><br>")
    safe = safe.replace("\n", "<br>")
    # Re-bold patterns like ── Section ──
    safe = safe.replace("──", "—")
    return safe


# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### 🧭 Navigation")
    page = st.radio("", ["🤖 Agent", "📋 Bookings", "📊 Logs"], label_visibility="collapsed")

    st.markdown("---")
    st.markdown("### 🏗️ Architecture")
    st.markdown("""
    <div class="sidebar-section">
        <span class="badge badge-ai">Gemini LLM</span>
        <span class="badge badge-live">Live Flights</span>
        <span class="badge badge-search">Dual Intent</span>
        <span class="badge badge-rag">RAG Pipeline</span>
        <span class="badge badge-agent">LangGraph</span>
        <br/>
        <strong>Stack:</strong> LangGraph + Gemini + Aviationstack + FastAPI + ChromaDB + SQLite
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📐 Dual Workflow")
    st.markdown("""
    ```
    Customer Request
         ↓
    Detect Intent
       /       \\
    Search    Reschedule
      ↓          ↓
    Extract    Extract
      ↓          ↓
    Parse      Booking
    Dates        ↓
      ↓       Flights
    Multi-       ↓
    Search    Compare
      ↓          ↓
    Compare   Policy+Fee
      ↓          ↓
    Response   Update
      ↓          ↓
     Log        Log
    ```
    """)

    st.markdown("---")
    st.markdown(
        "<p style='color: rgba(255,255,255,0.3); font-size: 0.75rem; text-align: center;'>"
        "AI Flight Agent v3.0<br/>Dual Intent | Live Search</p>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════
# AGENT PAGE
# ══════════════════════════════════════════════════════════════

if page == "🤖 Agent":
    st.markdown("""
    <div class="main-header">
        <h1>✈️ AI Flight Search & Rescheduling Agent</h1>
        <p>
            Search for flights using natural language or reschedule existing bookings.
            The agent understands flexible dates like "next week" or "this weekend"
            and searches across multiple days to find your best option.
        </p>
        <span class="badge badge-search">Natural Language Search</span>
        <span class="badge badge-ai">Gemini LLM</span>
        <span class="badge badge-live">Live Flights</span>
        <span class="badge badge-rag">RAG Policy</span>
        <span class="badge badge-agent">LangGraph</span>
    </div>
    """, unsafe_allow_html=True)

    col_input, col_samples = st.columns([3, 2])

    with col_input:
        st.markdown("#### 💬 What would you like to do?")
        user_query = st.text_area(
            "Enter your request:",
            height=120,
            placeholder="e.g., Find me the cheapest flight from Delhi to Mumbai next week.",
            label_visibility="collapsed",
        )
        process_btn = st.button("🚀 Process Request", type="primary", use_container_width=True)

    with col_samples:
        st.markdown("#### 📝 Try These Examples")

        search_samples = [
            "Find flights from Hyderabad to Mumbai next week. Cheapest option.",
            "I want to travel from Delhi to Bangalore tomorrow.",
            "Show me flights from Chennai to Delhi this weekend.",
            "Any flights from Mumbai to Goa next month?",
        ]
        resched_samples = [
            "My booking BK1024, change to July 25.",
            "Reschedule booking BK1025 to August 5th.",
        ]

        st.markdown("**🔍 Flight Search:**")
        for i, s in enumerate(search_samples):
            if st.button(f"📨 {s[:50]}...", key=f"ss_{i}", use_container_width=True):
                st.session_state["sample_query"] = s
                st.rerun()

        st.markdown("**🔄 Rescheduling:**")
        for i, s in enumerate(resched_samples):
            if st.button(f"📨 {s[:50]}...", key=f"rs_{i}", use_container_width=True):
                st.session_state["sample_query"] = s
                st.rerun()

    if "sample_query" in st.session_state:
        user_query = st.session_state.pop("sample_query")

    st.markdown("---")

    # ── Process Request ───────────────────────────────────────
    if process_btn and user_query:
        st.markdown("#### ⚙️ Agent Workflow Execution")

        with st.spinner("🤖 Agent is processing..."):
            start = time.time()
            result = call_agent_api(user_query)
            elapsed = time.time() - start

        if result:
            intent = result.get("intent", "Unknown")
            is_search = intent == "Flight Search"
            is_reschedule = intent == "Flight Rescheduling"

            # ── Stats Row ─────────────────────────────────────
            cols = st.columns(5)
            with cols[0]:
                emoji = "✅" if result["status"] == "Completed" else "⚠️"
                st.markdown(f'<div class="stat-card"><h2>{emoji}</h2><p>{result["status"]}</p></div>', unsafe_allow_html=True)
            with cols[1]:
                intent_short = "Search" if is_search else "Reschedule" if is_reschedule else intent[:10]
                st.markdown(f'<div class="stat-card"><h2>{"🔍" if is_search else "🔄"}</h2><p>{intent_short}</p></div>', unsafe_allow_html=True)
            with cols[2]:
                st.markdown(f'<div class="stat-card"><h2>{result.get("num_flights_found", 0)}</h2><p>Flights Found</p></div>', unsafe_allow_html=True)
            with cols[3]:
                dates_count = len(result.get("search_dates", [])) if is_search else 1
                st.markdown(f'<div class="stat-card"><h2>{dates_count}</h2><p>Dates Searched</p></div>', unsafe_allow_html=True)
            with cols[4]:
                st.markdown(f'<div class="stat-card"><h2>{result.get("processing_time", elapsed):.1f}s</h2><p>Time</p></div>', unsafe_allow_html=True)

            st.markdown("")

            if result["status"] == "Completed":
                flights = result.get("available_flights", [])
                recommended = result.get("recommended_flight", {})
                st.session_state["_current_flights"] = flights

                col_flights, col_response = st.columns([1, 1])

                with col_flights:
                    if flights:
                        title = f"✈️ Flights ({len(flights)} found"
                        if is_search and result.get("search_dates"):
                            title += f" across {len(result['search_dates'])} days"
                        title += ")"
                        st.markdown(f"##### {title}")

                        # Show top 8 flights
                        for flight in flights[:8]:
                            is_rec = flight.get("flight_number") == recommended.get("flight_number", "")
                            render_flight_card(flight, is_recommended=is_rec, show_date=is_search)

                        if len(flights) > 8:
                            st.caption(f"... and {len(flights) - 8} more flights")

                    # Cost breakdown (rescheduling only)
                    if is_reschedule:
                        st.markdown("##### 💰 Cost Breakdown")
                        fee = result.get("fee", 0)
                        fare_diff = result.get("fare_difference", 0)
                        total = result.get("total_cost", 0)

                        cost_html = '<div class="cost-card">'
                        cost_html += f'<div class="cost-row"><span>Rescheduling Fee</span><span>₹{fee:,.0f}</span></div>'
                        if fare_diff > 0:
                            cost_html += f'<div class="cost-row"><span>Fare Difference</span><span style="color: #f87171;">+₹{fare_diff:,.0f}</span></div>'
                        elif fare_diff < 0:
                            cost_html += f'<div class="cost-row"><span>Fare Savings</span><span style="color: #34d399;">-₹{abs(fare_diff):,.0f}</span></div>'
                        cost_html += f'<div class="cost-row total"><span>Total</span><span style="color: #818cf8;">₹{total:,.0f}</span></div>'
                        cost_html += '</div>'
                        st.markdown(cost_html, unsafe_allow_html=True)

                with col_response:
                    st.markdown("##### 💬 Agent Response")
                    icon = "✅" if is_reschedule else "🔍"
                    label = "Confirmation" if is_reschedule else "Search Results"
                    response_html = format_response_html(result["message"])
                    st.markdown(
                        f'<div class="response-card"><h3>{icon} {label}</h3>'
                        f'<div style="line-height:1.7;">{response_html}</div></div>',
                        unsafe_allow_html=True,
                    )

                    st.markdown("##### 📋 Workflow Steps")
                    for step in result.get("steps", []):
                        render_step(step)

            elif result["status"] in ["Failed", "Incomplete", "Unsupported"]:
                st.markdown("##### 💬 Response")
                response_html = format_response_html(result["message"])
                st.markdown(
                    f'<div class="response-card" style="border-color: rgba(59,130,246,0.3);">'
                    f'<h3>ℹ️ Agent Response</h3><div style="line-height:1.7;">{response_html}</div></div>',
                    unsafe_allow_html=True,
                )
                if result.get("steps"):
                    st.markdown("##### 📋 Workflow Steps")
                    for step in result.get("steps", []):
                        render_step(step)

    elif process_btn and not user_query:
        st.warning("Please enter a request.")


# ══════════════════════════════════════════════════════════════
# BOOKINGS PAGE
# ══════════════════════════════════════════════════════════════

elif page == "📋 Bookings":
    st.markdown("""
    <div class="main-header">
        <h1>📋 Booking Database</h1>
        <p>View all bookings. Use Booking IDs for rescheduling requests.</p>
    </div>
    """, unsafe_allow_html=True)

    bookings = get_bookings()
    if bookings:
        df = pd.DataFrame(bookings)
        cols = ["booking_id", "customer_name", "airline", "origin", "origin_code",
                "destination", "destination_code", "travel_date", "status", "ticket_price"]
        df = df[[c for c in cols if c in df.columns]]
        df.columns = ["ID", "Customer", "Airline", "From", "IATA", "To", "IATA ", "Date", "Status", "₹ Price"]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No bookings found. Make sure the backend is running.")


# ══════════════════════════════════════════════════════════════
# LOGS PAGE
# ══════════════════════════════════════════════════════════════

elif page == "📊 Logs":
    st.markdown("""
    <div class="main-header">
        <h1>📊 Execution Logs</h1>
        <p>Audit trail of all agent workflow executions.</p>
    </div>
    """, unsafe_allow_html=True)

    logs = get_logs()
    if logs:
        df = pd.DataFrame(logs)
        cols = ["timestamp", "booking_id", "detected_intent", "execution_status", "processing_time", "user_query"]
        df = df[[c for c in cols if c in df.columns]]
        df.columns = ["Timestamp", "Booking", "Intent", "Status", "Time", "Query"]
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("#### 🔍 Details")
        for i, log in enumerate(logs[:10]):
            with st.expander(f"#{log.get('log_id', i+1)} — {log.get('timestamp', '')}"):
                st.json(log)
    else:
        st.info("No logs yet. Process a request first.")
