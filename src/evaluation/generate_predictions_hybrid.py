"""Run hybrid RAG on eval set, save predictions for RAGAS evaluation."""

import json
import time
from pathlib import Path
from tqdm import tqdm

from src.rag.hybrid_rag import (
    get_collection_and_bm25,
    retrieve,
    generate,
)

# Smoke test mode
LIMIT = None


def main():
    eval_set = json.loads(Path("data/eval/eval_set.json").read_text(encoding="utf-8"))

    if LIMIT is not None:
        eval_set = eval_set[:LIMIT]
        print(f"SMOKE TEST MODE: {LIMIT} samples\n")

    # Initialize retrieval indices (ChromaDB + BM25)
    print("Loading retrieval indices...")
    collection, bm25, corpus = get_collection_and_bm25()
    print()

    predictions = []
    output_path = Path("data/eval/predictions_hybrid.json")

    for item in tqdm(eval_set, desc="Generating"):
        try:
            # Hybrid retrieve: BM25 + semantic fused via RRF
            docs, metas = retrieve(collection, bm25, corpus, item["question"])

            # Generate answer (same generator as baseline — ablation invariant)
            answer = generate(item["question"], docs, metas)

            predictions.append(
                {
                    "question": item["question"],
                    "ground_truth": item["answer"],
                    "answer": answer,
                    "contexts": docs,  # already list of strings ✓
                    "qtype": item.get("qtype"),
                    "focus": item.get("focus"),
                }
            )

            # Save after each — crash safety
            output_path.write_text(json.dumps(predictions, indent=2, ensure_ascii=False))
            time.sleep(0.5)

        except Exception as e:
            print(f"\nFailed: {item['question'][:60]}... -> {e}")
            time.sleep(5)

    print(f"\nSaved {len(predictions)} predictions to {output_path}")


if __name__ == "__main__":
    main()
