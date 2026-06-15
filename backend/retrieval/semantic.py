"""
Semantic retrieval — ChromaDB dense vector search.

Embeds the query with all-MiniLM-L6-v2, searches against a named
ChromaDB collection, optionally filtering by metadata (e.g. qtype
for nurse role).
"""

import chromadb
from sentence_transformers import SentenceTransformer

from backend.config import CHROMA_DIR, EMBEDDING_MODEL, TOP_K

# Module-level singletons — loaded once, reused across queries.
_embedder: SentenceTransformer | None = None
_chroma_client: chromadb.ClientAPI | None = None


def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def _get_chroma_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _chroma_client


def semantic_search(
    query: str,
    collection_name: str,
    top_k: int = TOP_K,
    where_filter: dict | None = None,
) -> list[dict]:
    """
    Search a ChromaDB collection by semantic similarity.

    Args:
        query:            User question.
        collection_name:  ChromaDB collection to search (e.g. "medical").
        top_k:            Number of results to return.
        where_filter:     Optional ChromaDB 'where' clause for metadata
                          filtering. Example for nurse qtype restriction:
                          {"qtype": {"$in": ["information", "symptoms", ...]}}

    Returns:
        List of dicts, each with keys: id, text, metadata, score.
        Score is cosine distance (lower = more similar).
    """
    client = _get_chroma_client()
    embedder = _get_embedder()

    try:
        collection = client.get_collection(name=collection_name)
    except Exception:
        print(f"[WARN] Collection '{collection_name}' not found.")
        return []

    # Cap top_k to actual collection size
    actual_count = collection.count()
    if actual_count == 0:
        return []
    k = min(top_k, actual_count)

    query_embedding = embedder.encode([query], convert_to_numpy=True).tolist()

    query_params = {
        "query_embeddings": query_embedding,
        "n_results": k,
    }
    if where_filter:
        query_params["where"] = where_filter

    results = collection.query(**query_params)

    output = []
    for doc_id, text, metadata, distance in zip(
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append(
            {
                "id": doc_id,
                "text": text,
                "metadata": metadata,
                "score": distance,
            }
        )

    return output
