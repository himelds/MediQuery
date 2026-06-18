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


def _check_query_scope(query: str) -> dict:
    """
    Layer 1: Detect if the query is related to medical/hospital domain.
    Uses Groq for fast classification.
    """
    try:
        import os
        from groq import Groq

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a query classifier for a hospital information system. "
                        "The system covers: medical diseases, symptoms, treatments, "
                        "clinical protocols, billing/insurance codes, equipment manuals, "
                        "nursing procedures, and hospital policies.\n\n"
                        "Classify the query as IN_SCOPE or OUT_OF_SCOPE.\n"
                        "Reply with ONLY 'IN_SCOPE' or 'OUT_OF_SCOPE'."
                    ),
                },
                {"role": "user", "content": query},
            ],
            temperature=0,
            max_tokens=10,
        )
        result = response.choices[0].message.content.strip().upper()

        if "OUT" in result:
            return {
                "in_scope": False,
                "message": (
                    "🏥 I'm a medical information assistant and can only answer "
                    "questions related to medical conditions, hospital procedures, "
                    "billing codes, equipment, and hospital policies.\n\n"
                    "Please ask a relevant question, for example:\n"
                    '• "What are the symptoms of diabetes?"\n'
                    '• "What is the ICD-10 code for pneumonia?"\n'
                    '• "What is the leave policy?"'
                ),
            }
    except Exception:
        pass

    return {"in_scope": True, "message": ""}


def _detect_query_department(query: str) -> list[str]:
    """
    Layer 2: Predict which collection(s) are most relevant to the query.
    Returns empty list if unsure (falls back to searching all allowed).
    """
    try:
        import os
        from groq import Groq

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You route hospital queries to the right department. "
                        "Available departments:\n"
                        "- medical: diseases, symptoms, treatments, diagnosis\n"
                        "- clinical: drug dosing, treatment protocols, lab values\n"
                        "- billing: ICD-10 codes, insurance claims, billing policies\n"
                        "- equipment: medical equipment operation, maintenance\n"
                        "- nursing: ICU procedures, infection control, nursing SOPs\n"
                        "- general: leave policy, code of conduct, HR, staff handbook\n\n"
                        "Reply with ONLY the department name(s), comma-separated. "
                        "If unsure, reply 'all'."
                    ),
                },
                {"role": "user", "content": query},
            ],
            temperature=0,
            max_tokens=30,
        )
        result = response.choices[0].message.content.strip().lower()

        if "all" in result:
            return []

        valid = {"medical", "clinical", "billing", "equipment", "nursing", "general"}
        departments = [d.strip() for d in result.split(",") if d.strip() in valid]
        return departments
    except Exception:
        return []


def _assess_confidence(reranked: list[dict]) -> dict:
    if not reranked:
        return {"level": "low", "top_score": 0}

    top_score = reranked[0].get("rerank_score", 0)

    if top_score > 3:
        return {"level": "high", "top_score": top_score}
    elif top_score > -12:
        return {"level": "medium", "top_score": top_score}
    else:
        return {"level": "low", "top_score": top_score}


def ask(query: str, role: str, history: list[dict] = None) -> dict:
    if history is None:
        history = []

    allowed = get_allowed_collections(role)
    if not allowed:
        return {
            "answer": f"Unknown role: {role}",
            "sources": [],
            "role": role,
            "collections_searched": [],
        }

    # --- Layer 1: Out-of-scope detection ---
    scope_check = _check_query_scope(query)
    if not scope_check["in_scope"]:
        return {
            "answer": scope_check["message"],
            "sources": [],
            "role": role,
            "collections_searched": [],
        }

    # Resolve follow-up queries
    search_query = _resolve_query(query, history)

    # --- Layer 2: Department routing ---
    suggested_collections = _detect_query_department(search_query)
    accessible = [c for c in suggested_collections if c in allowed]

    if suggested_collections and not accessible:
        denied_deps = ", ".join(suggested_collections)
        allowed_deps = ", ".join(allowed)
        return {
            "answer": (
                f"⛔ This question relates to **{denied_deps}** collection(s), "
                f"which your **{role}** role cannot access.\n\n"
                f"💡 Please contact the relevant department or log in with an authorized role.\n\n"
                f"📋 With your current role, you can ask about: **{allowed_deps}**."
            ),
            "sources": [],
            "role": role,
            "collections_searched": [],
        }

    search_collections = allowed

    # Retrieve from relevant collections
    all_candidates = []

    for collection_name in search_collections:
        where_filter, allowed_qtypes = get_filters_for_role(role, collection_name)

        results = hybrid_search(
            query=search_query,
            collection_name=collection_name,
            top_k=TOP_K,
            where_filter=where_filter,
            allowed_qtypes=allowed_qtypes,
        )

        for r in results:
            r["collection"] = collection_name

        all_candidates.extend(results)

    # Rerank
    all_candidates.sort(key=lambda x: x.get("score", 0), reverse=True)

    from collections import defaultdict

    by_collection = defaultdict(list)
    for cand in all_candidates:
        by_collection[cand.get("collection", "")].append(cand)

    top_candidates = []
    seen_texts = set()
    for coll, cands in by_collection.items():
        cands.sort(key=lambda x: x.get("score", 0), reverse=True)
        added = 0
        for cand in cands:
            text_key = cand["text"][:200]
            if text_key in seen_texts:
                continue
            seen_texts.add(text_key)
            top_candidates.append(cand)
            added += 1
            if added >= 8:  # top 8 per collection
                break

    reranked = rerank(search_query, top_candidates, top_k=RERANK_TOP_K)

    # --- Layer 3: Low confidence detection ---
    confidence = _assess_confidence(reranked)

    answer = generate(query, reranked, role=role, history=history)

    if confidence["level"] == "low":
        answer = (
            "⚠️ **Low confidence** — the retrieved sources may not be relevant "
            "to your question. Please rephrase or ask a more specific question.\n\n"
            + answer
        )

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
        "collections_searched": search_collections,
    }


def _resolve_query(query: str, history: list[dict]) -> str:
    """
    When conversation history exists, use LLM to rewrite the query
    as a standalone question. LLM decides if rewriting is needed.
    """
    if not history:
        return query

    recent = history[-4:]
    context_lines = []
    for msg in recent:
        role = "User" if msg["role"] == "user" else "Assistant"
        content = msg["content"][:150] if msg["role"] == "assistant" else msg["content"]
        context_lines.append(f"{role}: {content}")

    context = "\n".join(context_lines)

    try:
        import os
        from groq import Groq

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Given the conversation history and a new question, "
                        "rewrite the question as a fully standalone question "
                        "that includes all necessary context. "
                        "If the question is already standalone, return it unchanged. "
                        "Preserve the exact wording of medical terms, numbers, and type designations "
                        "(e.g. keep 'type 1' as 'type 1', never convert to 'type I'). "
                        "Do not add or change punctuation. "
                        "Reply with ONLY the rewritten question, nothing else."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Conversation:\n{context}\n\nNew question: {query}\n\nStandalone question:",
                },
            ],
            temperature=0,
            max_tokens=100,
        )
        resolved = response.choices[0].message.content.strip()
        print(f"[Query resolved] '{query}' -> '{resolved}'")
        return resolved
    except Exception as e:
        print(f"[Query resolution failed] {e}")
        return query
