from pathlib import Path


# Project Paths

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

MEDICAL_DIR = DATA_DIR / "medical"
CLINICAL_DIR = DATA_DIR / "clinical"
NURSING_DIR = DATA_DIR / "nursing"
BILLING_DIR = DATA_DIR / "billing"
EQUIPMENT_DIR = DATA_DIR / "equipment"
GENERAL_DIR = DATA_DIR / "general"

CHROMA_DIR = DATA_DIR / "chroma_db"
BM25_DIR = DATA_DIR / "bm25_index"

# Collections

COLLECTIONS = {
    "medical": MEDICAL_DIR,
    "clinical": CLINICAL_DIR,
    "nursing": NURSING_DIR,
    "billing": BILLING_DIR,
    "equipment": EQUIPMENT_DIR,
    "general": GENERAL_DIR,
}


# Models

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


# Retrieval Settings

TOP_K = 20
RRF_K = 60
RERANK_TOP_K = 5

# Chunking (for PDF/markdown documents)
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

LLM_TEMPERATURE = 0.1

NURSE_ALLOWED_QTYPES = [
    "information",
    "symptoms",
    "prevention",
    "considerations",
    "frequency",
]
