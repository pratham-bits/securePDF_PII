"""Score a name/address/organisation/date detector on the synthetic set (or your own).

  python ml/benchmark/run_benchmark.py --predictor cue
  python ml/benchmark/run_benchmark.py --predictor gliner --thresholds 0.3,0.5,0.7

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

ROOT = Path(__file__).resolve().parents[1]
LABEL_NAMES = {
    "person name": "PERSON",
    "address": "ADDRESS",
    "organization": "ORGANIZATION",
    "date": "DATE",
}
CHUNK_CHARS = 800  # GLiNER reads a limited number of tokens at a time


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


def run(docs, predict, thresholds):
    started = time.perf_counter()
    raw = {d["id"]: predict(d["text"]) for d in docs}
    seconds = time.perf_counter() - started
    chars = sum(len(d["text"]) for d in docs)
    results = {}
    for t in thresholds:
        kept = {i: [e for e in spans if e["score"] >= t] for i, spans in raw.items()}
        results[str(t)] = evaluate(docs, kept)
    return {
        "n_docs": len(docs),
        "seconds_per_doc": round(seconds / max(len(docs), 1), 4),
        "seconds_per_1000_chars": round(seconds / max(chars, 1) * 1000, 4),
        "results": results,
    }


def show(report):
    fmt = lambda v: "  -  " if v is None else f"{v:5.2f}"
    for t, res in report["results"].items():
        print(f"\n=== threshold {t} ===")
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
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    thresholds = sorted(float(x) for x in a.thresholds.split(","))
    predict = cue_baseline.predict if a.predictor == "cue" else gliner_predictor(a.model, thresholds[0])
    report = run(load(a.data), predict, thresholds if a.predictor == "gliner" else [0.0])
    report.update(predictor=a.predictor, model=a.model if a.predictor == "gliner" else None,
                  dataset=Path(a.data).name, device=getattr(predict, "device", "cpu"))
    out = Path(a.out) if a.out else ROOT / "reports" / f"{Path(a.data).stem}_{a.predictor}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    show(report)
    print(f"\nreport written to {out}")


if __name__ == "__main__":
    main()
