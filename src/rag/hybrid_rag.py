"""
Phase 3 — Hybrid RAG Pipeline
-------------------------------
Hybrid retrieval: BM25 (lexical) + semantic (dense) fused via Reciprocal Rank Fusion.

Rationale:
  - Semantic (all-MiniLM-L6-v2 + ChromaDB) handles paraphrasing, synonyms.
  - BM25 handles rare medical terms (drug names, disease names, codes).
  - RRF combines without score-scale normalization or weight tuning.

Strategy:
  - Each retriever pulls TOP_K_PER_RETRIEVER candidates.
  - RRF (k=60) fuses the two ranked lists.
  - Top TOP_K_FINAL passed to generator (reused from baseline).

Run:
    python -m src.rag.hybrid_rag

First run builds BM25 index from corpus (~1-2 min CPU, one-time).
After that, both ChromaDB and BM25 load instantly from disk.

Ablation note:
  Generator, prompt, eval set, and judge identical to baseline.
  Only the retrieval stage changes — clean comparison vs baseline scores.
"""

import json
import pickle
import re
from pathlib import Path

import chromadb
from rank_bm25 import BM25Okapi
from tqdm import tqdm

from src.rag.baseline_rag import (
    CHROMA_DIR,
    CORPUS_PATH,
    embedding_fn,  # noqa: F401  (imported for parity / future reuse)
    generate,
    get_collection,
)

# Config
BM25_INDEX_PATH = Path("data/bm25/bm25_index.pkl")
TOP_K_PER_RETRIEVER = 20  # candidate pool size per retriever before fusion
TOP_K_FINAL = 5  # final contexts passed to generator (matches baseline TOP_K)
RRF_K = 60  # RRF damping constant (Cormack et al. 2009, standard default)

# Minimal English stopword set — kept short on purpose to preserve medical terms.
# No stemming: "diabetic" vs "diabetes" distinction matters for retrieval signal.
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "he",
    "her",
    "him",
    "his",
    "i",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "she",
    "such",
    "that",
    "the",
    "their",
    "then",
    "there",
    "these",
    "they",
    "this",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "will",
    "with",
    "you",
    "your",
}


# Tokenization


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, split on whitespace, drop stopwords.

    Used both for BM25 indexing (corpus answers) and querying (user questions).
    Critical: same tokenizer in both places, otherwise vocabulary mismatch.
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return [t for t in text.split() if t and t not in STOPWORDS]


# BM25 index — build + load


def _build_bm25_index() -> tuple[BM25Okapi, list[dict]]:
    """Build BM25 index from corpus.json (one-time, ~1-2 min CPU)."""
    print("Building BM25 index from corpus...")
    corpus = json.load(open(CORPUS_PATH, encoding="utf-8"))
    print(f"{len(corpus)} documents found.")

    # Tokenize answer text only — same content ChromaDB embedded.
    # This keeps the ablation clean: retrieval method changes, corpus does not.
    tokenized = [_tokenize(doc["answer"]) for doc in tqdm(corpus, desc="Tokenizing")]
    bm25 = BM25Okapi(tokenized)

    # Persist BM25 + corpus together — both needed at retrieval time
    # (BM25 returns indices into corpus; corpus provides text + metadata).
    BM25_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BM25_INDEX_PATH, "wb") as f:
        pickle.dump({"bm25": bm25, "corpus": corpus}, f)

    print(f"\nBM25 index built and saved to {BM25_INDEX_PATH}")
    return bm25, corpus


def get_bm25() -> tuple[BM25Okapi, list[dict]]:
    """Load BM25 index from disk if present, else build from scratch."""
    if BM25_INDEX_PATH.exists():
        print(f"Loading BM25 index from {BM25_INDEX_PATH}...")
        with open(BM25_INDEX_PATH, "rb") as f:
            data = pickle.load(f)
        print(f"BM25 index loaded — {len(data['corpus'])} documents ready.")
        return data["bm25"], data["corpus"]
    return _build_bm25_index()


def get_collection_and_bm25():
    """Load both ChromaDB collection and BM25 index. Single entry point."""
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = get_collection(chroma_client)
    bm25, corpus = get_bm25()
    return collection, bm25, corpus


# Retrievers (internal)


def _semantic_retrieve(collection, query: str, k: int) -> list[tuple[int, str, dict]]:
    """ChromaDB semantic search. Returns list of (corpus_idx, doc, meta).

    corpus_idx is parsed from ChromaDB's doc_id (e.g. "doc_42" → 42).
    This int index serves as the cross-retriever ID for RRF fusion.
    """
    results = collection.query(query_texts=[query], n_results=k)

    output = []
    for doc_id, doc, meta in zip(
        results["ids"][0], results["documents"][0], results["metadatas"][0]
    ):
        corpus_idx = int(doc_id.split("_")[1])
        output.append((corpus_idx, doc, meta))
    return output


def _bm25_retrieve(
    bm25: BM25Okapi, corpus: list[dict], query: str, k: int
) -> list[tuple[int, str, dict]]:
    """BM25 lexical search. Returns list of (corpus_idx, doc, meta).

    Reconstructs metadata to exactly match baseline's structure so generate()
    works unchanged.
    """
    tokens = _tokenize(query)
    if not tokens:
        return []

    scores = bm25.get_scores(tokens)
    top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]

    output = []
    for idx in top_idx:
        doc = corpus[idx]
        meta = {
            "question": doc["question"],
            "focus": doc["focus"],
            "qtype": doc["qtype"],
            "source": doc["source"],
            "source_url": doc["source_url"],
        }
        output.append((idx, doc["answer"], meta))
    return output


# Fusion


def _reciprocal_rank_fusion(
    semantic_results: list[tuple[int, str, dict]],
    bm25_results: list[tuple[int, str, dict]],
    k_rrf: int = RRF_K,
) -> list[tuple[int, str, dict]]:
    """Combine two ranked lists via RRF: score(d) = Σ 1 / (k_rrf + rank_in_list).

    Documents in both lists accumulate scores from both → rank higher.
    No score normalization needed; rank is the only signal.

    Reference: Cormack, Clarke, Buettcher 2009.
    """
    scores: dict[int, float] = {}
    data: dict[int, tuple[str, dict]] = {}

    for rank, (idx, doc, meta) in enumerate(semantic_results, start=1):
        scores[idx] = scores.get(idx, 0.0) + 1.0 / (k_rrf + rank)
        data[idx] = (doc, meta)

    for rank, (idx, doc, meta) in enumerate(bm25_results, start=1):
        scores[idx] = scores.get(idx, 0.0) + 1.0 / (k_rrf + rank)
        data[idx] = (doc, meta)

    sorted_idx = sorted(scores.keys(), key=lambda i: scores[i], reverse=True)
    return [(idx, data[idx][0], data[idx][1]) for idx in sorted_idx]


# Public retrieve — drop-in replacement for baseline.retrieve()


def retrieve(
    collection,
    bm25: BM25Okapi,
    corpus: list[dict],
    query: str,
    top_k: int = TOP_K_FINAL,
) -> tuple[list[str], list[dict]]:
    """Hybrid retrieval: BM25 + semantic fused via RRF.

    Pulls TOP_K_PER_RETRIEVER candidates from each, applies RRF, returns top_k.
    Output format identical to baseline.retrieve() → generate() works unchanged.
    """
    semantic = _semantic_retrieve(collection, query, TOP_K_PER_RETRIEVER)
    bm25_res = _bm25_retrieve(bm25, corpus, query, TOP_K_PER_RETRIEVER)
    fused = _reciprocal_rank_fusion(semantic, bm25_res)[:top_k]

    docs = [doc for _, doc, _ in fused]
    metas = [meta for _, _, meta in fused]
    return docs, metas


# Full pipeline


def ask(collection, bm25: BM25Okapi, corpus: list[dict], query: str) -> str:
    """End-to-end hybrid: question → retrieve → generate → print."""
    print(f"\n{'=' * 65}")
    print(f"Question: {query}")
    print(f"{'=' * 65}")

    docs, metas = retrieve(collection, bm25, corpus, query)

    print("\nRetrieved sources (after RRF fusion):")
    for i, meta in enumerate(metas, start=1):
        print(f"  {i}. {meta['focus']}  [{meta['source']}]  ({meta['qtype']})")

    answer = generate(query, docs, metas)
    print(f"\nAnswer:\n{answer}\n")
    return answer


# Main — smoke test


def main():
    collection, bm25, corpus = get_collection_and_bm25()

    # Three smoke-test queries chosen for diagnostic value:
    #   1. Generic disease (semantic-friendly, paraphrasable)
    #   2. Rare specific term (BM25-friendly, exact match needed)
    #   3. Mixed signal (both retrievers contribute)
    test_questions = [
        "What is polycystic kidney disease?",
        "What are the symptoms of Fabry disease?",
        "How is type 2 diabetes diagnosed?",
    ]

    for question in test_questions:
        ask(collection, bm25, corpus, question)


if __name__ == "__main__":
    main()
