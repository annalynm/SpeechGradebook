#!/usr/bin/env python3
"""
Evaluate the fine-tuned Mistral 7B adapter on a holdout set (validation.jsonl).

Reports: loss (if labels available), sample predictions vs expected, and optional
score agreement (MAE per section).

Usage:
  python eval_model.py --model_path ./mistral7b-speech-lora --validation_file validation.jsonl [--base_model mistralai/Mistral-7B-Instruct-v0.2]
"""

import argparse
import json
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def parse_args():
    p = argparse.ArgumentParser(description="Evaluate fine-tuned Mistral 7B on holdout set")
    p.add_argument("--model_path", default="./mistral7b-speech-lora", help="Path to adapter (and tokenizer)")
    p.add_argument("--base_model", default="mistralai/Mistral-7B-Instruct-v0.2", help="Base model ID")
    p.add_argument("--validation_file", default="validation.jsonl", help="Path to validation.jsonl")
    p.add_argument("--max_new_tokens", type=int, default=1024)
    p.add_argument("--num_samples", type=int, default=5, help="Number of examples to print (pred vs expected)")
    p.add_argument("--load_in_8bit", action="store_true", help="Load base model in 8-bit")
    return p.parse_args()


def load_jsonl(path: str):
    data = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data.append(json.loads(line))
    return data


def extract_json_from_assistant(text: str):
    """Try to extract a JSON object from model output (after [/INST] or at end)."""
    # Common pattern: model may output markdown or raw JSON
    text = text.strip()
    # Find last { ... } block
    start = text.rfind("{")
    if start == -1:
        return None
    depth = 0
    end = -1
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end == -1:
        return None
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return None


def main():
    args = parse_args()
    model_path = Path(args.model_path)
    val_path = Path(args.validation_file)
    if not model_path.exists():
        raise FileNotFoundError(f"Model path not found: {model_path}")
    if not val_path.exists():
        raise FileNotFoundError(f"Validation file not found: {val_path}")

    tokenizer = AutoTokenizer.from_pretrained(
        str(model_path),
        trust_remote_code=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model_kwargs = {"torch_dtype": torch.bfloat16 if torch.cuda.is_available() else torch.float32}
    if args.load_in_8bit:
        from transformers import BitsAndBytesConfig
        model_kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)

    base = AutoModelForCausalLM.from_pretrained(args.base_model, **model_kwargs)
    model = PeftModel.from_pretrained(base, str(model_path))
    model.eval()

    val_data = load_jsonl(args.validation_file)
    if not val_data:
        print("No examples in validation file.")
        return

    print(f"Loaded {len(val_data)} validation examples. Running inference on up to {args.num_samples} for display...\n")

    for i, ex in enumerate(val_data[: args.num_samples]):
        messages = ex["messages"]
        # Expected assistant content (ground truth)
        expected = next((m["content"] for m in messages if m["role"] == "assistant"), "")
        try:
            expected_json = json.loads(expected) if expected.strip().startswith("{") else None
        except json.JSONDecodeError:
            expected_json = None

        # Format prompt (system + user, no assistant)
        prompt_messages = [m for m in messages if m["role"] != "assistant"]
        prompt = tokenizer.apply_chat_template(
            prompt_messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}

        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
            )
        # Decode only the new part
        gen = tokenizer.decode(out[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)
        pred_json = extract_json_from_assistant(gen)

        print(f"--- Example {i + 1} ---")
        print("Expected (snippet):", (expected[:200] + "..." if len(expected) > 200 else expected))
        print("Predicted (snippet):", (gen[:200] + "..." if len(gen) > 200 else gen))
        if pred_json and expected_json:
            # Simple score comparison if both are section-style dicts
            exp_scores = []
            pred_scores = []
            for k, v in expected_json.items():
                if isinstance(v, dict) and "score" in v:
                    exp_scores.append(v["score"])
                    pred_scores.append(pred_json.get(k, {}).get("score", 0))
            if exp_scores and pred_scores:
                mae = sum(abs(p - e) for p, e in zip(pred_scores, exp_scores)) / len(exp_scores)
                print(f"MAE (section scores): {mae:.2f}")
        print()

    print("Done. For full validation loss, use the trainer's eval during training or run a separate eval loop with labels.")


if __name__ == "__main__":
    main()
