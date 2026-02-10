#!/usr/bin/env python3
"""
Build training manifests from qwen_behavior_references.json for your coding example videos.

Reads llm_training/qwen_behavior_references.json and writes:
  1. behavior_examples_qwen.jsonl  — one line per behavior with media (for Qwen-VL training)
  2. behavior_examples_export.json — array of records for Mistral (export_to_jsonl.js → train_lora.py)

Run from repo root or from llm_training/:
  python llm_training/scripts/build_behavior_examples_manifests.py
  cd llm_training && python scripts/build_behavior_examples_manifests.py

Then:
  - Qwen: Merge behavior_examples_qwen.jsonl with train_qwen.jsonl (or use alone) and run Qwen training.
  - Mistral: Merge behavior_examples_export.json with exported.json, then:
    node export_to_jsonl.js combined_export.json --split 0.9
    python train_lora.py --train_file train.jsonl --validation_file validation.jsonl ...
"""

import json
import sys
from pathlib import Path

# Resolve llm_training dir (script may be run from repo root or from llm_training)
SCRIPT_DIR = Path(__file__).resolve().parent
LLM_DIR = SCRIPT_DIR.parent
REFS_PATH = LLM_DIR / "qwen_behavior_references.json"
OUT_JSONL = LLM_DIR / "behavior_examples_qwen.jsonl"
OUT_JSON = LLM_DIR / "behavior_examples_export.json"

# Placeholder rubric (replace with your real rubric name/structure when training)
PLACEHOLDER_RUBRIC = {
    "name": "Speech (Delivery + Content)",
    "categories": [
        {"name": "Content", "subcategories": ["Organization", "Supporting Material"]},
        {"name": "Delivery", "subcategories": ["Body/professionalism", "Vocal delivery"]},
    ],
}

# Placeholder scores shape (delivery behaviors: deduct; purpose statement: credit)
def _placeholder_scores(behavior: dict) -> dict:
    t = (behavior.get("type") or "delivery").lower()
    severity = (behavior.get("severity_default") or "moderate").lower()
    # Example: Delivery category 10 pts, Content 10 pts
    if t == "content" or behavior.get("label", "").lower().startswith("purpose"):
        return {
            "Content": {"score": 8, "maxScore": 10, "subcategories": [{"name": "Organization", "points": 4, "maxPoints": 5}, {"name": "Supporting Material", "points": 4, "maxPoints": 5}]},
            "Delivery": {"score": 10, "maxScore": 10, "subcategories": [{"name": "Body/professionalism", "points": 5, "maxPoints": 5}, {"name": "Vocal delivery", "points": 5, "maxPoints": 5}]},
        }
    # Delivery behavior: deduct
    deduct = 3 if severity == "moderate" else 1
    return {
        "Content": {"score": 10, "maxScore": 10, "subcategories": [{"name": "Organization", "points": 5, "maxPoints": 5}, {"name": "Supporting Material", "points": 5, "maxPoints": 5}]},
        "Delivery": {"score": 10 - deduct, "maxScore": 10, "subcategories": [{"name": "Body/professionalism", "points": max(0, 5 - deduct), "maxPoints": 5}, {"name": "Vocal delivery", "points": 5, "maxPoints": 5}]},
    }


def main():
    if not REFS_PATH.exists():
        print(f"Error: {REFS_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    with open(REFS_PATH, "r", encoding="utf-8") as f:
        behaviors = json.load(f)

    if not isinstance(behaviors, list):
        print("Error: qwen_behavior_references.json must be a JSON array.", file=sys.stderr)
        sys.exit(1)

    # Build Qwen JSONL (only entries that have media_url)
    qwen_lines = []
    mistral_records = []

    for b in behaviors:
        media_url = (b.get("media_url") or "").strip()
        if not media_url:
            continue
        media_type = (b.get("media_type") or "video").lower()
        label = b.get("label") or "behavior"
        rubric = b.get("rubric") or PLACEHOLDER_RUBRIC
        scores = b.get("scores") or _placeholder_scores(b)

        # Qwen: one line per behavior
        line = {"rubric": rubric, "scores": scores}
        if media_type == "image":
            line["image_path"] = media_url
        else:
            line["video_path"] = media_url
        qwen_lines.append(line)

        # Mistral: one record per behavior (transcript + video_notes → scores)
        video_notes = f"{b.get('description') or ''}. {b.get('scoring_guidance') or ''}".strip()
        mistral_records.append({
            "transcript": "N/A",
            "video_notes": video_notes,
            "rubric": rubric.get("name") if isinstance(rubric, dict) else "Speech (Delivery + Content)",
            "rubric_structure": rubric if isinstance(rubric, dict) else PLACEHOLDER_RUBRIC,
            "scores": scores,
            "source_behavior_label": label,
        })

    # Write Qwen JSONL
    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for line in qwen_lines:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    print(f"Wrote {len(qwen_lines)} lines to {OUT_JSONL}")

    # Write Mistral export JSON
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(mistral_records, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(mistral_records)} records to {OUT_JSON}")

    print("\nNext steps:")
    print("  Qwen:   Merge with train_qwen.jsonl or use as-is, then run Qwen training.")
    print("  Mistral: Merge with exported.json → export_to_jsonl.js → train_lora.py (see BEHAVIOR_EXAMPLES_NEXT_STEPS.md).")


if __name__ == "__main__":
    main()
