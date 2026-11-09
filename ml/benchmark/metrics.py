"""Span-level scoring built for redaction, where a partly covered name still leaks.

Besides exact-match precision/recall/F1 it reports:
  char_recall      share of the true characters covered by predictions of the same label
  full_cover       share of true entities covered 100% (the ones that would not leak)
  char_precision   share of predicted characters that were really PII (over-redaction)
The "ANY" label ignores which label was predicted: a name tagged as an organisation is
still redacted, so for the leak question the label does not matter.
"""

from collections import defaultdict

KEYS = ("gold", "pred", "tp", "gold_chars", "pred_chars", "overlap_chars", "gold_full")


def _chars(spans):
    covered = set()
    for start, end in spans:
        covered.update(range(start, end))
    return covered


def _counts(gold, pred):
    g_chars, p_chars = _chars(gold), _chars(pred)
    return {
        "gold": len(gold),
        "pred": len(pred),
        "tp": len(set(gold) & set(pred)),
        "gold_chars": len(g_chars),
        "pred_chars": len(p_chars),
        "overlap_chars": len(g_chars & p_chars),
        "gold_full": sum(1 for a, b in gold if _chars([(a, b)]) <= p_chars),
    }


def _ratio(num, den):
    return None if den == 0 else round(num / den, 4)


def _metrics(c):
    p, r = _ratio(c["tp"], c["pred"]), _ratio(c["tp"], c["gold"])
    f1 = None if not p or not r else round(2 * p * r / (p + r), 4)
    return {
        "gold": c["gold"], "pred": c["pred"],
        "precision": p, "recall": r, "f1": f1,
        "char_recall": _ratio(c["overlap_chars"], c["gold_chars"]),
        "char_precision": _ratio(c["overlap_chars"], c["pred_chars"]),
        "full_cover": _ratio(c["gold_full"], c["gold"]),
    }


def _rollup(table, lang=None, doc_type=None, label=None):
    total = dict.fromkeys(KEYS, 0)
    for (lg, dt, lb), counts in table.items():
        if (lang in (None, lg)) and (doc_type in (None, dt)) and (label in (None, lb)):
            for k in KEYS:
                total[k] += counts[k]
    return _metrics(total)


def evaluate(docs, predictions):
    """docs: dataset rows. predictions: {doc_id: [{"label","start","end"}, ...]}."""
    table = defaultdict(lambda: dict.fromkeys(KEYS, 0))
    labels = set()
    for doc in docs:
        preds = predictions.get(doc["id"], [])
        for mode in ("label", "any"):
            pick = (lambda e: e["label"]) if mode == "label" else (lambda e: "ANY")
            names = {pick(e) for e in doc["entities"]} | {pick(e) for e in preds}
            labels |= names
            for name in names:
                gold = [(e["start"], e["end"]) for e in doc["entities"] if pick(e) == name]
                pred = [(e["start"], e["end"]) for e in preds if pick(e) == name]
                cell = table[(doc["lang"], doc["doc_type"], name)]
                for k, v in _counts(gold, pred).items():
                    cell[k] += v
    langs = sorted({d["lang"] for d in docs})
    types = sorted({d["doc_type"] for d in docs})
    return {
        "by_label": {lb: _rollup(table, label=lb) for lb in sorted(labels)},
        "by_lang": {lg: _rollup(table, lang=lg, label="ANY") for lg in langs},
        "by_doc_type": {dt: _rollup(table, doc_type=dt, label="ANY") for dt in types},
        "by_label_and_lang": {
            f"{lb}|{lg}": _rollup(table, lang=lg, label=lb)
            for lb in sorted(labels) for lg in langs
        },
    }