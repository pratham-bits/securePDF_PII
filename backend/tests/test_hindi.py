from pathlib import Path

from app.pipeline.document import extract_document, verify_output
from app.pipeline.locate import find_pii
from app.pipeline.redact import redact_pdf

HINDI = Path(__file__).resolve().parents[2] / "samples" / "sample_scanned_hi.pdf"
LANG = "eng+hin"


def _types(extraction):
    return {f.detection.entity_type for f in find_pii(extraction.words)}


def test_hindi_scan_is_read_in_devanagari():
    extraction = extract_document(HINDI, lang=LANG)
    assert extraction.modes == ["ocr"]
    texts = {w.text for w in extraction.words}
    assert "समझौता" in texts  # a Hindi word is read as Hindi, not as noise


def test_hindi_scan_yields_pii_that_english_only_ocr_misses():
    types = _types(extract_document(HINDI, lang=LANG))
    # Aadhaar written in Devanagari digits, and a bank account with a Hindi label.
    assert {"AADHAAR", "BANK_ACCOUNT", "PAN", "EMAIL", "PHONE_IN", "IFSC"} <= types
    assert "AADHAAR" not in _types(extract_document(HINDI, lang="eng"))


def test_hindi_scan_redaction_is_verified_with_both_languages(tmp_path):
    extraction = extract_document(HINDI, lang=LANG)
    boxes = [b for f in find_pii(extraction.words) for b in f.boxes]
    out = tmp_path / "out.pdf"
    redact_pdf(HINDI, out, boxes)
    data = out.read_bytes()
    assert verify_output(data, boxes, extraction.modes, lang=LANG) == []
    assert len(verify_output(HINDI.read_bytes(), boxes, extraction.modes, lang=LANG)) > 0
    leftover = {w.text for w in extract_document(data, lang=LANG).words}
    assert "ABCDE1234F" not in leftover
    assert "२३४५" not in leftover