"""
AI Flight Rescheduling Agent — Main Application Entry Point.

Starts the FastAPI server and initializes the database and RAG pipeline.
"""

import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import API_HOST, API_PORT
from src.api.routes import router
from src.database.sqlite import init_db, seed_sample_data
from src.rag.ingest import ingest_policies


# ── Create FastAPI App ────────────────────────────────────────
app = FastAPI(
    title="AI Flight Search & Rescheduling Agent",
    description=(
        "An Agentic AI application that automates flight search and rescheduling "
        "by combining LLM reasoning, Retrieval-Augmented Generation (RAG), "
        "live flight APIs, and business services."
    ),
    version="3.0.0",
)

# ── CORS Middleware (for Streamlit communication) ─────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include API Routes ────────────────────────────────────────
app.include_router(router)


# ── Startup Event ─────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """Initialize database and RAG pipeline on application startup."""
    print("\n" + "=" * 60)
    print("🚀 AI Flight Rescheduling Agent — Starting Up")
    print("=" * 60)

    # Step 1: Initialize database
    print("\n📦 Step 1: Initializing Database...")
    init_db()
    seed_sample_data()

    # Step 2: Ingest airline policies into ChromaDB
    print("\n📄 Step 2: Ingesting Airline Policies...")
    try:
        ingest_policies()
    except Exception as e:
        print(f"⚠️  Policy ingestion warning: {e}")
        print("   The agent will still work but policy retrieval may be limited.")

    print("\n" + "=" * 60)
    print("✅ Agent is ready! API available at:")
    print(f"   http://{API_HOST}:{API_PORT}")
    print(f"   Docs: http://localhost:{API_PORT}/docs")
    print("=" * 60 + "\n")


# ── Run with Uvicorn ──────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
    )
