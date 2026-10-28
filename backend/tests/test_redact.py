from pathlib import Path

import pymupdf

from app.pipeline.extract import extract_words
from app.pipeline.locate import find_pii
from app.pipeline.redact import redact_pdf, verify_redaction

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "sample_digital_en.pdf"


def _sample_boxes():
    findings = find_pii(extract_words(SAMPLE))
    return [b for f in findings for b in f.boxes]


def test_redaction_removes_pii_text_but_keeps_the_rest(tmp_path):
    out = tmp_path / "out.pdf"
    redact_pdf(SAMPLE, out, _sample_boxes())
    with pymupdf.open(out) as doc:
        assert doc.page_count == 1
        text = doc[0].get_text()
    for secret in ["ABCDE1234F", "rahul.verma@example.com", "98765", "43210", "+91"]:
        assert secret not in text
    assert "RENT AGREEMENT" in text
    assert "Landlord" in text


def test_verification_passes_after_redaction(tmp_path):
    out = tmp_path / "out.pdf"
    boxes = _sample_boxes()
    redact_pdf(SAMPLE, out, boxes)
    assert verify_redaction(out, boxes) == []


def test_verification_catches_an_unredacted_file():
    boxes = _sample_boxes()
    leaks = verify_redaction(SAMPLE, boxes)
    assert len(leaks) == len(boxes)


def test_metadata_is_scrubbed(tmp_path):
    src = tmp_path / "meta.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), "PAN ABCDE1234F")
        doc.set_metadata({"author": "Rahul Verma", "title": "Rent agreement"})
        doc.save(src)

    out = tmp_path / "out.pdf"
    boxes = [b for f in find_pii(extract_words(src)) for b in f.boxes]
    redact_pdf(src, out, boxes)

    with pymupdf.open(out) as doc:
        meta = doc.metadata or {}
        assert not meta.get("author")
        assert not meta.get("title")
