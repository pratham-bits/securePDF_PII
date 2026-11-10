"""Show HOW a detector fails: which true entities it missed, split, or labelled wrongly.

  python ml/benchmark/analyze_misses.py --predictions preds.jsonl --threshold 0.3

Uses the synthetic data, so printing document text here is fine. Do not point it at real
documents and paste the output anywhere.
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent))

from run_benchmark import ROOT, load, variant_spans  # noqa: E402


def _covered(gold, spans):
    chars = set()
    for s in spans:
        chars.update(range(s["start"], s["end"]))
    return all(i in chars for i in range(gold["start"], gold["end"])), any(
        i in chars for i in range(gold["start"], gold["end"])
    )


def classify(gold, preds):
    """covered | wrong_label | partial | wrong_label_partial | missed"""
    same = [p for p in preds if p["label"] == gold["label"]]
    full, touched = _covered(gold, same)
    if full:
        return "covered"
    if touched:
        return "partial"
    any_full, any_touched = _covered(gold, preds)
    if any_full:
        return "wrong_label"
    return "wrong_label_partial" if any_touched else "missed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "synthetic_v1.jsonl"))
    ap.add_argument("--predictions", required=True)
    ap.add_argument("--threshold", type=float, default=0.3)
    ap.add_argument("--variant", default="raw")
    ap.add_argument("--examples", type=int, default=3)
    a = ap.parse_args()

    raw = {}
    for line in Path(a.predictions).read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        raw[row["id"]] = row["spans"]
    counts, examples = defaultdict(Counter), defaultdict(list)
    for doc in load(a.data):
        spans = [s for s in raw.get(doc["id"], []) if s["score"] >= a.threshold]
        spans = variant_spans(doc["text"], spans, a.variant)
        for gold in doc["entities"]:
            outcome = classify(gold, spans)
            key = (gold["label"], doc["lang"])
            counts[key][outcome] += 1
            if outcome != "covered" and len(examples[key + (outcome,)]) < a.examples:
                pieces = [doc["text"][p["start"]:p["end"]] for p in spans
                          if p["start"] < gold["end"] and p["end"] > gold["start"]]
                examples[key + (outcome,)].append((gold["text"], pieces))

    print(f"threshold {a.threshold}, variant {a.variant}")
    for key in sorted(counts):
        total = sum(counts[key].values())
        summary = ", ".join(f"{k} {v}" for k, v in counts[key].most_common())
        print(f"\n{key[0]} / {key[1]}  (n={total}): {summary}")
        for outcome in ("partial", "wrong_label", "wrong_label_partial", "missed"):
            for gold_text, pieces in examples.get(key + (outcome,), []):
                print(f"   {outcome:20} gold={gold_text!r}  predicted={pieces}")


if __name__ == "__main__":
    main()
