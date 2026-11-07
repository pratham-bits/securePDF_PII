import io
from pathlib import Path

import pymupdf
from PIL import Image, ImageStat

from app.pipeline.document import (
    _could_be_leaked_text,
    _inside_fraction,
    extract_document,
    verify_output,
)
from app.pipeline.extract import Word
from app.pipeline.locate import Box, find_pii
from app.pipeline.redact import redact_pdf

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
DIGITAL = SAMPLES / "sample_digital_en.pdf"
SCANNED = SAMPLES / "sample_scanned_en.pdf"


def _first_image(path):
    with pymupdf.open(path) as doc:
        page = doc[0]
        xref = page.get_images(full=True)[0][0]
        rect = page.get_image_rects(xref)[0]
        raw = doc.extract_image(xref)["image"]
    return Image.open(io.BytesIO(raw)).convert("L"), rect


def _region_stddev(img, rect, box) -> float:
    sx = img.width / rect.width
    sy = img.height / rect.height
    crop = img.crop((
        int((box.x0 - rect.x0) * sx),
        int((box.y0 - rect.y0) * sy),
        int((box.x1 - rect.x0) * sx),
        int((box.y1 - rect.y0) * sy),
    ))
    return ImageStat.Stat(crop).stddev[0]


def _boxes(extraction):
    return [b for f in find_pii(extraction.words) for b in f.boxes]


def test_digital_pages_use_the_text_layer():
    extraction = extract_document(DIGITAL)
    assert extraction.modes == ["digital"]
    assert extraction.words[0].conf is None


def test_scanned_pages_fall_back_to_ocr():
    extraction = extract_document(SCANNED)
    assert extraction.modes == ["ocr"]
    assert extraction.words[0].conf is not None


def test_scanned_redaction_wipes_the_image_pixels(tmp_path):
    boxes = _boxes(extract_document(SCANNED))
    assert boxes
    out = tmp_path / "out.pdf"
    redact_pdf(SCANNED, out, boxes)

    before, rect_before = _first_image(SCANNED)
    after, rect_after = _first_image(out)
    for box in boxes:
        assert _region_stddev(before, rect_before, box) > 10  # text is there
        assert _region_stddev(after, rect_after, box) < 5  # now uniform


def test_verification_passes_on_a_redacted_scan(tmp_path):
    extraction = extract_document(SCANNED)
    boxes = _boxes(extraction)
    out = tmp_path / "out.pdf"
    redact_pdf(SCANNED, out, boxes)
    assert verify_output(out, boxes, extraction.modes) == []


def test_verification_catches_an_unredacted_scan():
    extraction = extract_document(SCANNED)
    boxes = _boxes(extraction)
    assert len(verify_output(SCANNED, boxes, extraction.modes)) > 0


def test_label_word_stretched_over_a_black_box_is_not_a_leak():
    box = Box(0, 100.0, 10.0, 124.0, 22.0)
    label = Word(0, "Aadhaar:", 10.0, 10.0, 138.0, 22.0, 90.0)  # mostly outside the box
    leaked = Word(0, "ABCDE1234F", 100.0, 10.0, 124.0, 22.0, 90.0)
    assert _inside_fraction(label, box) < 0.5
    assert _inside_fraction(leaked, box) >= 0.5

def test_junk_read_on_a_black_box_is_not_a_leak_but_a_confident_word_is():
    junk = Word(0, "ia", 0.0, 0.0, 10.0, 10.0, 31.0)
    leaked = Word(0, "ABCDE1234F", 0.0, 0.0, 10.0, 10.0, 92.0)
    assert not _could_be_leaked_text(junk)
    assert _could_be_leaked_text(leaked)


# --- digital pages that also carry images -------------------------------------

LETTER = "This letter confirms the address change for the tenant as discussed today."


def _text_image(text: str) -> bytes:
    """A PNG of dark text on white, big enough for Tesseract to read."""
    from PIL import ImageDraw

    img = Image.new("L", (700, 120), 255)
    ImageDraw.Draw(img).text((20, 45), text, fill=0)
    img = img.resize((2100, 360))
    out = io.BytesIO()
    img.save(out, "PNG")
    return out.getvalue()


def _page_with_image(text: str, rect=(72, 120, 372, 170)) -> bytes:
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), LETTER, fontsize=10)
        page.insert_image(pymupdf.Rect(*rect), stream=_text_image(text))
        return doc.tobytes()


def test_text_inside_an_embedded_image_is_found_on_a_digital_page():
    data = _page_with_image("PAN ABCDE1234F")
    extraction = extract_document(data)
    assert extraction.modes == ["mixed"]
    findings = find_pii(extraction.words)
    pan = [f for f in findings if f.detection.entity_type == "PAN"]
    assert len(pan) == 1
    box = pan[0].boxes[0]
    assert 72 <= box.x0 and box.x1 <= 372 and 120 <= box.y0 and box.y1 <= 170


def test_redacting_text_in_an_image_is_verified_by_a_second_ocr_pass(tmp_path):
    data = _page_with_image("PAN ABCDE1234F")
    extraction = extract_document(data)
    boxes = _boxes(extraction)
    src = tmp_path / "in.pdf"
    out = tmp_path / "out.pdf"
    src.write_bytes(data)
    redact_pdf(src, out, boxes)
    assert verify_output(out.read_bytes(), boxes, extraction.modes) == []
    assert len(verify_output(data, boxes, extraction.modes)) > 0  # unredacted: caught
    assert not any(w.text == "ABCDE1234F" for w in extract_document(out.read_bytes()).words)


def test_an_image_without_text_leaves_the_page_digital():
    data = _page_with_image("")
    extraction = extract_document(data)
    assert extraction.modes == ["digital"]
    assert all(w.conf is None for w in extraction.words)


def test_text_already_in_the_text_layer_is_not_found_twice():
    # A "searchable scan": the image shows the text and an invisible layer repeats it.
    data = _page_with_image("PAN ABCDE1234F")
    with pymupdf.open(stream=data) as doc:
        page = doc[0]
        page.insert_text((92, 150), "PAN ABCDE1234F", fontsize=36, render_mode=3)
        data = doc.tobytes()
    extraction = extract_document(data)
    pan_words = [w for w in extraction.words if w.text == "ABCDE1234F"]
    assert len(pan_words) == 1
    assert pan_words[0].conf is None  # the text-layer copy was kept


def test_tiny_images_are_not_read(monkeypatch):
    calls = []
    import app.pipeline.document as document

    monkeypatch.setattr(document, "ocr_page", lambda *a, **k: calls.append(1) or [])
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), LETTER, fontsize=10)
        page.insert_image(pymupdf.Rect(72, 100, 82, 110), stream=_text_image("PAN"))
        data = doc.tobytes()
    assert extract_document(data).modes == ["digital"]
    assert calls == []