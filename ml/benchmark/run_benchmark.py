"""Score a name/address/organisation/date detector on the synthetic set (or your own).

  python ml/benchmark/run_benchmark.py --predictor cue
  python ml/benchmark/run_benchmark.py --predictor gliner --thresholds 0.1,0.2,0.3,0.5 --dump preds.jsonl

Variants of the same predictions are scored side by side:
  raw          what the model returned
  merged       fragments of one entity joined (see postprocess.py)
  merged+cue   merged, plus the name-cue baseline's findings added on top

The report holds numbers only, never document text, so it is safe to commit.
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import cue_baseline  # noqa: E402
from metrics import evaluate  # noqa: E402
from postprocess import merge  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LABEL_NAMES = {
    "person name": "PERSON",
    "address": "ADDRESS",
    "organization": "ORGANIZATION",
    "date": "DATE",
}
CHUNK_CHARS = 800  # GLiNER reads a limited number of tokens at a time
VARIANTS = ("raw", "merged", "merged+cue")


def chunk_text(text, limit=CHUNK_CHARS):
    """Split into pieces of at most `limit` characters at line breaks (or spaces).

    Returns (offset, piece) pairs so predictions can be mapped back to the full text.
    """
    chunks, start = [], 0
    while start < len(text):
        end = min(start + limit, len(text))
        if end < len(text):
            cut = max(text.rfind("\n", start, end), text.rfind(" ", start, end))
            end = cut + 1 if cut > start else end
        chunks.append((start, text[start:end]))
        start = end
    return chunks


def load(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def gliner_predictor(model_name, min_threshold):
    from gliner import GLiNER  # imported late: the baseline needs no ML packages

    model = GLiNER.from_pretrained(model_name)
    import torch  # installed together with gliner

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    print(f"running on {device}")
    names = list(LABEL_NAMES)

    def predict(text):
        out = []
        for offset, piece in chunk_text(text):
            for e in model.predict_entities(piece, names, threshold=min_threshold):
                out.append({
                    "label": LABEL_NAMES[e["label"]],
                    "start": offset + e["start"],
                    "end": offset + e["end"],
                    "score": e["score"],
                })
        return out

    predict.device = device
    return predict


def variant_spans(text, spans, variant, cue_spans=None):
    if variant == "raw":
        return spans
    if variant == "merged":
        return merge(spans, text)
    if variant == "merged+cue":
        extra = cue_baseline.predict(text) if cue_spans is None else cue_spans
        return merge(spans + extra, text)
    raise ValueError(f"unknown variant: {variant}")


def run(docs, predict, thresholds, variants=("raw",)):
    started = time.perf_counter()
    raw = {d["id"]: predict(d["text"]) for d in docs}
    seconds = time.perf_counter() - started
    chars = sum(len(d["text"]) for d in docs)
    cue = {d["id"]: cue_baseline.predict(d["text"]) for d in docs} if "merged+cue" in variants else {}
    results = {}
    for t in thresholds:
        for v in variants:
            kept = {}
            for d in docs:
                spans = [e for e in raw[d["id"]] if e["score"] >= t]
                kept[d["id"]] = variant_spans(d["text"], spans, v, cue.get(d["id"]))
            results[f"{t}|{v}"] = evaluate(docs, kept)
    return {
        "n_docs": len(docs),
        "seconds_per_doc": round(seconds / max(len(docs), 1), 4),
        "seconds_per_1000_chars": round(seconds / max(chars, 1) * 1000, 4),
        "results": results,
        "raw_predictions": raw,
    }


def dump_predictions(path, raw):
    """Offsets, labels and scores only: no document text."""
    lines = (json.dumps({"id": i, "spans": spans}) for i, spans in raw.items())
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def show(report):
    fmt = lambda v: "  -  " if v is None else f"{v:5.2f}"
    for key, res in report["results"].items():
        t, v = key.split("|")
        print(f"\n=== threshold {t} | {v} ===")
        print(f"{'':16}{'gold':>6}{'prec':>7}{'recall':>7}{'f1':>7}{'charR':>7}{'full':>7}")
        for section in ("by_label", "by_lang", "by_doc_type"):
            for name, m in res[section].items():
                print(f"{name:16}{m['gold']:>6}  {fmt(m['precision'])} {fmt(m['recall'])} "
                      f"{fmt(m['f1'])} {fmt(m['char_recall'])} {fmt(m['full_cover'])}")
            print()
    print(f"speed: {report['seconds_per_doc']} s/doc, {report['seconds_per_1000_chars']} s per 1000 chars")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data" / "synthetic_v1.jsonl"))
    ap.add_argument("--predictor", choices=("cue", "gliner"), required=True)
    ap.add_argument("--model", default="urchade/gliner_multi-v2.1")
    ap.add_argument("--thresholds", default="0.5")
    ap.add_argument("--variants", default=None, help="comma list of: " + ", ".join(VARIANTS))
    ap.add_argument("--dump", default=None, help="write raw predictions (no text) to this file")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    gliner = a.predictor == "gliner"
    thresholds = sorted(float(x) for x in a.thresholds.split(",")) if gliner else [0.0]
    variants = tuple((a.variants or ("raw,merged,merged+cue" if gliner else "raw")).split(","))
    predict = gliner_predictor(a.model, thresholds[0]) if gliner else cue_baseline.predict
    report = run(load(a.data), predict, thresholds, variants)
    raw = report.pop("raw_predictions")
    if a.dump:
        dump_predictions(a.dump, raw)
    report.update(predictor=a.predictor, model=a.model if gliner else None,
                  dataset=Path(a.data).name, device=getattr(predict, "device", "cpu"))
    out = Path(a.out) if a.out else ROOT / "reports" / f"{Path(a.data).stem}_{a.predictor}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    show(report)
    print(f"\nreport written to {out}")


if __name__ == "__main__":
    main()
