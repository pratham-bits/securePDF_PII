import re
from dataclasses import dataclass

from app.pipeline.validators import luhn_valid, verhoeff_valid

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def normalize_digits(text: str) -> str:
    """Map Devanagari digits to ASCII. Length-preserving, so offsets stay valid."""
    return text.translate(_DEVANAGARI_DIGITS)


@dataclass(frozen=True)
class Detection:
    entity_type: str
    start: int
    end: int
    text: str  # kept in memory only; never store this in the database
    score: float
    source: str = "rules"
    checksum_ok: bool | None = None  # None when the entity has no checksum


EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"
)
# Format-only check: the 4th letter (holder type) is not restricted, so that
# recall stays high. False positives are caught in the review step.
PAN_RE = re.compile(r"(?<![A-Za-z0-9])[A-Z]{5}[0-9]{4}[A-Z](?![A-Za-z0-9])")
AADHAAR_RE = re.compile(
    r"(?<![0-9])(?<![0-9][ -])[2-9][0-9]{3}[ -]?[0-9]{4}[ -]?[0-9]{4}(?![0-9])(?![ -][0-9])"
)
PHONE_RE = re.compile(
    r"(?<![0-9])(?:(?:\+91|0091|91)[ -]?)?[6-9][0-9]{4}[ -]?[0-9]{5}(?![0-9])"
)
CARD_RE = re.compile(r"(?<![0-9])[0-9](?:[ -]?[0-9]){12,18}(?![0-9])")


def _make(entity_type, match, original, score, checksum_ok=None) -> Detection:
    start, end = match.start(), match.end()
    return Detection(entity_type, start, end, original[start:end], score,
                     checksum_ok=checksum_ok)


def resolve_overlaps(detections: list[Detection]) -> list[Detection]:
    """When spans overlap, keep the higher score, then the longer span."""
    ordered = sorted(detections, key=lambda d: (-d.score, -(d.end - d.start), d.start))
    kept: list[Detection] = []
    for d in ordered:
        if all(d.end <= k.start or d.start >= k.end for k in kept):
            kept.append(d)
    return sorted(kept, key=lambda d: d.start)


def detect_rules(text: str) -> list[Detection]:
    norm = normalize_digits(text)
    found: list[Detection] = []

    for m in EMAIL_RE.finditer(norm):
        found.append(_make("EMAIL", m, text, 0.95))

    for m in PAN_RE.finditer(norm):
        found.append(_make("PAN", m, text, 0.90))

    for m in AADHAAR_RE.finditer(norm):
        ok = verhoeff_valid(re.sub(r"\D", "", m.group()))
        found.append(_make("AADHAAR", m, text, 0.95 if ok else 0.40, ok))

    for m in PHONE_RE.finditer(norm):
        found.append(_make("PHONE_IN", m, text, 0.80))

    for m in CARD_RE.finditer(norm):
        if luhn_valid(re.sub(r"\D", "", m.group())):
            found.append(_make("CREDIT_CARD", m, text, 0.90, True))

    return resolve_overlaps(found)