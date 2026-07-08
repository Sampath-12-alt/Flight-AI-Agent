"""
Centralized configuration for the AI Flight Rescheduling Agent.

All paths, model names, and settings are managed here so that
changes can be made in one place without modifying business logic.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load Environment Variables ────────────────────────────────
load_dotenv()

# Support Streamlit Cloud secrets (available when deployed on Streamlit Cloud)
try:
    import streamlit as st
    if hasattr(st, "secrets"):
        for key in ["GOOGLE_API_KEY", "AVIATIONSTACK_API_KEY"]:
            if key not in os.environ and key in st.secrets:
                os.environ[key] = st.secrets[key]
except Exception:
    pass  # Not running in Streamlit context


# ── Project Paths ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
POLICIES_DIR = DATA_DIR / "airline_policies"
CHROMA_DIR = DATA_DIR / "chroma_db"
LOG_DIR = BASE_DIR / "logs"
DB_PATH = DATA_DIR / "bookings.db"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# ── LLM Configuration ────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/embedding-001")
LLM_TEMPERATURE = 0.1  # Low temperature for consistent business responses

# ── RAG Configuration ────────────────────────────────────────
CHROMA_COLLECTION_NAME = "airline_policies"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
RAG_TOP_K = 3  # Number of relevant chunks to retrieve

# ── Aviationstack Flight Search API ─────────────────────────────
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY", "")

# ── API Configuration ────────────────────────────────────────
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))
FASTAPI_URL = os.getenv("FASTAPI_URL", f"http://localhost:{API_PORT}")

# ── Logging Configuration ────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = LOG_DIR / "agent.log"
