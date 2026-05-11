"""
Prepare CUSB training data for LLM fine-tuning.
Converts final_data_set.json to Alpaca format.

Usage:
    python src/prepare_finetune_data.py
Output:
    data/finetune_dataset.json
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import DATA_DIR, QA_DATASET_PATH


def load_qa_dataset(path: Path) -> list:
    """Load existing QA dataset."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def convert_to_alpaca(qa_data: list, system_prompt: str = None) -> list:
    """Convert QA pairs to Alpaca instruction format."""
    alpaca_data = []

    default_system = (
        "You are CUSB AI Assistant, a helpful chatbot for Central University of South Bihar. "
        "Answer student questions accurately based on CUSB information. "
        "Respond in the same language style as the question (English, Hindi, or Hinglish)."
    )
    system = system_prompt or default_system

    for item in qa_data:
        question = item.get("input", "").strip()
        answer = item.get("output", "").strip()

        if not question or not answer:
            continue

        # Some inputs have bilingual format: "Hindi? / English?"
        # Use the first part as instruction
        if "/" in question:
            parts = [p.strip() for p in question.split("/")]
            # Prefer Hinglish/Hindi part for instruction if present
            instruction = parts[0] if any(c in parts[0] for c in "कखग") or any(
                w in parts[0].lower() for w in ["kya", "hai", "kitna", "kaise"]
            ) else parts[0]
        else:
            instruction = question

        alpaca_data.append({
            "instruction": instruction,
            "input": "",
            "output": answer,
            "system": system,
        })

    return alpaca_data


def convert_to_chat_format(alpaca_data: list) -> list:
    """Convert Alpaca format to modern chat format (for Unsloth/TRL)."""
    chat_data = []

    for item in alpaca_data:
        chat_data.append({
            "messages": [
                {"role": "system", "content": item["system"]},
                {"role": "user", "content": item["instruction"]},
                {"role": "assistant", "content": item["output"]},
            ]
        })

    return chat_data


def save_dataset(data: list, output_path: Path, format: str = "chat"):
    """Save prepared dataset."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved {format} format: {output_path}")
    print(f"   Total examples: {len(data)}")
    print(f"   Sample:")
    print(json.dumps(data[0], indent=2, ensure_ascii=False))


def main():
    print("=" * 60)
    print("CUSB Fine-tuning Data Preparation")
    print("=" * 60)

    # Load existing QA dataset
    print(f"\n📥 Loading QA dataset: {QA_DATASET_PATH}")
    qa_data = load_qa_dataset(QA_DATASET_PATH)
    print(f"   Loaded {len(qa_data)} QA pairs")

    # Convert to Alpaca format
    print("\n🔄 Converting to Alpaca format...")
    alpaca_data = convert_to_alpaca(qa_data)
    print(f"   Converted {len(alpaca_data)} examples")

    # Save Alpaca format
    alpaca_path = DATA_DIR / "finetune_alpaca.json"
    save_dataset(alpaca_data, alpaca_path, "alpaca")

    # Convert to chat format (modern models prefer this)
    print("\n🔄 Converting to Chat format...")
    chat_data = convert_to_chat_format(alpaca_data)

    chat_path = DATA_DIR / "finetune_chat.json"
    save_dataset(chat_data, chat_path, "chat")

    # Also save as JSONL (one example per line, preferred by TRL/Unsloth)
    jsonl_path = DATA_DIR / "finetune_chat.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for item in chat_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"\n✅ Saved JSONL format: {jsonl_path}")
    print(f"   Total lines: {len(chat_data)}")

    print("\n" + "=" * 60)
    print("Data preparation complete!")
    print("Files created:")
    print(f"  - {alpaca_path}")
    print(f"  - {chat_path}")
    print(f"  - {jsonl_path}")
    print("\nNext step: Run finetune.py to start training")
    print("=" * 60)


if __name__ == "__main__":
    main()
