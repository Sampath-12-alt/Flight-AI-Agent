"""
RAG Ingestion Module.

Loads airline policy markdown files, splits them into chunks,
generates embeddings, and stores them in ChromaDB for semantic retrieval.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import POLICIES_DIR, CHROMA_DIR, CHROMA_COLLECTION_NAME, CHUNK_SIZE, CHUNK_OVERLAP

import chromadb
from chromadb.config import Settings


def load_policy_documents(policies_dir: Path = POLICIES_DIR) -> list[dict]:
    """
    Load all markdown policy files from the policies directory.
    Returns a list of dicts with 'content', 'airline', and 'source' keys.
    """
    # Map filenames to canonical airline brand names
    AIRLINE_NAME_MAP = {
        "air_india": "Air India",
        "indigo": "IndiGo",
        "spicejet": "SpiceJet",
        "vistara": "Vistara",
    }

    documents = []

    for filepath in sorted(policies_dir.glob("*.md")):
        content = filepath.read_text(encoding="utf-8")
        airline_name = AIRLINE_NAME_MAP.get(filepath.stem, filepath.stem.replace("_", " ").title())
        documents.append({
            "content": content,
            "airline": airline_name,
            "source": str(filepath.name),
        })
        print(f"  📄 Loaded: {filepath.name} ({len(content)} chars)")

    return documents


def split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks for embedding.
    Uses a simple character-based splitter with paragraph awareness.
    """
    # Split by double newlines first to respect paragraph boundaries
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) <= chunk_size:
            current_chunk += para + "\n\n"
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def ingest_policies():
    """
    Main ingestion pipeline:
    1. Load policy documents
    2. Split into chunks
    3. Store in ChromaDB with metadata
    """
    print("\n🔄 Starting policy ingestion...\n")

    # Load documents
    documents = load_policy_documents()
    if not documents:
        print("❌ No policy documents found!")
        return

    # Initialize ChromaDB
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Delete existing collection if it exists (for re-ingestion)
    try:
        client.delete_collection(CHROMA_COLLECTION_NAME)
        print(f"\n🗑️  Cleared existing collection: {CHROMA_COLLECTION_NAME}")
    except Exception:
        pass

    collection = client.create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"description": "Airline rescheduling policies for RAG retrieval"},
    )

    # Process each document
    all_chunks = []
    all_metadatas = []
    all_ids = []

    for doc in documents:
        chunks = split_into_chunks(doc["content"])
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc['source']}__chunk_{i}"
            all_chunks.append(chunk)
            all_metadatas.append({
                "airline": doc["airline"],
                "source": doc["source"],
                "chunk_index": i,
            })
            all_ids.append(chunk_id)

    # Add to ChromaDB (uses default embedding function)
    collection.add(
        documents=all_chunks,
        metadatas=all_metadatas,
        ids=all_ids,
    )

    print(f"\n✅ Ingested {len(all_chunks)} chunks from {len(documents)} policy documents.")
    print(f"   Collection: {CHROMA_COLLECTION_NAME}")
    print(f"   Storage: {CHROMA_DIR}")

    return collection


# ── Standalone execution ──────────────────────────────────────
if __name__ == "__main__":
    ingest_policies()
