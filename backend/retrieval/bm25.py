"""
BM25 keyword retrieval — sparse lexical search.

Loads a pickled BM25 index (built by index_corpus.py), tokenizes
the query, scores all documents, and returns top-k results.
Supports metadata filtering (e.g. nurse qtype restriction).
"""

import pickle
import re

import numpy as np

from backend.config import BM25_DIR, TOP_K

# Cache loaded indices — one pickle per collection, loaded on first use.
_bm25_cache: dict[str, dict] = {}


def _tokenize(text: str) -> list[str]:
    """Same tokenizer used during indexing — must match exactly."""
    return re.findall(r"\w+", text.lower())


def _load_bm25(collection_name: str) -> dict:
    """Load a pickled BM25 index. Cached after first load."""
    if collection_name not in _bm25_cache:
        pkl_path = BM25_DIR / f"{collection_name}.pkl"
        if not pkl_path.exists():
            print(f"[WARN] BM25 index not found: {pkl_path}")
            return {}
        with open(pkl_path, "rb") as f:
            _bm25_cache[collection_name] = pickle.load(f)
    return _bm25_cache[collection_name]


def bm25_search(
    query: str,
    collection_name: str,
    top_k: int = TOP_K,
    allowed_qtypes: list[str] | None = None,
) -> list[dict]:
    """
    Search a BM25 index by keyword relevance.

    Args:
        query:            User question.
        collection_name:  Which BM25 pickle to search (e.g. "medical").
        top_k:            Number of results to return.
        allowed_qtypes:   If set, only return documents whose metadata
                          'qtype' is in this list. Used for nurse filtering
                          on the medical collection.

    Returns:
        List of dicts, each with keys: id, text, metadata, score.
        Score is BM25 relevance (higher = more relevant).
    """
    payload = _load_bm25(collection_name)
    if not payload:
        return []

    tokens = _tokenize(query)
    if not tokens:
        return []

    bm25 = payload["bm25"]
    ids = payload["ids"]
    metadatas = payload["metadatas"]
    texts = payload["texts"]

    scores = bm25.get_scores(tokens)

    # Rank all documents by score (descending)
    ranked_indices = np.argsort(scores)[::-1]

    output = []
    for idx in ranked_indices:
        if len(output) >= top_k:
            break

        # Metadata filter (nurse qtype restriction)
        if allowed_qtypes is not None:
            qtype = metadatas[idx].get("qtype", "")
            if qtype not in allowed_qtypes:
                continue

        output.append(
            {
                "id": ids[idx],
                "text": texts[idx],
                "metadata": metadatas[idx],
                "score": float(scores[idx]),
            }
        )

    return output
