"""Pure scoring helpers for the extraction eval — no model calls, unit-testable."""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher

INTENTS = ("order", "inquiry", "complaint")
NAME_MATCH_THRESHOLD = 0.6  # SequenceMatcher ratio to count two item names as "the same"


def _norm(s: str) -> str:
    return " ".join(str(s).lower().split())


def name_sim(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def _qty_eq(a: float, b: float) -> bool:
    return abs(float(a) - float(b)) < 1e-6


@dataclass
class ExampleScore:
    example_id: str
    json_valid: bool
    intent_ok: bool = False
    expected_intent: str = ""
    predicted_intent: str = ""
    # item-level tallies
    item_tp: int = 0          # right name + unit + qty
    item_fp: int = 0          # predicted item with no gold match (hallucination)
    item_fn: int = 0          # gold item the model missed
    name_ok: int = 0          # matched pairs whose name cleared the threshold
    unit_ok: int = 0          # matched pairs with the right unit
    qty_ok: int = 0           # matched pairs with the right quantity
    matched_pairs: int = 0
    qty_abs_err: list[float] = field(default_factory=list)
    exact_match: bool = False


def score_example(
    example_id: str,
    expected: dict,
    predicted: dict | None,
) -> ExampleScore:
    """`predicted is None` -> the model failed to return schema-valid JSON."""
    exp_items = expected.get("items", [])
    exp_intent = expected["intent"]

    if predicted is None:
        return ExampleScore(
            example_id=example_id,
            json_valid=False,
            expected_intent=exp_intent,
            item_fn=len(exp_items),
        )

    pred_items = predicted.get("items", [])
    pred_intent = predicted.get("intent", "")
    s = ExampleScore(
        example_id=example_id,
        json_valid=True,
        expected_intent=exp_intent,
        predicted_intent=pred_intent,
        intent_ok=(pred_intent == exp_intent),
    )

    # greedy align: each gold item takes its best still-free predicted item
    free = list(range(len(pred_items)))
    aligned: list[tuple[dict, dict | None]] = []
    for g in exp_items:
        best_i, best_r = None, 0.0
        for i in free:
            r = name_sim(g["name"], pred_items[i]["name"])
            if r > best_r:
                best_i, best_r = i, r
        if best_i is not None and best_r >= NAME_MATCH_THRESHOLD:
            free.remove(best_i)
            aligned.append((g, pred_items[best_i]))
        else:
            aligned.append((g, None))

    for g, p in aligned:
        if p is None:
            s.item_fn += 1
            continue
        s.matched_pairs += 1
        s.name_ok += 1  # cleared threshold by construction
        unit_ok = _norm(g["unit"]) == _norm(p.get("unit", ""))
        qty_ok = _qty_eq(g["quantity"], p.get("quantity", 0))
        s.unit_ok += int(unit_ok)
        s.qty_ok += int(qty_ok)
        s.qty_abs_err.append(abs(float(g["quantity"]) - float(p.get("quantity", 0))))
        if unit_ok and qty_ok:
            s.item_tp += 1
        else:
            s.item_fn += 1  # matched by name but wrong -> still a miss on that gold item

    s.item_fp = len(free)  # predicted items nobody claimed

    s.exact_match = (
        s.intent_ok
        and s.item_tp == len(exp_items)
        and s.item_fp == 0
    )
    return s


def _macro_f1(report: dict[str, dict]) -> float:
    """Average F1 over the intent classes that actually appear in the gold set."""
    present = [v["f1"] for v in report.values() if v["support"] > 0]
    return sum(present) / len(present) if present else 0.0


def _prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(f1, 3)}


def aggregate(scores: list[ExampleScore]) -> dict:
    n = len(scores)
    valid = [s for s in scores if s.json_valid]

    # per-intent P/R/F1 (only over examples with valid JSON)
    intent_report = {}
    for c in INTENTS:
        tp = sum(1 for s in valid if s.expected_intent == c and s.predicted_intent == c)
        fp = sum(1 for s in valid if s.expected_intent != c and s.predicted_intent == c)
        fn = sum(1 for s in valid if s.expected_intent == c and s.predicted_intent != c)
        intent_report[c] = {**_prf(tp, fp, fn), "support": tp + fn}

    item_tp = sum(s.item_tp for s in scores)
    item_fp = sum(s.item_fp for s in scores)
    item_fn = sum(s.item_fn for s in scores)
    all_qty_err = [e for s in scores for e in s.qty_abs_err]
    matched = sum(s.matched_pairs for s in scores)

    return {
        "n_examples": n,
        "json_validity_rate": round(len(valid) / n, 3) if n else 0.0,
        "intent_accuracy": round(sum(s.intent_ok for s in scores) / n, 3) if n else 0.0,
        "intent_macro_f1": round(_macro_f1(intent_report), 3),
        "intent_per_class": intent_report,
        "order_exact_match_rate": round(sum(s.exact_match for s in scores) / n, 3) if n else 0.0,
        "item": _prf(item_tp, item_fp, item_fn),
        "item_counts": {"tp": item_tp, "fp": item_fp, "fn": item_fn},
        "unit_accuracy": round(sum(s.unit_ok for s in scores) / matched, 3) if matched else 0.0,
        "qty_accuracy": round(sum(s.qty_ok for s in scores) / matched, 3) if matched else 0.0,
        "qty_mae": round(sum(all_qty_err) / len(all_qty_err), 3) if all_qty_err else 0.0,
        "hallucination_rate": round(item_fp / (item_tp + item_fp), 3) if item_tp + item_fp else 0.0,
    }
