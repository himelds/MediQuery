"""Run baseline RAG on full eval set, save predictions for RAGAS evaluation."""
import json
import time
from pathlib import Path
from tqdm import tqdm
from src.rag.baseline_rag import BaselineRAG

LIMIT = 3

def main():
    eval_set = json.loads(Path("data/eval/eval_set.json").read_text())
    
    if LIMIT is not None:
        eval_set = eval_set[:LIMIT]
        print(f"SMOKE TEST MODE — running on {LIMIT} samples only\n")
    
    rag = BaselineRAG()
    predictions = []
    output_path = Path("data/eval/predictions_baseline.json")
    
    for item in tqdm(eval_set, desc="Generating"):
        try:
            result = rag.query(item["question"])
            
            # contexts MUST be list of strings for RAGAS
            contexts = result["retrieved_docs"]
            if contexts and isinstance(contexts[0], dict):
                contexts = [doc.get("text", str(doc)) for doc in contexts]
            
            predictions.append({
                "question": item["question"],
                "ground_truth": item["answer"],
                "answer": result["answer"],
                "contexts": contexts,
                # Optional metadata — for failure analysis
                "qtype": item.get("qtype"),
                "focus": item.get("focus"),
            })
            
            # save after every prediction — crash safety
            output_path.write_text(json.dumps(predictions, indent=2))
            time.sleep(0.5)
            
        except Exception as e:
            print(f"\n✗ Failed: {item['question'][:60]}... → {e}")
            time.sleep(5)
    
    print(f"\n✓ Saved {len(predictions)} predictions to {output_path}")

if __name__ == "__main__":
    main()