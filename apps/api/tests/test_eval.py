"""Unit tests for the eval scoring — pure, no model calls."""

from eval.metrics import aggregate, score_example

EXP = {
    "intent": "order",
    "items": [
        {"name": "semen gresik", "quantity": 5, "unit": "sak"},
        {"name": "cat tembok putih", "quantity": 2, "unit": "kaleng"},
    ],
}


def test_perfect_prediction_is_exact_match() -> None:
    s = score_example("x", EXP, EXP)
    assert s.exact_match and s.intent_ok
    assert (s.item_tp, s.item_fp, s.item_fn) == (2, 0, 0)


def test_invalid_json_counts_every_gold_item_as_missed() -> None:
    s = score_example("x", EXP, None)
    assert not s.json_valid and not s.exact_match
    assert (s.item_tp, s.item_fp, s.item_fn) == (0, 0, 2)


def test_wrong_unit_and_extra_item_are_penalised() -> None:
    pred = {
        "intent": "order",
        "items": [
            {"name": "semen gresik", "quantity": 5, "unit": "kaleng"},  # wrong unit
            {"name": "cat tembok putih", "quantity": 2, "unit": "kaleng"},  # ok
            {"name": "paku", "quantity": 1, "unit": "kg"},  # hallucinated
        ],
    }
    s = score_example("x", EXP, pred)
    assert s.item_tp == 1
    assert s.item_fp == 1  # the paku
    assert s.item_fn == 1  # semen matched by name but wrong unit
    assert not s.exact_match


def test_aggregate_reports_rates() -> None:
    good = score_example("a", EXP, EXP)
    bad = score_example("b", EXP, None)
    agg = aggregate([good, bad])
    assert agg["n_examples"] == 2
    assert agg["json_validity_rate"] == 0.5
    assert agg["order_exact_match_rate"] == 0.5
    # intent P/R/F1 is scored only over examples that returned valid JSON
    assert agg["intent_per_class"]["order"]["support"] == 1
