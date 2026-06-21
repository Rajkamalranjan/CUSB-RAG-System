"""Fine-tune the dense retriever with MultipleNegativesRankingLoss."""

from __future__ import annotations

import argparse
from pathlib import Path

from sentence_transformers import InputExample, SentenceTransformer, losses
from torch.utils.data import DataLoader

from training.data.dataset_builder import load_pairs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", default="data/benchmark/synthetic_pairs.jsonl")
    parser.add_argument("--base-model", default="intfloat/multilingual-e5-small")
    parser.add_argument("--output", default="models/cusb-e5-finetuned")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()

    pairs = load_pairs(Path(args.pairs))
    if not pairs:
        raise FileNotFoundError(f"No training pairs found in {args.pairs}")

    model = SentenceTransformer(args.base_model, device="cuda")
    examples = [InputExample(texts=[query, passage]) for query, passage in pairs]
    loader = DataLoader(examples, shuffle=True, batch_size=args.batch_size)
    train_loss = losses.MultipleNegativesRankingLoss(model)
    model.fit(
        train_objectives=[(loader, train_loss)],
        epochs=args.epochs,
        warmup_steps=max(100, len(loader) // 10),
        output_path=args.output,
        use_amp=True,
        checkpoint_path=str(Path(args.output) / "checkpoints"),
        checkpoint_save_steps=500,
    )


if __name__ == "__main__":
    main()

