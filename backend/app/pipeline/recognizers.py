import re
from dataclasses import dataclass

from app.pipeline.validators import gstin_valid, luhn_valid, verhoeff_valid

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


# --- Patterns: the original detectors ---------------------------------------
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

# --- Patterns: the expansion pack -------------------------------------------
IFSC_RE = re.compile(r"(?<![A-Za-z0-9])[A-Z]{4}0[A-Z0-9]{6}(?![A-Za-z0-9])")
# Only a number right after an account label counts: bare digits are too common.
BANK_ACCOUNT_RE = re.compile(
    r"(?i)(?:a/c|\bacc(?:ount)?|खाता|खाते)\.?\s*"
    r"(?:no\.?|number|num|संख्या|नंबर|सं\.?)?\s*[:\-#]?\s*"
    r"(?P<num>[0-9][0-9 -]{7,20}[0-9])(?![0-9])"
)
VID_RE = re.compile(
    r"(?i)(?:\bvid\b|virtual\s+id|वर्चुअल\s*आईडी)\s*[:\-#]?\s*"
    r"(?P<num>[0-9]{4}(?:[ -]?[0-9]{4}){3})(?![0-9])"
)
PASSPORT_RE = re.compile(r"(?<![A-Za-z0-9])[A-PR-WY][0-9]{7}(?![A-Za-z0-9])")
VOTER_RE = re.compile(r"(?<![A-Za-z0-9])[A-Z]{3}[0-9]{7}(?![A-Za-z0-9])")
DL_RE = re.compile(
    r"(?<![A-Za-z0-9])[A-Z]{2}[ -]?[0-9]{2}[ -]?(?:19|20)[0-9]{2}[ -]?[0-9]{7}(?![A-Za-z0-9])"
)
GSTIN_RE = re.compile(
    r"(?<![A-Za-z0-9])[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z](?![A-Za-z0-9])"
)
# A UPI handle has no dot after the "@", which keeps it apart from an email address.
UPI_RE = re.compile(
    r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._-]{2,64}@(?P<handle>[A-Za-z][A-Za-z0-9]{1,31})"
    r"(?![A-Za-z0-9])(?!\.[A-Za-z0-9])"
)
VEHICLE_RE = re.compile(
    r"(?<![A-Za-z0-9])[A-Z]{2}[ -]?[0-9]{2}[ -]?[A-Z]{1,3}[ -]?[0-9]{4}(?![A-Za-z0-9])"
)
_MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
_DATE_VALUE = (
    r"(?:[0-9]{1,2}[/.\-][0-9]{1,2}[/.\-][0-9]{2,4}"
    r"|[0-9]{1,2}(?:st|nd|rd|th)?[ \-](?:" + _MONTHS + r")[a-z]*\.?,?[ \-][0-9]{4})"
)
DOB_RE = re.compile(
    r"(?i)(?:\bdob\b|date\s+of\s+birth|born\s+on|जन्म\s*तिथि|जन्मतिथि)\s*[:\-]?\s*"
    r"(?P<date>" + _DATE_VALUE + r")"
)

# --- Patterns: card, EPFO, ABHA and device identifiers -----------------------
# CVV and expiry mean nothing without a label, so the label is always required.
CVV_RE = re.compile(
    r"(?i)(?:(?<![A-Za-z])(?:cvv2?|cvc2?)|security\s+code|सीवीवी)\s*[:\-#]?\s*"
    r"(?P<num>[0-9]{3,4})(?![0-9])"
)
CARD_EXPIRY_RE = re.compile(
    r"(?i)(?:(?<![A-Za-z])exp(?:iry|\.)?(?:\s+date)?|valid\s+(?:thru|through|till|until)|वैधता)"
    r"\s*[:\-#]?\s*(?P<date>(?:0[1-9]|1[0-2])\s*/\s*(?:[0-9]{4}|[0-9]{2}))(?![0-9])"
)
UAN_RE = re.compile(
    r"(?i)(?:(?<![A-Za-z])uan|यूएएन)\s*(?:no\.?|number|संख्या|नंबर)?\s*[:\-#]?\s*"
    r"(?P<num>[0-9]{12})(?![0-9])"
)
# ABHA is 14 digits. The dashed 2-4-4-4 layout is specific enough to stand alone.
ABHA_LABELLED_RE = re.compile(
    r"(?i)(?:(?<![A-Za-z])abha|आभा|health\s*id)\s*(?:no\.?|number|संख्या|नंबर)?\s*[:\-#]?\s*"
    r"(?P<num>[0-9]{2}(?:[ -]?[0-9]{4}){3})(?![0-9])"
)
ABHA_DASHED_RE = re.compile(r"(?<![0-9])[0-9]{2}-[0-9]{4}-[0-9]{4}-[0-9]{4}(?![0-9])")
# With the label we skip the Luhn check, so an IMEI with one misread digit is still found.
IMEI_RE = re.compile(
    r"(?i)(?<![A-Za-z])imei\s*[0-9]?\s*(?:no\.?|number)?\s*[:\-#]?\s*"
    r"(?P<num>[0-9](?:[ -]?[0-9]){14})(?![0-9])"
)

PASSPORT_CONTEXT = ("passport", "पासपोर्ट")
VOTER_CONTEXT = ("voter", "epic", "मतदाता", "निर्वाचन")
DL_CONTEXT = ("driving", "licence", "license", "dl no", "d.l.", "ड्राइविंग", "लाइसेंस")
KNOWN_UPI_HANDLES = {
    "okaxis", "okhdfcbank", "okicici", "oksbi", "ybl", "ibl", "axl", "paytm", "upi", "apl",
}


def _make_span(entity_type, start, end, original, score, checksum_ok=None) -> Detection:
    return Detection(
        entity_type, start, end, original[start:end], score, checksum_ok=checksum_ok
    )


def _make(entity_type, match, original, score, checksum_ok=None) -> Detection:
    return _make_span(
        entity_type, match.start(), match.end(), original, score, checksum_ok
    )


def _has_context(norm: str, start: int, words: tuple[str, ...], window: int = 40) -> bool:
    """True if one of the words appears shortly before the match."""
    before = norm[max(0, start - window):start].lower()
    return any(word in before for word in words)


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

    # Original detectors
    for m in EMAIL_RE.finditer(norm):
        found.append(_make("EMAIL", m, text, 0.95))

    for m in PAN_RE.finditer(norm):
        found.append(_make("PAN", m, text, 0.90))

    for m in AADHAAR_RE.finditer(norm):
        ok = verhoeff_valid(re.sub(r"\D", "", m.group()))
        found.append(_make("AADHAAR", m, text, 0.95 if ok else 0.40, ok))
    # Fallback detection: OCR of a Hindi Aadhaar written in Devanagari digits often inserts a
    # space between every digit, so the primary regex (which allows one optional separator between
    # 4‑digit groups) cannot match. We normalise the entire string to remove all spaces/hyphens
    # and retry. This fallback is restricted to texts that contain Devanagari characters so it
    # never fires when English-only OCR happens to produce an unrelated 12‑digit number.
    # We use a real match position on `norm` (not a dummy span) so that `locate()` can still
    # build bounding boxes: we find the first position in `norm` where the digit sequence starts.
    if not any(d.entity_type == "AADHAAR" for d in found) and re.search(r"[\u0900-\u097F\u0966-\u096F]", text):
        norm_nospace = re.sub(r"[ \-]", "", norm)
        m2 = re.search(r"[2-9]\d{11}", norm_nospace)
        if m2:
            ok2 = verhoeff_valid(m2.group())
            # Locate the start of the matched digit sequence inside the original `norm` string.
            # We scan `norm` character by character, skipping spaces/hyphens, until we have
            # consumed as many non-separator characters as the match start in `norm_nospace`.
            target_ns_start = m2.start()
            ns_idx = 0
            real_start = 0
            for real_start, ch in enumerate(norm):
                if ch not in (" ", "-"):
                    if ns_idx == target_ns_start:
                        break
                    ns_idx += 1
            # Find real_end similarly (advance another 12 non-separator characters).
            real_end = real_start
            digits_seen = 0
            for i in range(real_start, len(norm)):
                if norm[i] not in (" ", "-"):
                    digits_seen += 1
                real_end = i + 1
                if digits_seen == 12:
                    break
            found.append(_make_span("AADHAAR", real_start, real_end, text, 0.95 if ok2 else 0.40, ok2))


    for m in PHONE_RE.finditer(norm):
        found.append(_make("PHONE_IN", m, text, 0.80))

    for m in CARD_RE.finditer(norm):
        if luhn_valid(re.sub(r"\D", "", m.group())):
            found.append(_make("CREDIT_CARD", m, text, 0.90, True))

    # Expansion pack
    for m in IFSC_RE.finditer(norm):
        found.append(_make("IFSC", m, text, 0.85))

    for m in BANK_ACCOUNT_RE.finditer(norm):
        digits = re.sub(r"\D", "", m.group("num"))
        if 9 <= len(digits) <= 18:
            found.append(
                _make_span("BANK_ACCOUNT", m.start("num"), m.end("num"), text, 0.92)
            )

    for m in VID_RE.finditer(norm):
        found.append(_make_span("AADHAAR_VID", m.start("num"), m.end("num"), text, 0.92))

    for m in PASSPORT_RE.finditer(norm):
        near = _has_context(norm, m.start(), PASSPORT_CONTEXT)
        found.append(_make("PASSPORT_IN", m, text, 0.90 if near else 0.45))

    for m in VOTER_RE.finditer(norm):
        near = _has_context(norm, m.start(), VOTER_CONTEXT)
        found.append(_make("VOTER_ID", m, text, 0.90 if near else 0.40))

    for m in DL_RE.finditer(norm):
        near = _has_context(norm, m.start(), DL_CONTEXT)
        found.append(_make("DRIVING_LICENCE", m, text, 0.92 if near else 0.85))

    for m in GSTIN_RE.finditer(norm):
        ok = gstin_valid(m.group())
        found.append(_make("GSTIN", m, text, 0.95 if ok else 0.50, ok))

    for m in UPI_RE.finditer(norm):
        known = m.group("handle").lower() in KNOWN_UPI_HANDLES
        found.append(_make("UPI_ID", m, text, 0.90 if known else 0.50))

    for m in VEHICLE_RE.finditer(norm):
        found.append(_make("VEHICLE_REG", m, text, 0.70))

    for m in CVV_RE.finditer(norm):
        found.append(_make_span("CVV", m.start("num"), m.end("num"), text, 0.92))

    for m in CARD_EXPIRY_RE.finditer(norm):
        found.append(
            _make_span("CARD_EXPIRY", m.start("date"), m.end("date"), text, 0.85)
        )

    for m in UAN_RE.finditer(norm):
        found.append(_make_span("UAN", m.start("num"), m.end("num"), text, 0.96))

    for m in ABHA_LABELLED_RE.finditer(norm):
        found.append(_make_span("ABHA", m.start("num"), m.end("num"), text, 0.95))

    for m in ABHA_DASHED_RE.finditer(norm):
        found.append(_make("ABHA", m, text, 0.85))

    for m in IMEI_RE.finditer(norm):
        ok = luhn_valid(re.sub(r"\D", "", m.group("num")))
        found.append(_make_span("IMEI", m.start("num"), m.end("num"), text, 0.96, ok))
    
    for m in DOB_RE.finditer(norm):
        found.append(
            _make_span("DATE_OF_BIRTH", m.start("date"), m.end("date"), text, 0.90)
        )

    return resolve_overlaps(found)