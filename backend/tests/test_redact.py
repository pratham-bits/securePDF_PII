from pathlib import Path

import pymupdf
from app.pipeline.document import extract_document, verify_output
from app.pipeline.extract import extract_words
from app.pipeline.locate import find_pii
from app.pipeline.redact import redact_bytes, redact_pdf, verify_redaction

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


# --- form fields and annotations ----------------------------------------------

INTRO = "Application form for account opening. Please fill in all the fields below."


def _form_with_fields() -> bytes:
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), INTRO, fontsize=10)
        for name, value, top in (("pan", "ABCDE1234F", 100), ("note", "keep me", 140)):
            field = pymupdf.Widget()
            field.field_type = getattr(pymupdf, "PDF_WIDGET_TYPE_TEXT", 0)
            field.field_name = name
            field.field_value = value
            field.rect = pymupdf.Rect(72, top, 250, top + 25)
            page.add_widget(field)
        return doc.tobytes()


def _boxes_for(data: bytes):
    extraction = extract_document(data)
    return extraction, [b for f in find_pii(extraction.words) for b in f.boxes]


def test_a_value_in_a_form_field_is_redacted_and_verified():
    data = _form_with_fields()
    extraction, boxes = _boxes_for(data)
    assert boxes  # the PAN inside the field is detected
    out = redact_bytes(data, boxes)
    assert verify_output(out, boxes, extraction.modes) == []
    with pymupdf.open(stream=out) as doc:
        text = doc[0].get_text()
        assert "ABCDE1234F" not in text
        assert list(doc[0].widgets()) == []


def test_other_form_fields_stay_visible_as_plain_text():
    data = _form_with_fields()
    _, boxes = _boxes_for(data)
    with pymupdf.open(stream=redact_bytes(data, boxes)) as doc:
        assert "keep me" in doc[0].get_text()
        assert not doc.is_form_pdf  # no editable fields, no hidden field values


def test_a_comment_is_removed_even_when_no_box_touches_it():
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), INTRO, fontsize=10)
        page.add_text_annot((300, 300), "Call Rahul on 9876543210")
        data = doc.tobytes()
    with pymupdf.open(stream=redact_bytes(data, [])) as doc:
        assert list(doc[0].annots()) == []


def test_text_in_a_visible_annotation_is_redacted():
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), INTRO, fontsize=10)
        page.add_freetext_annot(pymupdf.Rect(72, 200, 300, 225), "PAN ABCDE1234F", fontsize=11)
        data = doc.tobytes()
    extraction, boxes = _boxes_for(data)
    assert boxes
    out = redact_bytes(data, boxes)
    assert verify_output(out, boxes, extraction.modes) == []
    with pymupdf.open(stream=out) as doc:
        assert "ABCDE1234F" not in doc[0].get_text()
        assert list(doc[0].annots()) == []