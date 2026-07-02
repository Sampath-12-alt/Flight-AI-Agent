# AI Flight Rescheduling Agent ✈️

An **Agentic AI** application that automates flight rescheduling by combining LLM reasoning, Retrieval-Augmented Generation (RAG), and modular business services.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![LangGraph](https://img.shields.io/badge/LangGraph-Agent_Framework-green?style=flat-square)
![Gemini](https://img.shields.io/badge/Gemini-LLM-orange?style=flat-square&logo=google)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-teal?style=flat-square&logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-red?style=flat-square&logo=streamlit)

---

## 📌 Overview

Customer support teams in travel companies spend significant time handling repetitive flight rescheduling requests. Each request requires checking booking details, reviewing airline policies, calculating rescheduling fees, updating booking records, and drafting customer responses.

This project demonstrates how an **AI Agent** can automate that entire workflow.

**Unlike a traditional chatbot** that only generates answers, this agent **plans and executes** a complete business process by invoking multiple services.

---

## 🎯 Business Problem

**Current manual workflow:**

```
Customer Request → Support Executive → Booking Lookup → Policy Search
    → Fee Calculation → Booking Update → Customer Reply
```

This process is repetitive, time-consuming, and prone to manual errors.

---

## 🧠 Proposed Solution

The AI Flight Rescheduling Agent automates the workflow by:

1. **Understanding** customer requests in natural language
2. **Identifying** customer intent (Flight Rescheduling vs. other)
3. **Retrieving** booking information from the database
4. **Searching** airline policies using RAG (Retrieval-Augmented Generation)
5. **Calculating** rescheduling fees based on business rules
6. **Updating** booking records in the database
7. **Generating** professional customer responses
8. **Logging** all actions for auditing

---

## 🏗️ System Architecture

```
Customer
     │
     ▼
Streamlit UI
     │
     ▼
FastAPI Backend
     │
     ▼
LangGraph Agent (Orchestrator)
     │
     ├── Intent Detection (Gemini LLM)
     ├── Entity Extraction (Gemini LLM)
     ├── Booking Service (SQLite)
     ├── Policy Service (ChromaDB RAG)
     ├── Fee Calculation Service
     ├── Booking Update Service (SQLite)
     ├── Response Generation (Gemini LLM)
     └── Logging Service (SQLite + File)
```

---

## 🛠️ Technology Stack

| Component          | Technology          |
|--------------------|---------------------|
| Language           | Python 3.10+        |
| Agent Framework    | LangGraph           |
| LLM                | Google Gemini        |
| Backend            | FastAPI              |
| Frontend           | Streamlit            |
| Database           | SQLite               |
| Vector Database    | ChromaDB             |
| Version Control    | Git                  |

---

## 📁 Project Structure

```
AI-agent/
├── main.py                          # FastAPI entry point
├── config.py                        # Centralized configuration
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variable template
├── .gitignore
│
├── src/
│   ├── agent/
│   │   ├── graph.py                 # LangGraph workflow orchestrator
│   │   ├── state.py                 # Agent state definition
│   │   └── prompts.py               # LLM prompts
│   │
│   ├── services/
│   │   ├── booking_service.py       # Booking lookup
│   │   ├── policy_service.py        # RAG policy retrieval
│   │   ├── fee_service.py           # Fee calculation
│   │   ├── booking_update_service.py # Booking modification
│   │   ├── response_service.py      # Response generation
│   │   └── logging_service.py       # Audit logging
│   │
│   ├── database/
│   │   └── sqlite.py                # Database operations
│   │
│   ├── rag/
│   │   ├── ingest.py                # Policy document ingestion
│   │   └── retriever.py             # Semantic policy retrieval
│   │
│   ├── api/
│   │   └── routes.py                # FastAPI endpoints
│   │
│   └── ui/
│       └── streamlit_app.py         # Streamlit frontend
│
├── data/
│   └── airline_policies/            # Airline policy documents
│       ├── air_india.md
│       ├── indigo.md
│       ├── spicejet.md
│       └── vistara.md
│
├── tests/
│   ├── test_booking_service.py
│   ├── test_fee_service.py
│   └── test_agent.py
│
└── docs/
    ├── SRS.md                       # Software Requirements Specification
    └── architecture.md              # Architecture documentation
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- Google Gemini API Key ([Get one free](https://aistudio.google.com/apikey))

### 1. Clone the Repository
```bash
git clone <repository-url>
cd AI-agent
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate      # macOS/Linux
# venv\Scripts\activate       # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### 5. Start the Backend
```bash
python main.py
```
The backend will:
- Initialize the SQLite database with sample bookings
- Ingest airline policies into ChromaDB
- Start the FastAPI server at `http://localhost:8000`

### 6. Start the Frontend (in a new terminal)
```bash
streamlit run src/ui/streamlit_app.py
```
Open `http://localhost:8501` in your browser.

---

## 📖 API Documentation

Once the backend is running, visit `http://localhost:8000/docs` for interactive API documentation.

| Method | Endpoint              | Description                        |
|--------|------------------------|------------------------------------|
| POST   | `/agent/process`       | Process a rescheduling request      |
| GET    | `/booking/{booking_id}`| Get booking details                 |
| GET    | `/bookings`            | List all bookings                   |
| GET    | `/logs`                | Get execution history               |
| GET    | `/health`              | Health check                        |

---

## 💡 Example Scenario

### Customer Request
```
My booking ID is BK1024. I need to change my flight from 20 July to 23 July.
```

### Agent Workflow
1. ✅ **Intent Detected**: Flight Rescheduling
2. ✅ **Extracted**: Booking ID = BK1024, Date = 2025-07-23
3. ✅ **Booking Found**: Rahul Sharma | Air India | Delhi → Mumbai
4. ✅ **Policy Retrieved**: 3 relevant sections for Air India
5. ✅ **Fee Calculated**: ₹2,500 — 24 hours to 3 days before departure
6. ✅ **Booking Updated**: 2025-07-20 → 2025-07-23
7. ✅ **Response Generated**
8. ✅ **Execution Logged**

### Agent Response
```
Dear Rahul Sharma,

Your flight rescheduling request has been successfully processed.

Booking ID: BK1024
Airline: Air India
Route: Delhi → Mumbai
Previous Date: 2025-07-20
New Date: 2025-07-23
Rescheduling Fee: ₹2,500

Your updated itinerary has been generated successfully.

Thank you for choosing our services.
Travel Support Team
```

---

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific tests
python -m pytest tests/test_booking_service.py -v
python -m pytest tests/test_fee_service.py -v
```

---

## 🔮 Future Enhancements

- Flight cancellation support
- Refund processing
- Hotel booking modifications
- Real airline API integration
- Human approval workflow
- PostgreSQL migration
- Docker deployment
- CI/CD pipeline
- Multi-agent architecture
- Email/WhatsApp notifications

---

## 📚 Learning Outcomes

This project demonstrates practical implementation of:

- ✅ **Agentic AI** — Autonomous task execution
- ✅ **Tool Calling** — LLM interacting with external services
- ✅ **Workflow Orchestration** — LangGraph state machine
- ✅ **RAG** — Retrieval-Augmented Generation with ChromaDB
- ✅ **Service-Oriented Architecture** — Modular, testable design
- ✅ **Full-Stack AI Application** — FastAPI + Streamlit

---

## 👤 Author

Developed as an **Agentic AI portfolio project** to demonstrate the application of Large Language Models in solving real-world business problems within the travel industry.

---

## 📄 License

This project is for educational and portfolio purposes.
