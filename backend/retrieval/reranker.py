"""
Cross-encoder reranker — re-scores hybrid results for precision.

Takes the fused candidate list from hybrid retrieval (up to 40
documents) and re-scores each (query, document) pair using a
cross-encoder model. Returns the top-k most relevant.

Why two stages:
  - Hybrid retrieval is fast but approximate (bi-encoder, BM25).
  - Cross-encoder is slow but accurate — it reads query + document
    together, capturing fine-grained relevance that bi-encoders miss.
  - Running cross-encoder on 40 candidates is feasible (~100ms);
    running it on 16k documents is not.
"""

from sentence_transformers import CrossEncoder

from backend.config import RERANK_TOP_K, RERANKER_MODEL

_reranker: CrossEncoder | None = None


def _get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(RERANKER_MODEL)
    return _reranker


def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = RERANK_TOP_K,
) -> list[dict]:
    """
    Re-score candidates using a cross-encoder and return top-k.

    Args:
        query:       User question.
        candidates:  List of dicts from hybrid_search(), each with
                     at least 'text' key.
        top_k:       Number of results to return after reranking.

    Returns:
        Top-k candidates sorted by cross-encoder score (descending).
    """
    if not candidates:
        return []

    reranker = _get_reranker()

    # Cross-encoder takes (query, document) pairs
    pairs = [(query, c["text"]) for c in candidates]
    scores = reranker.predict(pairs)

    # Attach reranker scores and sort
    for candidate, score in zip(candidates, scores):
        candidate["rerank_score"] = float(score)

    ranked = sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)

    return ranked[:top_k]
