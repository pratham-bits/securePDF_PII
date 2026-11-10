"""Cheap fixes applied after a model has predicted spans.

merge() joins same-label pieces that overlap or sit next to each other. It is what turns an
address the model returned in fragments ("Flat 4B", "Shanti Nagar", "Dhanbad ...") into one
span. The gap rules differ by label on purpose: an address may contain commas, but joining two
names across a comma would redact a list of two people as if it were one.
"""

import re

# label -> (largest gap in characters, characters allowed inside the gap)
GAP_RULES = {
    "ADDRESS": (3, re.compile(r"[ ,.\-/]*")),
    "PERSON": (1, re.compile(r" *")),
    "ORGANIZATION": (1, re.compile(r" *")),
    "DATE": (1, re.compile(r" *")),
}
DEFAULT_RULE = (0, re.compile(r""))


def merge(spans, text):
    out = []
    for label in sorted({s["label"] for s in spans}):
        max_gap, allowed = GAP_RULES.get(label, DEFAULT_RULE)
        current = None
        for s in sorted((s for s in spans if s["label"] == label), key=lambda s: (s["start"], s["end"])):
            if current is not None:
                gap = text[current["end"]:s["start"]]
                touching = s["start"] <= current["end"]
                if touching or (len(gap) <= max_gap and allowed.fullmatch(gap)):
                    current["end"] = max(current["end"], s["end"])
                    current["score"] = max(current["score"], s["score"])
                    continue
                out.append(current)
            current = dict(s)
        if current is not None:
            out.append(current)
    return sorted(out, key=lambda s: (s["start"], s["end"]))
