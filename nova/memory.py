from datetime import datetime
from uuid import uuid4

import chromadb

from .config import MEMORY_DIR, MEMORY_FILE

_collection = None


def _get_collection():
    global _collection
    if _collection is None:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(MEMORY_DIR / "chroma"))
        _collection = client.get_or_create_collection("notes")
    return _collection


def remember(content: str) -> None:
    collection = _get_collection()
    timestamp = datetime.now().isoformat(timespec="minutes")
    collection.add(
        ids=[str(uuid4())],
        documents=[content],
        metadatas=[{"timestamp": timestamp}],
    )
    _log(content, timestamp)


def recall(query: str, n_results: int = 5) -> list[str]:
    collection = _get_collection()
    count = collection.count()
    if count == 0:
        return []
    results = collection.query(query_texts=[query], n_results=min(n_results, count))
    return results["documents"][0]


def _log(content: str, timestamp: str) -> None:
    """Human-readable audit trail, separate from the vector index used for recall."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with MEMORY_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\n## {timestamp}\n{content}\n")
