"""
Hybrid retrieval — Reciprocal Rank Fusion (RRF).

Merges semantic (dense) and BM25 (sparse) ranked lists into a single
ranking using RRF: score(d) = Σ 1/(k + rank).

No score calibration needed — only rank positions matter.
Reference: Cormack, Clarke, Buettcher (2009).
"""

from backend.config import RRF_K, TOP_K

from .bm25 import bm25_search
from .semantic import semantic_search


def _reciprocal_rank_fusion(
    semantic_results: list[dict],
    bm25_results: list[dict],
    k: int = RRF_K,
) -> list[dict]:
    """
    Fuse two ranked lists via RRF.

    Documents appearing in both lists accumulate scores from both,
    naturally ranking higher. The k parameter (default 60) controls
    how much lower ranks are dampened.

    Args:
        semantic_results:  Ranked list from semantic search.
        bm25_results:      Ranked list from BM25 search.
        k:                 RRF damping constant.

    Returns:
        Merged list sorted by RRF score (descending).
    """
    rrf_scores: dict[str, float] = {}
    doc_data: dict[str, dict] = {}

    for rank, result in enumerate(semantic_results, start=1):
        doc_id = result["id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank)
        doc_data[doc_id] = result

    for rank, result in enumerate(bm25_results, start=1):
        doc_id = result["id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank)
        doc_data[doc_id] = result

    sorted_ids = sorted(rrf_scores, key=lambda d: rrf_scores[d], reverse=True)

    return [{**doc_data[doc_id], "score": rrf_scores[doc_id]} for doc_id in sorted_ids]


def hybrid_search(
    query: str,
    collection_name: str,
    top_k: int = TOP_K,
    where_filter: dict | None = None,
    allowed_qtypes: list[str] | None = None,
) -> list[dict]:
    """
    Hybrid retrieval: semantic + BM25, fused via RRF.

    Args:
        query:            User question.
        collection_name:  Collection to search.
        top_k:            Candidates per retriever (both pull this many).
        where_filter:     ChromaDB metadata filter (passed to semantic).
        allowed_qtypes:   BM25 qtype filter (passed to bm25).

    Returns:
        Fused ranked list (all candidates from both retrievers, merged).
    """
    semantic_results = semantic_search(
        query=query,
        collection_name=collection_name,
        top_k=top_k,
        where_filter=where_filter,
    )

    bm25_results = bm25_search(
        query=query,
        collection_name=collection_name,
        top_k=top_k,
        allowed_qtypes=allowed_qtypes,
    )

    return _reciprocal_rank_fusion(semantic_results, bm25_results)
