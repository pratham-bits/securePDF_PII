"""A rule-only baseline: names and addresses found from the words around them.

It exists to answer "how much does ML add over cheap cues?". On the synthetic set it is
flattering, because the cues mirror the generator's templates. Its real value is when it
is run on your own sample documents. It covers PERSON and ADDRESS only.
"""

import re

_WORD = r"(?:[A-Z][a-z]+|[ऀ-ॿ]+)"
_NAME = rf"(?:(?:Mr|Mrs|Ms)\.\s+|श्री(?:मती)?\s+)?{_WORD}(?: {_WORD}){{0,2}}"

PERSON_LINE_LABELS = ("Father's Name:", "Account Holder:", "पिता का नाम:", "खाताधारक:", "Name:", "नाम:")
ADDRESS_LINE_LABELS = ("Address:", "पता:")
INLINE_PERSON = [
    re.compile(rf"(?:Mr|Mrs|Ms)\.\s+{_WORD}(?: {_WORD}){{0,2}}"),
    re.compile(rf"श्री(?:मती)?\s+{_WORD}(?: {_WORD}){{0,2}}"),
    re.compile(rf"(?:UPI/|यूपीआई/)(?P<n>{_NAME})"),
    re.compile(rf"(?:Signed by |हस्ताक्षरकर्ता: )(?P<n>{_NAME})"),
]


def _line_spans(text):
    pos = 0
    for line in text.split("\n"):
        yield pos, line
        pos += len(line) + 1


def predict(text):
    found = []
    for start, line in _line_spans(text):
        for labels, entity in ((PERSON_LINE_LABELS, "PERSON"), (ADDRESS_LINE_LABELS, "ADDRESS")):
            for label in labels:
                if line.startswith(label):
                    rest = line[len(label):]
                    value = rest.strip()
                    if value:
                        begin = start + len(label) + (len(rest) - len(rest.lstrip()))
                        found.append({"label": entity, "start": begin, "end": begin + len(value), "score": 1.0})
                    break
    for pattern in INLINE_PERSON:
        for m in pattern.finditer(text):
            a, b = (m.start("n"), m.end("n")) if "n" in pattern.groupindex else (m.start(), m.end())
            found.append({"label": "PERSON", "start": a, "end": b, "score": 1.0})
    # keep the longest span when cues overlap
    found.sort(key=lambda e: (-(e["end"] - e["start"]), e["start"]))
    kept = []
    for e in found:
        if all(e["end"] <= k["start"] or e["start"] >= k["end"] for k in kept):
            kept.append(e)
    return sorted(kept, key=lambda e: e["start"])
