#!/usr/bin/env python3
"""
LoRA fine-tuning for Mistral 7B on SpeechGradebook evaluation data.

Expects: train.jsonl (and optionally validation.jsonl) in messages format:
  {"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}

Usage:
  pip install -r requirements-train.txt
  export HF_TOKEN=your_huggingface_token   # needed for mistralai/Mistral-7B-Instruct-v0.2
  python train_lora.py --train_file train.jsonl [--validation_file validation.jsonl] --output_dir ./mistral7b-speech-lora

Requires: ~16GB GPU VRAM (or use --load_in_8bit for ~10GB).
"""

import argparse
import json
import os
from pathlib import Path

import torch
from datasets import Dataset, load_dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, TaskType
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from trl import SFTTrainer


def parse_args():
    p = argparse.ArgumentParser(description="Mistral 7B LoRA fine-tuning for speech evaluation")
    p.add_argument("--model_name", default="mistralai/Mistral-7B-Instruct-v0.2", help="Base model ID")
    p.add_argument("--train_file", default="train.jsonl", help="Path to train.jsonl")
    p.add_argument("--validation_file", default=None, help="Path to validation.jsonl (optional)")
    p.add_argument("--output_dir", default="./mistral7b-speech-lora", help="Where to save adapter and logs")
    p.add_argument("--max_seq_length", type=int, default=2048, help="Max tokens per example")
    p.add_argument("--num_epochs", type=int, default=3)
    p.add_argument("--per_device_train_batch_size", type=int, default=2)
    p.add_argument("--gradient_accumulation_steps", type=int, default=4)
    p.add_argument("--learning_rate", type=float, default=2e-5)
    p.add_argument("--lora_r", type=int, default=16)
    p.add_argument("--lora_alpha", type=int, default=32)
    p.add_argument("--load_in_8bit", action="store_true", help="Load base model in 8-bit to save VRAM")
    p.add_argument("--use_4bit", action="store_true", help="Load base model in 4-bit (requires bitsandbytes)")
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


def main():
    args = parse_args()
    train_path = Path(args.train_file)
    if not train_path.exists():
        raise FileNotFoundError(f"Train file not found: {train_path}")

    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(
        args.model_name,
        trust_remote_code=True,
    )
    # Mistral Instruct uses same chat template; ensure padding side for causal LM
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model_kwargs = {"torch_dtype": torch.bfloat16 if torch.cuda.is_available() else torch.float32}
    if args.load_in_8bit:
        model_kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
    elif args.use_4bit:
        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4",
        )

    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        **model_kwargs,
    )
    if args.load_in_8bit or args.use_4bit:
        model = prepare_model_for_kbit_training(model)

    # LoRA for Mistral: attention projections
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Dataset: JSONL with "messages" key (system / user / assistant)
    train_data = load_jsonl(args.train_file)
    train_dataset = Dataset.from_list([{"messages": ex["messages"]} for ex in train_data])

    eval_dataset = None
    if args.validation_file and Path(args.validation_file).exists():
        eval_data = load_jsonl(args.validation_file)
        eval_dataset = Dataset.from_list([{"messages": ex["messages"]} for ex in eval_data])

    def formatting_func(example):
        return tokenizer.apply_chat_template(
            example["messages"],
            tokenize=False,
            add_generation_prompt=False,
        )

    # Use trainer default data collator (trl 0.20+ removed DataCollatorForCompletionOnlyLM;
    # we train on full sequence unless you use SFTConfig with assistant_only_loss=True and no formatting_func)
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.num_epochs,
        per_device_train_batch_size=args.per_device_train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        bf16=torch.cuda.is_available(),
        logging_steps=10,
        save_strategy="epoch",
        save_total_limit=2,
        report_to="none",
    )
    if eval_dataset:
        training_args.eval_strategy = "epoch"
        training_args.per_device_eval_batch_size = 1

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer,
        formatting_func=formatting_func,
        max_seq_length=args.max_seq_length,
    )
    trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"Adapter and tokenizer saved to {args.output_dir}")


if __name__ == "__main__":
    main()
