"""
MediChat - MedQuAD Ingestion Script
----------------------------------

Parses all MedQuAD XML files and generates:

    data/medical/corpus.json

This corpus is later indexed into:
    - ChromaDB (semantic retrieval)
    - BM25 (keyword retrieval)

Usage:
    python backend/ingestion/ingest_medquad.py
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

# Configuration

MEDQUAD_DIR = Path("data/raw/MedQuAD")
OUTPUT_DIR = Path("data/medical")

MIN_ANSWER_LEN = 80


def parse_xml_file(xml_path: Path) -> list[dict]:
    """
    Parse a single MedQuAD XML file and return QA records.
    """

    records = []

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

    except ET.ParseError as e:
        print(f"[SKIP] {xml_path.name} | Parse Error: {e}")
        return records

    source = root.get("source", xml_path.parent.name)
    source_url = root.get("url", "")

    focus_element = root.find("Focus")
    focus = (
        focus_element.text.strip()
        if focus_element is not None and focus_element.text
        else ""
    )

    qa_pairs = root.find("QAPairs")

    if qa_pairs is None:
        return records

    for qa_pair in qa_pairs.findall("QAPair"):
        pid = qa_pair.get("pid", "")

        question_element = qa_pair.find("Question")
        answer_element = qa_pair.find("Answer")

        if question_element is None or answer_element is None:
            continue

        question = (question_element.text or "").strip()
        answer = (answer_element.text or "").strip()

        qtype = question_element.get("qtype", "")
        qid = question_element.get("qid", "")

        if not question:
            continue

        if len(answer) < MIN_ANSWER_LEN:
            continue

        records.append(
            {
                "id": f"{xml_path.parent.name}_{xml_path.stem}_{pid}",
                "qid": qid,
                "question": question,
                "answer": answer,
                "qtype": qtype,
                "focus": focus,
                "source": source,
                "source_url": source_url,
                "source_file": xml_path.name,
            }
        )

    return records


def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not MEDQUAD_DIR.exists():
        print(f"ERROR: MedQuAD directory not found:\n{MEDQUAD_DIR.resolve()}")
        return

    print("\nScanning MedQuAD Dataset")
    print(f"Location: {MEDQUAD_DIR.resolve()}\n")

    all_records = []
    folder_stats = {}

    for xml_file in sorted(MEDQUAD_DIR.rglob("*.xml")):
        records = parse_xml_file(xml_file)

        if not records:
            continue

        folder_name = xml_file.parent.name

        folder_stats[folder_name] = folder_stats.get(folder_name, 0) + len(records)

        all_records.extend(records)

    print("Documents Extracted Per Collection")
    print("-" * 60)

    for folder, count in sorted(folder_stats.items()):
        print(f"{folder:<45} {count:>6}")

    print("-" * 60)
    print(f"{'TOTAL':<45} {len(all_records):>6}")

    if not all_records:
        print("\nNo records found.")
        return

    corpus_path = OUTPUT_DIR / "corpus.json"

    with open(corpus_path, "w", encoding="utf-8") as file:
        json.dump(
            all_records,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print("\nCorpus Generation Completed")
    print(f"Saved: {corpus_path}")
    print(f"Documents: {len(all_records):,}")


if __name__ == "__main__":
    main()
