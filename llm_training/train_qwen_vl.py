#!/usr/bin/env python3
"""
Prepare and validate data for Qwen2.5-VL training (video tier).

Manifest format: train_qwen.jsonl — one JSON object per line:
  {"video_path": "path/to/video.mp4", "rubric": {...}, "scores": {...}}
  or {"image_path": "path/to/image.png", "rubric": {...}, "scores": {...}}
  Each line must have at least one of video_path or image_path (for video or still-image coding examples).

Rubric: same structure as app (name, categories with subcategories, etc.).
Scores: same as SpeechGradebook Model output (category -> score, maxScore, subcategories).

Usage:
  python train_qwen_vl.py --manifest train_qwen.jsonl --output_dir ./qwen2.5vl-speech-lora --validate_only
  python train_qwen_vl.py --manifest train_qwen.jsonl --output_dir ./qwen2.5vl-speech-lora --num_epochs 2  # when training loop is implemented

See DUAL_MODEL_TRAINING.md for two-tier setup (Mistral = text, Qwen = video).
"""

import argparse
import json
import os
from pathlib import Path


def load_manifest(path: str) -> list[dict]:
    out = []
    with open(path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Line {i}: invalid JSON: {e}")
    return out


def validate_item(item: dict, base_dir: Path, check_media_exists: bool) -> list[str]:
    errs = []
    if not isinstance(item, dict):
        errs.append("item must be a JSON object")
        return errs
    has_video = "video_path" in item and item["video_path"]
    has_image = "image_path" in item and item["image_path"]
    if not has_video and not has_image:
        errs.append("missing video_path or image_path")
    if check_media_exists:
        for key, label in (("video_path", "video"), ("image_path", "image")):
            path_val = item.get(key)
            if not path_val:
                continue
            if isinstance(path_val, str) and (path_val.startswith("http://") or path_val.startswith("https://")):
                pass  # URL: skip local file check (training can download)
            else:
                p = Path(path_val)
                if not p.is_absolute():
                    p = base_dir / p
                if not p.exists():
                    errs.append(f"{label} file not found: {item[key]}")
    if "rubric" not in item:
        errs.append("missing rubric")
    else:
        r = item["rubric"]
        if not isinstance(r, dict) or not r.get("categories"):
            errs.append("rubric must have categories")
    if "scores" not in item:
        errs.append("missing scores")
    else:
        s = item["scores"]
        if not isinstance(s, dict):
            errs.append("scores must be an object")
    return errs


def main():
    p = argparse.ArgumentParser(description="Qwen2.5-VL training for SpeechGradebook video tier")
    p.add_argument("--manifest", default="train_qwen.jsonl", help="JSONL manifest (video_path, rubric, scores per line)")
    p.add_argument("--output_dir", default="./qwen2.5vl-speech-lora", help="Output directory for adapter")
    p.add_argument("--num_epochs", type=int, default=2)
    p.add_argument("--batch_size", type=int, default=1)
    p.add_argument("--lr", type=float, default=2e-5)
    p.add_argument("--validate_only", action="store_true", help="Only validate manifest and exit")
    p.add_argument("--base_dir", default=".", help="Base directory for relative video_path/image_path in manifest")
    args = p.parse_args()

    base_dir = Path(args.base_dir).resolve()
    if not Path(args.manifest).exists():
        print(f"Manifest not found: {args.manifest}")
        print("Create a JSONL file with one JSON per line: {\"video_path\": \"...\" or \"image_path\": \"...\", \"rubric\": {...}, \"scores\": {...}}")
        return 1

    data = load_manifest(args.manifest)
    print(f"Loaded {len(data)} examples from {args.manifest}")

    all_ok = True
    for i, item in enumerate(data):
        errs = validate_item(item, base_dir, check_media_exists=True)
        if errs:
            print(f"  Example {i + 1}: {', '.join(errs)}")
            all_ok = False
    if not all_ok:
        return 1
    print("Validation passed.")

    if args.validate_only:
        print("Validate-only: skipping training. See DUAL_MODEL_TRAINING.md for full training (LLaMA-Factory or extended script).")
        return 0

    # Full training loop would go here: build Dataset from manifest, load Qwen2.5-VL + LoRA, train.
    # For now we do not implement the training step; use LLaMA-Factory with a custom dataset or extend this script.
    print("Training loop not yet implemented in this script.")
    print("Options: (1) Use LLaMA-Factory with a dataset adapter for this manifest format.")
    print("         (2) Extend this script with a PyTorch Dataset + Qwen2_5_VLProcessor/LoRA training.")
    print("See DUAL_MODEL_TRAINING.md.")
    return 1  # so SLURM job fails until training is implemented


if __name__ == "__main__":
    raise SystemExit(main())
