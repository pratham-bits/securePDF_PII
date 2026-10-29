import io
from pathlib import Path

import pymupdf
from PIL import Image, ImageStat

from app.pipeline.document import (
    Extraction,
    extract_document,
    inside_fraction,
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
    assert inside_fraction(label, box) < 0.5
    assert inside_fraction(leaked, box) >= 0.5