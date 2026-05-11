"""
Fine-tune CUSB AI Assistant using Unsloth (Fast QLoRA)
======================================================
Recommended: Run on Google Colab (Free T4 GPU)
Local: Requires CUDA GPU (RTX 3060+ or better)

Usage:
    # 1. First prepare data
    python src/prepare_finetune_data.py

    # 2. Then run training
    python finetune.py

Dependencies:
    pip install unsloth torch transformers trl
"""

import json
import sys
from pathlib import Path

# ===================== Configuration =====================
BASE_MODEL = "unsloth/Llama-3.2-1B-Instruct"  # Small, fast, ~2GB
# BASE_MODEL = "unsloth/Llama-3.2-3B-Instruct"  # Better quality, ~6GB
# BASE_MODEL = "unsloth/gemma-2-2b-it"          # Google model, good for Indian languages

DATA_PATH = Path("data/finetune_chat.jsonl")
OUTPUT_DIR = Path("models/cusb_finetuned")

MAX_SEQ_LENGTH = 2048
LORA_RANK = 16
LORA_ALPHA = 16
LEARNING_RATE = 2e-4
NUM_EPOCHS = 3
BATCH_SIZE = 4
GRADIENT_ACCUMULATION_STEPS = 4


def load_dataset(path: Path):
    """Load JSONL dataset."""
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def main():
    print("=" * 70)
    print("CUSB AI Assistant - Fine-tuning with Unsloth")
    print("=" * 70)

    # Check data exists
    if not DATA_PATH.exists():
        print(f"\n❌ Data not found: {DATA_PATH}")
        print("   Run first: python src/prepare_finetune_data.py")
        sys.exit(1)

    try:
        from unsloth import FastLanguageModel
        from trl import SFTTrainer
        from transformers import TrainingArguments
    except ImportError:
        print("\n❌ Missing dependencies. Install with:")
        print("   pip install unsloth trl")
        print("\n   Or use this Colab notebook (recommended):")
        print("   https://colab.research.google.com/drive/1Dyauq4kTZoL18Qa8ykIydGR_5VIJXM4Z")
        sys.exit(1)

    # Load model & tokenizer with Unsloth (4-bit quantization)
    print(f"\n📥 Loading base model: {BASE_MODEL}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,          # Auto-detect (float16 for GPU)
        load_in_4bit=True,   # QLoRA - memory efficient
    )

    # Add LoRA adapters
    print(f"\n🔧 Adding LoRA adapters (r={LORA_RANK}, alpha={LORA_ALPHA})")
    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_RANK,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_alpha=LORA_ALPHA,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    # Load training data
    print(f"\n📂 Loading training data: {DATA_PATH}")
    dataset = load_dataset(DATA_PATH)
    print(f"   Total examples: {len(dataset)}")

    # Format dataset for training (conversations -> text)
    def format_conversation(example):
        """Convert chat messages to model text format."""
        messages = example["messages"]
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False,
        )
        return {"text": text}

    # Convert to HF Dataset
    from datasets import Dataset
    hf_dataset = Dataset.from_list(dataset)
    formatted_dataset = hf_dataset.map(format_conversation)

    # Training arguments
    print(f"\n⚙️  Training Configuration:")
    print(f"   Epochs: {NUM_EPOCHS}")
    print(f"   Batch size: {BATCH_SIZE}")
    print(f"   Learning rate: {LEARNING_RATE}")
    print(f"   Gradient accumulation: {GRADIENT_ACCUMULATION_STEPS}")
    print(f"   Output: {OUTPUT_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCULATION_STEPS,
        learning_rate=LEARNING_RATE,
        warmup_steps=50,
        logging_steps=10,
        save_strategy="epoch",
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=42,
        report_to="none",  # Disable WandB/TensorBoard
    )

    # Initialize trainer
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=formatted_dataset,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        args=training_args,
    )

    # Train
    print("\n🚀 Starting training...")
    print("=" * 70)
    trainer.train()

    # Save model
    print("\n💾 Saving fine-tuned model...")
    model.save_pretrained_merged(str(OUTPUT_DIR / "merged"), tokenizer)
    model.save_pretrained(str(OUTPUT_DIR / "adapter"))
    tokenizer.save_pretrained(str(OUTPUT_DIR / "adapter"))

    print(f"\n✅ Fine-tuning complete!")
    print(f"   Merged model: {OUTPUT_DIR / 'merged'}")
    print(f"   LoRA adapter: {OUTPUT_DIR / 'adapter'}")
    print("\n" + "=" * 70)
    print("To use the fine-tuned model:")
    print(f"   from unsloth import FastLanguageModel")
    print(f"   model, tokenizer = FastLanguageModel.from_pretrained(")
    print(f'       model_name="{OUTPUT_DIR / "merged"}")")
    print("=" * 70)


if __name__ == "__main__":
    main()
