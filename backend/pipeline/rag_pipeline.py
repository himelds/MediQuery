"""
RAG Pipeline Orchestrator
--------------------------

Connects all components: role filtering → hybrid retrieval →
reranking → generation.

This is the single entry point that the API layer calls.
Role-based access control happens HERE — before any retrieval,
the pipeline determines which collections and metadata filters
apply for the given role.
"""

from backend.auth.roles import get_allowed_collections, get_filters_for_role
from backend.config import RERANK_TOP_K, TOP_K
from backend.generation.generator import generate
from backend.retrieval.hybrid import hybrid_search
from backend.retrieval.reranker import rerank


def ask(query: str, role: str) -> dict:
    """
    Full RAG pipeline: role filter → retrieve → rerank → generate.

    Args:
        query:  User question.
        role:   User role (doctor, nurse, billing_executive, technician, admin).

    Returns:
        Dict with keys:
            - answer:    Generated text from LLM.
            - sources:   List of source documents used (top-k after reranking).
            - role:      Echo of the user's role.
            - collections_searched:  Which collections were queried.
    """
    # 1. Determine allowed collections
    allowed = get_allowed_collections(role)
    if allowed is None:
        return {
            "answer": f"Unknown role: {role}",
            "sources": [],
            "role": role,
            "collections_searched": [],
        }

    # 2. Retrieve from all allowed collections
    all_candidates = []

    for collection_name in allowed:
        where_filter, allowed_qtypes = get_filters_for_role(role, collection_name)

        results = hybrid_search(
            query=query,
            collection_name=collection_name,
            top_k=TOP_K,
            where_filter=where_filter,
            allowed_qtypes=allowed_qtypes,
        )

        # Tag each result with its source collection
        for r in results:
            r["collection"] = collection_name

        all_candidates.extend(results)

    # 3. Rerank all candidates together
    per_collection_top = []
    from itertools import groupby

    all_candidates.sort(key=lambda x: x.get("collection", ""))
    for _, group in groupby(all_candidates, key=lambda x: x.get("collection", "")):
        group_list = sorted(list(group), key=lambda x: x.get("score", 0), reverse=True)
        per_collection_top.extend(group_list[:5])

    reranked = rerank(query, per_collection_top, top_k=RERANK_TOP_K)

    # 4. Generate answer
    answer = generate(query, reranked, role=role)

    # 5. Build source list for response
    sources = [
        {
            "id": doc["id"],
            "collection": doc.get("collection", ""),
            "text": doc["text"][:300],
            "metadata": doc["metadata"],
            "rerank_score": doc.get("rerank_score", 0.0),
        }
        for doc in reranked
    ]

    return {
        "answer": answer,
        "sources": sources,
        "role": role,
        "collections_searched": allowed,
    }
