"""Run the extraction model over the gold set and print an accuracy table.

    uv run python -m eval.run                 # whole gold set
    uv run python -m eval.run --limit 5        # quick smoke
    uv run python -m eval.run --model gemma3:1b # A/B a different model

Results (aggregate + per-example) are saved to eval/results/<timestamp>.json so
you can diff two prompt versions.
"""

import argparse
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings
from app.services.extraction import extract_order
from eval.metrics import ExampleScore, aggregate, score_example

EVAL_DIR = Path(__file__).resolve().parent
GOLD = EVAL_DIR / "gold.jsonl"
RESULTS_DIR = EVAL_DIR / "results"


def _load_gold(limit: int | None) -> list[dict]:
    rows = [json.loads(line) for line in GOLD.read_text().splitlines() if line.strip()]
    return rows[:limit] if limit else rows


async def _predict(message: str) -> dict | None:
    try:
        return (await extract_order(message)).model_dump(mode="json")
    except Exception:  # eval must never crash on one bad row (invalid JSON, timeout, ...)
        return None


def _fmt_pct(x: float) -> str:
    return f"{x * 100:5.1f}%"


def _print_table(agg: dict) -> None:
    print(f"\n  examples            {agg['n_examples']}")
    print(f"  JSON validity       {_fmt_pct(agg['json_validity_rate'])}")
    print(f"  intent accuracy     {_fmt_pct(agg['intent_accuracy'])}")
    print(f"  intent macro-F1     {agg['intent_macro_f1']:.3f}")
    for c, v in agg["intent_per_class"].items():
        print(
            f"    {c:<9} P {v['precision']:.2f}  R {v['recall']:.2f}  "
            f"F1 {v['f1']:.2f}  (n={v['support']})"
        )
    print(f"  order exact match   {_fmt_pct(agg['order_exact_match_rate'])}")
    it = agg["item"]
    print(
        f"  item P/R/F1         {it['precision']:.2f} / {it['recall']:.2f} / {it['f1']:.2f}"
        f"   {agg['item_counts']}"
    )
    print(f"  unit accuracy       {_fmt_pct(agg['unit_accuracy'])}")
    print(f"  qty accuracy        {_fmt_pct(agg['qty_accuracy'])}")
    print(f"  qty MAE             {agg['qty_mae']:.3f}")
    print(f"  hallucination rate  {_fmt_pct(agg['hallucination_rate'])}\n")


async def main(limit: int | None, model: str) -> None:
    settings.ollama_model = model  # let --model override for A/B
    gold = _load_gold(limit)
    prompt_hash = hashlib.sha256(
        (EVAL_DIR.parent / "app" / "prompts" / "extract_order.txt").read_bytes()
    ).hexdigest()[:12]

    print(f"model={model}  prompt={prompt_hash}  n={len(gold)}")
    scores: list[ExampleScore] = []
    per_example: list[dict] = []
    for i, row in enumerate(gold, 1):
        pred = await _predict(row["message"])
        s = score_example(row["id"], row["expected"], pred)
        scores.append(s)
        mark = "ok " if s.exact_match else ("json" if not s.json_valid else "  ~")
        print(f"  [{i:>2}/{len(gold)}] {mark} {row['id']}  «{row['message'][:52]}»")
        per_example.append(
            {
                "id": row["id"],
                "message": row["message"],
                "expected": row["expected"],
                "predicted": pred,
                "exact_match": s.exact_match,
                "intent_ok": s.intent_ok,
                "json_valid": s.json_valid,
            }
        )

    agg = aggregate(scores)
    _print_table(agg)

    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = RESULTS_DIR / f"{stamp}.json"
    out.write_text(
        json.dumps(
            {
                "model": model,
                "prompt_hash": prompt_hash,
                "timestamp": stamp,
                "aggregate": agg,
                "examples": per_example,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print(f"saved {out.relative_to(EVAL_DIR.parent)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--model", default=settings.ollama_model)
    args = ap.parse_args()
    asyncio.run(main(args.limit, args.model))
