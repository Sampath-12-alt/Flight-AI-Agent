# Architecture Documentation

## 1. Architecture Overview

The AI Flight Rescheduling Agent follows a **modular, tool-based architecture**. The Large Language Model (LLM) acts as the reasoning engine, while specialized services perform business operations.

This separation allows the AI agent to make decisions while ensuring that business logic remains **deterministic and maintainable**.

---

## 2. High-Level Architecture Diagram

```mermaid
graph TD
    A[Customer] --> B[Streamlit UI]
    B --> C[FastAPI Backend]
    C --> D[LangGraph Agent]
    D --> E[Intent Detection<br/>Gemini LLM]
    D --> F[Entity Extraction<br/>Gemini LLM]
    D --> G[Booking Service<br/>SQLite]
    D --> H[Policy Service<br/>ChromaDB RAG]
    D --> I[Fee Calculation<br/>Business Rules]
    D --> J[Booking Update<br/>SQLite]
    D --> K[Response Generation<br/>Gemini LLM]
    D --> L[Logging Service<br/>SQLite + File]
```

---

## 3. Agent Workflow — LangGraph State Machine

```mermaid
stateDiagram-v2
    [*] --> DetectIntent
    DetectIntent --> ExtractEntities: Flight Rescheduling
    DetectIntent --> HandleUnsupported: Unsupported Intent

    ExtractEntities --> RetrieveBooking: All entities found
    ExtractEntities --> HandleMissingInfo: Missing booking ID or date

    RetrieveBooking --> RetrievePolicy: Booking found
    RetrieveBooking --> HandleError: Booking not found

    RetrievePolicy --> CalculateFee: Policy retrieved
    RetrievePolicy --> HandleError: Policy not found

    CalculateFee --> UpdateBooking: Fee calculated
    CalculateFee --> HandleError: Not eligible

    UpdateBooking --> GenerateResponse: Booking updated
    UpdateBooking --> HandleError: Update failed

    GenerateResponse --> LogExecution
    LogExecution --> [*]

    HandleError --> [*]
    HandleUnsupported --> [*]
    HandleMissingInfo --> [*]
```

---

## 4. Data Flow Sequence

```mermaid
sequenceDiagram
    participant Customer
    participant UI as Streamlit UI
    participant API as FastAPI
    participant Agent as LangGraph Agent
    participant LLM as Gemini LLM
    participant DB as SQLite
    participant RAG as ChromaDB

    Customer->>UI: Submit rescheduling request
    UI->>API: POST /agent/process
    API->>Agent: Invoke workflow

    Agent->>LLM: Detect intent
    LLM-->>Agent: Flight Rescheduling

    Agent->>LLM: Extract entities
    LLM-->>Agent: booking_id, new_date

    Agent->>DB: Lookup booking
    DB-->>Agent: Booking details

    Agent->>RAG: Search airline policy
    RAG-->>Agent: Relevant policy chunks

    Agent->>Agent: Calculate fee

    Agent->>DB: Update booking
    DB-->>Agent: Confirmation

    Agent->>LLM: Generate response
    LLM-->>Agent: Customer message

    Agent->>DB: Log execution
    Agent-->>API: Final result
    API-->>UI: Response
    UI-->>Customer: Display result
```

---

## 5. Component Details

### 5.1 LangGraph Agent (`src/agent/graph.py`)
- **Role**: Decision-making orchestrator
- **Type**: StateGraph with conditional edges
- **Nodes**: 8 workflow nodes + 3 error handlers
- **State**: `AgentState` TypedDict flows through all nodes

### 5.2 Business Services (`src/services/`)
Each service follows the Single Responsibility Principle:

| Service | Responsibility | Data Source |
|---------|---------------|-------------|
| BookingService | Retrieve booking details | SQLite |
| PolicyService | Retrieve airline policies | ChromaDB |
| FeeService | Calculate rescheduling fees | Business rules |
| BookingUpdateService | Update booking records | SQLite |
| ResponseService | Generate customer responses | Gemini LLM |
| LoggingService | Record audit trail | SQLite + File |

### 5.3 RAG Pipeline (`src/rag/`)
- **Ingestion**: Markdown policy files → chunks → ChromaDB embeddings
- **Retrieval**: Semantic search with airline metadata filtering
- **Fallback**: Broad search if airline-specific results are empty

### 5.4 Database (`src/database/sqlite.py`)
- **Bookings table**: 10 sample records with realistic Indian airline data
- **Execution logs table**: Full audit trail of every agent execution

---

## 6. Design Principles

1. **Modularity** — Each component has a single responsibility
2. **Separation of Concerns** — AI reasoning, business logic, and data storage are independent
3. **Extensibility** — New tools can be added without redesigning the system
4. **Maintainability** — Components can be updated independently
5. **Observability** — Every significant action is logged
6. **Graceful Degradation** — Keyword fallbacks when LLM is unavailable
