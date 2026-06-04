"""Run RAGAS evaluation on saved predictions."""
import json
import os
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

# Cache MUST be set before any LLM import
from langchain.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

Path("data/cache").mkdir(parents=True, exist_ok=True)
set_llm_cache(SQLiteCache(database_path="data/cache/ragas_judge_cache.db"))

import numpy as np
from datasets import Dataset
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from ragas import evaluate
from ragas.run_config import RunConfig
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

load_dotenv()

# Judge LLM with longer timeout
JUDGE_MODEL = "openrouter/owl-alpha"

judge_llm = ChatOpenAI(
    model=JUDGE_MODEL,
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    openai_api_base="https://openrouter.ai/api/v1",
    temperature=0,
    max_retries=5,
    request_timeout=300,  # 5 min — free tier slow
)

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

ragas_llm = LangchainLLMWrapper(judge_llm)
ragas_emb = LangchainEmbeddingsWrapper(embeddings)

# Reduce concurrency — free tier overload এড়াতে
run_config = RunConfig(
    timeout=300,
    max_workers=2,    # default 16 থেকে কমিয়ে
    max_retries=5,
)

predictions = json.loads(
    Path("data/eval/predictions_baseline.json").read_text(encoding="utf-8")
)
dataset = Dataset.from_list(predictions)
print(f"Evaluating {len(predictions)} samples with {JUDGE_MODEL}...")
print(f"Using max_workers=2, timeout=300s (free tier safe)\n")

result = evaluate(
    dataset=dataset,
    metrics=[
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    ],
    llm=ragas_llm,
    embeddings=ragas_emb,
    raise_exceptions=False,
    run_config=run_config,
)

# Safe score extraction — handle both float and list/NaN cases
def safe_mean(value):
    if isinstance(value, (list, tuple, np.ndarray)):
        arr = np.array([x for x in value if x is not None], dtype=float)
        if len(arr) == 0 or np.all(np.isnan(arr)):
            return float('nan')
        return float(np.nanmean(arr))
    return float(value)

scores = {
    "pipeline_version": "baseline",
    "evaluated_on": str(date.today()),
    "n_samples": len(predictions),
    "judge_model": JUDGE_MODEL,
    "faithfulness": safe_mean(result["faithfulness"]),
    "answer_relevancy": safe_mean(result["answer_relevancy"]),
    "context_precision": safe_mean(result["context_precision"]),
    "context_recall": safe_mean(result["context_recall"]),
}

Path("data/eval/baseline_scores.json").write_text(
    json.dumps(scores, indent=2)
)
result.to_pandas().to_csv(
    "data/eval/baseline_per_sample.csv", index=False
)

print("=== Baseline Scores (smoke test, 3 samples) ===")
for k, v in scores.items():
    if isinstance(v, float):
        print(f"  {k:25s}: {v:.3f}")
    else:
        print(f"  {k:25s}: {v}")