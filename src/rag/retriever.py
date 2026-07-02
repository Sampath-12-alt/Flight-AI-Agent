"""
RAG Retriever Module.

Queries ChromaDB to retrieve relevant airline policy chunks
based on airline name or semantic similarity.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import CHROMA_DIR, CHROMA_COLLECTION_NAME, RAG_TOP_K

import chromadb


def get_collection():
    """Get the ChromaDB collection for airline policies."""
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        return client.get_collection(CHROMA_COLLECTION_NAME)
    except Exception:
        print("❌ Policy collection not found. Run ingest.py first.")
        return None


def retrieve_policy(airline_name: str, top_k: int = RAG_TOP_K) -> dict:
    """
    Retrieve the most relevant policy information for a given airline.

    Args:
        airline_name: Name of the airline (e.g., "Air India", "IndiGo")
        top_k: Number of top results to return

    Returns:
        dict with keys: 'airline', 'policy_text', 'chunks', 'found'
    """
    collection = get_collection()

    if collection is None:
        return {
            "airline": airline_name,
            "policy_text": "",
            "chunks": [],
            "found": False,
            "error": "Policy database not initialized. Run ingest.py first.",
        }

    # Query using the airline name as the search query to get relevant policy chunks
    query_text = f"{airline_name} flight rescheduling policy fees rules"

    results = collection.query(
        query_texts=[query_text],
        n_results=top_k,
        where={"airline": airline_name},
    )

    if not results["documents"][0]:
        # Try broader search without metadata filter
        results = collection.query(
            query_texts=[query_text],
            n_results=top_k,
        )

    if not results["documents"][0]:
        return {
            "airline": airline_name,
            "policy_text": "",
            "chunks": [],
            "found": False,
            "error": f"No policy found for {airline_name}.",
        }

    # Combine retrieved chunks into a single policy text
    chunks = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0] if results.get("distances") else [0] * len(chunks)

    policy_text = "\n\n---\n\n".join(chunks)

    return {
        "airline": airline_name,
        "policy_text": policy_text,
        "chunks": [
            {
                "text": chunk,
                "metadata": meta,
                "distance": dist,
            }
            for chunk, meta, dist in zip(chunks, metadatas, distances)
        ],
        "found": True,
    }


def list_available_airlines() -> list[str]:
    """List all airlines that have policies in the knowledge base."""
    collection = get_collection()
    if collection is None:
        return []

    # Get all unique airline names from metadata
    all_data = collection.get(include=["metadatas"])
    airlines = set()
    for meta in all_data["metadatas"]:
        if "airline" in meta:
            airlines.add(meta["airline"])

    return sorted(airlines)


# ── Standalone testing ────────────────────────────────────────
if __name__ == "__main__":
    print("\n📋 Available Airlines:")
    for airline in list_available_airlines():
        print(f"  ✈️  {airline}")

    print("\n🔍 Testing retrieval for 'Air India':")
    result = retrieve_policy("Air India")
    if result["found"]:
        print(f"  ✅ Found {len(result['chunks'])} relevant chunks")
        print(f"  📄 Policy preview: {result['policy_text'][:200]}...")
    else:
        print(f"  ❌ {result.get('error', 'Not found')}")
