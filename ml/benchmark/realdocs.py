"""Turn your own sample PDFs into a labelled set the benchmark can score.

You type only the names, addresses, organisations and dates you can see. The script finds every
occurrence in the text the real pipeline extracts (OCR noise included) and writes a dataset in
the same format as the synthetic one.

  1. Put fake-data PDFs in ml/real/   (name them legal_01.pdf, id_01.pdf, bank_01.pdf ...)
  2. python ml/benchmark/realdocs.py extract    -> ml/real/text/<name>.txt and ml/real/labels.txt
  3. Fill in ml/real/labels.txt, copying strings from the text files
  4. python ml/benchmark/realdocs.py build      -> ml/real/real_v1.jsonl

labels.txt format:
  == legal_01 | legal                 (optional third field: hi or en to override the language guess)
  PERSON: Ramesh Kumar ; Sunita Verma
  ADDRESS: Flat 4, Shanti Nagar, Dhanbad 826004
  ORGANIZATION: Bharat Textiles Pvt Ltd
  DATE: 12 March 2024
  NONE                               (only for a document that truly contains none of these)

Use fake data only. Everything under ml/real/ is gitignored.
"""

import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

ML = Path(__file__).resolve().parents[1]
REPO = ML.parent
REAL = ML / "real"
LABELS = ("PERSON", "ADDRESS", "ORGANIZATION", "DATE")
DOC_TYPES = {"legal": "legal", "id": "id_card", "bank": "bank_statement"}
_LETTER = r"[\wऀ-ॿ]"  # word characters, including Devanagari vowel signs
FUZZY_MIN_RATIO = 0.85  # how alike text must be to a typed value to count as an OCR-garbled copy
FUZZY_MIN_CHARS = 10  # shorter values are too easy to confuse, so they must match exactly


# --- text ---------------------------------------------------------------------------

def _new_line(prev, word):
    if word.page != prev.page:
        return True
    overlap = min(prev.y1, word.y1) - max(prev.y0, word.y0)
    smaller = min(prev.y1 - prev.y0, word.y1 - word.y0)
    return overlap <= 0 or overlap < 0.5 * smaller


def words_to_text(words):
    """Join words with a space, or a line break where the line changes.

    Returns the text and each word's (start, end). Production's own build_text uses single
    spaces only; the name and address models need to see line structure.
    """
    parts, spans, pos, prev = [], [], 0, None
    for word in words:
        if prev is not None:
            parts.append("\n" if _new_line(prev, word) else " ")
            pos += 1
        parts.append(word.text)
        spans.append((pos, pos + len(word.text)))
        pos += len(word.text)
        prev = word
    return "".join(parts), spans


def extract_pdf(path, lang="eng+hin"):
    sys.path.insert(0, str(REPO / "backend"))  # lazy: only extraction needs the backend packages
    from app.pipeline.document import extract_document

    return words_to_text(extract_document(path, lang=lang).words)[0]


# --- labels -------------------------------------------------------------------------

def parse_labels(text):
    """Return a list of blocks: {name, doc_type, lang, labels, none}."""
    blocks = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("=="):
            fields = [f.strip() for f in line[2:].split("|")]
            blocks.append({"name": fields[0], "doc_type": fields[1] if len(fields) > 1 and fields[1] else "other",
                           "lang": fields[2] if len(fields) > 2 and fields[2] else None,
                           "labels": {}, "none": False})
        elif not blocks:
            raise ValueError(f"line {number}: expected a '== name | type' header first")
        elif line.upper() == "NONE":
            blocks[-1]["none"] = True
        elif ":" in line and line.split(":", 1)[0].strip().upper() in LABELS:
            label, values = line.split(":", 1)
            found = [v.strip() for v in values.split(";") if v.strip()]
            if found:  # a blank line means "not filled in yet", never "none"
                blocks[-1]["labels"].setdefault(label.strip().upper(), []).extend(found)
        else:
            raise ValueError(f"line {number}: unknown label in {line!r} (use {', '.join(LABELS)} or NONE)")
    return blocks


def find_occurrences(text, value):
    """Every occurrence of `value`, tolerant of line breaks and repeated spaces inside it."""
    tokens = value.split()
    if not tokens:
        return []
    pattern = rf"(?<!{_LETTER})" + r"\s+".join(re.escape(t) for t in tokens) + rf"(?!{_LETTER})"
    return [(m.start(), m.end()) for m in re.finditer(pattern, text)]


def _is_word_char(c):
    return c.isalnum() or "\u0900" <= c <= "\u097f"


def find_fuzzy(text, value, taken=()):
    """Copies of `value` that OCR garbled ("Rahul Verrna" for "Rahul Verma").

    Only for values of FUZZY_MIN_CHARS or more. Never overlaps `taken` spans (exact hits).
    """
    target = " ".join(value.split()).lower()
    if len(target) < FUZZY_MIN_CHARS:
        return []
    words = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]
    size = len(target.split())
    found = []
    for n in sorted({max(1, size - 1), size, size + 1}):
        for i in range(len(words) - n + 1):
            a, b = words[i][0], words[i + n - 1][1]
            while b > a and not _is_word_char(text[b - 1]):  # "Verrna." is "Verrna"
                b -= 1
            while a < b and not _is_word_char(text[a]):
                a += 1
            if a >= b:
                continue
            matcher = SequenceMatcher(None, " ".join(text[a:b].split()).lower(), target)
            if matcher.real_quick_ratio() < FUZZY_MIN_RATIO or matcher.quick_ratio() < FUZZY_MIN_RATIO:
                continue
            ratio = matcher.ratio()
            if ratio >= FUZZY_MIN_RATIO:
                found.append((ratio, b - a, a, b))
    found.sort(key=lambda f: (-f[0], -f[1]))
    chosen = []
    for _ratio, _length, a, b in found:
        if not any(a < tb and b > ta for ta, tb in [*taken, *chosen]):
            chosen.append((a, b))
    return sorted(chosen)


def guess_lang(text):
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "en"
    return "hi" if sum("ऀ" <= c <= "ॿ" for c in letters) / len(letters) > 0.3 else "en"


def build_row(block, text) -> tuple[dict[str, Any] | None, list[str]]:
    """Return (row, problems). Row is None when the block cannot be used."""
    problems = []
    if not block["labels"] and not block["none"]:
        return None, [f"{block['name']}: no labels and no NONE line, skipped"]
    entities, fuzzy_count = [], 0
    for label, values in block["labels"].items():
        for value in values:
            hits = find_occurrences(text, value)
            garbled = find_fuzzy(text, value, taken=hits)
            if not hits and not garbled:
                problems.append(f"{block['name']}: {label} {value!r} not found in the extracted text")
            fuzzy_count += len(garbled)
            entities += [{"label": label, "start": a, "end": b} for a, b in hits + garbled]
    # drop an entity that sits inside a longer one of the same label
    entities = [e for e in entities if not any(
        o is not e and o["label"] == e["label"] and o["start"] <= e["start"] and e["end"] <= o["end"]
        and (o["end"] - o["start"]) > (e["end"] - e["start"]) for o in entities)]
    entities = sorted({(e["start"], e["end"], e["label"]) for e in entities})
    return {
        "id": f"real-{block['name']}",
        "doc_type": block["doc_type"],
        "lang": block["lang"] or guess_lang(text),
        "fuzzy_entities": fuzzy_count,
        "text": text,
        "entities": [{"label": l, "start": a, "end": b, "text": text[a:b]} for a, b, l in entities],
    }, problems


# --- commands -----------------------------------------------------------------------

def cmd_extract(real=REAL, lang="eng+hin", extractor=extract_pdf):
    (real / "text").mkdir(parents=True, exist_ok=True)
    pdfs = sorted(real.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {real}. Put your fake-data PDFs there first.")
        return
    labels_file = real / "labels.txt"
    existing = labels_file.read_text(encoding="utf-8") if labels_file.exists() else ""
    known = {b["name"] for b in parse_labels(existing)} if existing.strip() else set()
    template = ""
    for pdf in pdfs:
        (real / "text" / f"{pdf.stem}.txt").write_text(extractor(pdf, lang), encoding="utf-8")
        if pdf.stem not in known:
            kind = DOC_TYPES.get(pdf.stem.split("_")[0].lower(), "other")
            template += f"\n== {pdf.stem} | {kind}\nPERSON: \nADDRESS: \nORGANIZATION: \nDATE: \n"
    if template:
        labels_file.write_text(existing + template, encoding="utf-8")
    print(f"extracted {len(pdfs)} documents into {real / 'text'}")
    print(f"labels template: {labels_file}  ({'added blocks for new documents' if template else 'nothing new to add'})")


def cmd_build(real=REAL):
    blocks = parse_labels((real / "labels.txt").read_text(encoding="utf-8"))
    rows, problems = [], []
    for block in blocks:
        text_file = real / "text" / f"{block['name']}.txt"
        if not text_file.exists():
            problems.append(f"{block['name']}: no extracted text, run extract first")
            continue
        row, issues = build_row(block, text_file.read_text(encoding="utf-8"))
        problems += issues
        if row:
            rows.append(row)
    out = real / "real_v1.jsonl"
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    counts = {}
    for r in rows:
        for e in r["entities"]:
            counts[e["label"]] = counts.get(e["label"], 0) + 1
    print(f"wrote {len(rows)} documents to {out}")
    print("entities:", counts)
    print(f"matched despite OCR errors (fuzzy): {sum(r['fuzzy_entities'] for r in rows)} of {sum(counts.values())}")
    for p in problems:
        print("  warning:", p)
    return rows, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=("extract", "build"))
    ap.add_argument("--lang", default="eng+hin")
    a = ap.parse_args()
    cmd_extract(lang=a.lang) if a.command == "extract" else cmd_build()


if __name__ == "__main__":
    main()
