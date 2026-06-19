FROM python:3.11-slim

WORKDIR /app

# System deps (pdfplumber needs these for some PDFs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first (avoids huge CUDA download)
RUN pip install --no-cache-dir torch==2.12.0 --index-url https://download.pytorch.org/whl/cpu

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/

# Copy pre-built indices (ChromaDB + BM25)
COPY data/chroma_db/ ./data/chroma_db/
COPY data/bm25_index/ ./data/bm25_index/
COPY data/medical/corpus.json ./data/medical/corpus.json

# Pre-download embedding + reranker models into the image
# (avoids download on first request)
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
    SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); \
    CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

EXPOSE 8000

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
