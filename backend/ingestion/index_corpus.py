"""
MedRagAssistant - Collection Indexer
------------------------------------

Builds ChromaDB + BM25 indices for all 6 collections.

  - medical:   corpus.json (MedQuAD, pre-parsed)
  - clinical, nursing, billing, equipment, general:  PDFs + markdown files

Input:
    data/medical/corpus.json
    data/{clinical,nursing,billing,equipment,general}/*.pdf, *.md

Outputs:
    data/chroma_db/             (ChromaDB persistent store, 6 collections)
    data/bm25_index/{name}.pkl  (BM25 model + parallel ids/metadatas/texts)

Usage (from project root):
    python -m backend.ingestion.index_corpus                  # all collections
    python -m backend.ingestion.index_corpus --only medical   # single collection
    python -m backend.ingestion.index_corpus --force           # rebuild existing
    python -m backend.ingestion.index_corpus --skip-sanity
"""

import argparse
import json
import pickle
import re
import sys
from collections import Counter
from pathlib import Path

import chromadb
import numpy as np
import pdfplumber
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Make `backend.config` importable when run as a script.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import (  # noqa: E402
    BM25_DIR,
    CHROMA_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTIONS,
    EMBEDDING_MODEL,
    MEDICAL_DIR,
)

# --- Constants ---
EMBEDDING_BATCH_SIZE = 64
CHROMA_ADD_BATCH_SIZE = 5000
SANITY_QUERIES = {
    "medical": "What are the symptoms of diabetes?",
    "clinical": "treatment protocol",
    "nursing": "infection control procedures",
    "billing": "ICD-10 code",
    "equipment": "ventilator calibration",
    "general": "leave policy",
}
SANITY_TOP_K = 3


# =====================================================================
#  Shared utilities
# =====================================================================


def tokenize(text: str) -> list[str]:
    """BM25 tokenizer: lowercase + alphanumeric word splits."""
    return re.findall(r"\w+", text.lower())


def check_id_uniqueness(ids: list[str], collection_name: str) -> None:
    """Fail fast if duplicate IDs exist — saves expensive re-embedding."""
    counts = Counter(ids)
    duplicates = [doc_id for doc_id, count in counts.items() if count > 1]
    if duplicates:
        print(f"[ERROR] {collection_name}: {len(duplicates)} duplicate IDs found.")
        print(f"        First 5: {duplicates[:5]}")
        print("        Fix source data before re-running.")
        sys.exit(1)
    print(f"  ID uniqueness check passed: {len(ids):,} unique IDs")


def collection_exists(client, name: str) -> bool:
    """Check if a ChromaDB collection exists."""
    try:
        client.get_collection(name=name)
        return True
    except Exception:
        return False


# =====================================================================
#  Medical collection (JSON corpus)
# =====================================================================


def load_medical_corpus(corpus_path: Path) -> tuple[list[str], list[str], list[dict]]:
    """
    Load MedQuAD corpus.json into parallel arrays.

    Returns:
        ids, texts (answer field), metadatas
    """
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    ids = []
    texts = []
    metadatas = []

    for record in corpus:
        ids.append(record["id"])
        texts.append(record["answer"])
        metadatas.append(
            {
                "qtype": record.get("qtype", ""),
                "focus": record.get("focus", ""),
                "source": record.get("source", ""),
                "source_url": record.get("source_url", ""),
                "question": record.get("question", ""),
            }
        )

    return ids, texts, metadatas


# =====================================================================
#  Document collections (PDF + Markdown)
# =====================================================================


def extract_text_from_pdf(pdf_path: Path) -> list[tuple[str, int]]:
    """
    Extract text from a PDF file, one entry per page.

    Returns:
        List of (page_text, page_number) tuples.
        Empty pages are skipped.
    """
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text and text.strip():
                pages.append((text.strip(), i))
    return pages


def extract_text_from_markdown(md_path: Path) -> list[tuple[str, int]]:
    """
    Read a markdown file as a single page.

    Returns:
        List with one (full_text, page_number=1) tuple.
    """
    text = md_path.read_text(encoding="utf-8").strip()
    if text:
        return [(text, 1)]
    return []


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Split text into overlapping chunks by character count.

    Splits on sentence boundaries ('. ') when possible,
    falls back to word boundaries, then hard character split.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end >= len(text):
            chunks.append(text[start:].strip())
            break

        # Try to break at sentence boundary
        boundary = text.rfind(". ", start, end)
        if boundary > start:
            end = boundary + 1  # include the period
        else:
            # Fall back to word boundary
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        new_start = end - overlap
        if new_start <= start:
            new_start = end
        start = new_start

    return chunks


def load_document_collection(
    collection_name: str,
    folder_path: Path,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[list[str], list[str], list[dict]]:
    """
    Load all PDF and markdown files from a folder,
    extract text, chunk, and build parallel arrays.

    Returns:
        ids, texts, metadatas
    """
    ids = []
    texts = []
    metadatas = []

    if not folder_path.exists():
        print(f"  [WARN] Folder not found: {folder_path}")
        return ids, texts, metadatas

    # Gather all supported files
    files = sorted(list(folder_path.glob("*.pdf")) + list(folder_path.glob("*.md")))

    if not files:
        print(f"  [WARN] No PDF/MD files found in: {folder_path}")
        return ids, texts, metadatas

    chunk_counter = 0

    for file_path in files:
        # Extract raw pages
        if file_path.suffix.lower() == ".pdf":
            pages = extract_text_from_pdf(file_path)
        elif file_path.suffix.lower() == ".md":
            pages = extract_text_from_markdown(file_path)
        else:
            continue

        if not pages:
            print(f"  [SKIP] Empty file: {file_path.name}")
            continue

        # Chunk each page
        for page_text, page_num in pages:
            page_chunks = chunk_text(page_text, chunk_size, chunk_overlap)

            for chunk_idx, chunk in enumerate(page_chunks):
                chunk_counter += 1
                doc_id = f"{collection_name}_{file_path.stem}_p{page_num}_c{chunk_idx}"

                ids.append(doc_id)
                texts.append(chunk)
                metadatas.append(
                    {
                        "source": file_path.name,
                        "collection": collection_name,
                        "page": str(page_num),
                        "chunk_index": str(chunk_idx),
                    }
                )

        print(f"  Processed: {file_path.name} ({len(pages)} pages)")

    print(f"  Total chunks: {chunk_counter}")
    return ids, texts, metadatas


# =====================================================================
#  Indexing (shared for all collections)
# =====================================================================


def index_to_chroma(
    client,
    name: str,
    ids: list[str],
    texts: list[str],
    metadatas: list[dict],
    embedder: SentenceTransformer,
    force: bool,
):
    """Embed texts and store in a ChromaDB collection."""
    if collection_exists(client, name):
        if not force:
            print(f"  Collection '{name}' already exists. Use --force to rebuild.")
            return client.get_collection(name=name)
        client.delete_collection(name=name)
        print(f"  Deleted existing collection: {name}")

    collection = client.create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )

    print(f"  Embedding {len(texts):,} documents (batch={EMBEDDING_BATCH_SIZE})...")
    embeddings = embedder.encode(
        texts,
        batch_size=EMBEDDING_BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
    ).tolist()

    total_batches = (len(ids) + CHROMA_ADD_BATCH_SIZE - 1) // CHROMA_ADD_BATCH_SIZE
    for batch_idx in tqdm(range(total_batches), desc="  Chroma add"):
        start = batch_idx * CHROMA_ADD_BATCH_SIZE
        end = min(start + CHROMA_ADD_BATCH_SIZE, len(ids))
        collection.add(
            ids=ids[start:end],
            embeddings=embeddings[start:end],
            documents=texts[start:end],
            metadatas=metadatas[start:end],
        )

    print(f"  ChromaDB '{name}': {collection.count():,} documents indexed")
    return collection


def build_bm25_index(
    texts: list[str],
    ids: list[str],
    metadatas: list[dict],
    output_path: Path,
) -> dict:
    """Build BM25 index and pickle alongside parallel arrays."""
    print(f"  Tokenizing {len(texts):,} documents...")
    tokenized_corpus = [tokenize(t) for t in texts]

    bm25 = BM25Okapi(tokenized_corpus)

    payload = {
        "bm25": bm25,
        "ids": ids,
        "metadatas": metadatas,
        "texts": texts,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        pickle.dump(payload, f)

    print(f"  BM25 saved: {output_path.name} ({len(ids):,} documents)")
    return payload


# =====================================================================
#  Sanity check
# =====================================================================


def sanity_check(
    collection,
    bm25_payload: dict,
    embedder: SentenceTransformer,
    query: str,
    collection_name: str,
    top_k: int,
) -> None:
    """Run a sample query against both indices."""
    actual_count = collection.count()
    k = min(top_k, actual_count)
    if k == 0:
        print(f"  [SKIP] {collection_name} is empty, nothing to query.")
        return

    print(f"\n  Sanity check [{collection_name}]: '{query}'")

    # Semantic
    print("  [Semantic]")
    query_emb = embedder.encode([query], convert_to_numpy=True).tolist()
    results = collection.query(query_embeddings=query_emb, n_results=k)
    for rank, (doc_id, dist) in enumerate(
        zip(results["ids"][0], results["distances"][0]), start=1
    ):
        print(f"    {rank}. [{doc_id}] dist={dist:.4f}")

    # BM25
    print("  [BM25]")
    scores = bm25_payload["bm25"].get_scores(tokenize(query))
    top_indices = np.argsort(scores)[::-1][:k]
    for rank, idx in enumerate(top_indices, start=1):
        print(f"    {rank}. [{bm25_payload['ids'][idx]}] score={scores[idx]:.4f}")


# =====================================================================
#  Main
# =====================================================================


def index_single_collection(
    name: str,
    chroma_client,
    embedder: SentenceTransformer,
    force: bool,
    skip_sanity: bool,
) -> None:
    """Index one collection end-to-end (load → embed → ChromaDB → BM25)."""
    print(f"\n{'=' * 60}")
    print(f"  Collection: {name}")
    print(f"{'=' * 60}")

    # Load data
    if name == "medical":
        corpus_path = MEDICAL_DIR / "corpus.json"
        if not corpus_path.exists():
            print(f"  [ERROR] corpus.json not found: {corpus_path}")
            print("  Run parse_medquad.py first.")
            return
        ids, texts, metadatas = load_medical_corpus(corpus_path)
    else:
        folder_path = COLLECTIONS[name]
        ids, texts, metadatas = load_document_collection(
            name, folder_path, CHUNK_SIZE, CHUNK_OVERLAP
        )

    if not ids:
        print(f"  [SKIP] No documents found for '{name}'.")
        return

    # Validate
    check_id_uniqueness(ids, name)

    # ChromaDB
    collection = index_to_chroma(
        chroma_client, name, ids, texts, metadatas, embedder, force
    )

    # BM25
    bm25_path = BM25_DIR / f"{name}.pkl"
    bm25_payload = build_bm25_index(texts, ids, metadatas, bm25_path)

    # Sanity check
    if not skip_sanity and name in SANITY_QUERIES:
        sanity_check(
            collection, bm25_payload, embedder, SANITY_QUERIES[name], name, SANITY_TOP_K
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Index collections into ChromaDB + BM25."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing collections and rebuild.",
    )
    parser.add_argument(
        "--skip-sanity",
        action="store_true",
        help="Skip post-indexing sanity check queries.",
    )
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        choices=list(COLLECTIONS.keys()),
        help="Index only this collection (default: all).",
    )
    args = parser.parse_args()

    # Directories
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    BM25_DIR.mkdir(parents=True, exist_ok=True)

    # Embedding model (load once, reuse for all collections)
    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    embedder = SentenceTransformer(EMBEDDING_MODEL)

    # ChromaDB client
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Which collections to index
    if args.only:
        targets = [args.only]
    else:
        targets = list(COLLECTIONS.keys())

    for name in targets:
        index_single_collection(
            name, chroma_client, embedder, args.force, args.skip_sanity
        )

    print(f"\n{'=' * 60}")
    print("[DONE] All requested collections indexed.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
