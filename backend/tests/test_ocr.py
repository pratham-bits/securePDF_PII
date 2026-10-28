from difflib import SequenceMatcher
from pathlib import Path

import pymupdf

from app.pipeline.extract import extract_words
from app.pipeline.locate import find_pii
from app.pipeline.ocr import extract_words_ocr

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
DIGITAL = SAMPLES / "sample_digital_en.pdf"
SCANNED = SAMPLES / "sample_scanned_en.pdf"


def test_scanned_sample_has_no_text_layer():
    with pymupdf.open(SCANNED) as doc:
        text = doc[0].get_text()
        assert isinstance(text, str)
        assert text.strip() == ""


def test_ocr_text_is_close_to_the_digital_text():
    ocr_text = " ".join(w.text for w in extract_words_ocr(SCANNED))
    true_text = " ".join(w.text for w in extract_words(DIGITAL))
    assert SequenceMatcher(None, ocr_text, true_text).ratio() >= 0.9


def test_ocr_boxes_are_in_pdf_points():
    truth = next(w for w in extract_words(DIGITAL) if w.text == "AGREEMENT")
    found = next(w for w in extract_words_ocr(SCANNED) if w.text == "AGREEMENT")
    truth_center = ((truth.x0 + truth.x1) / 2, (truth.y0 + truth.y1) / 2)
    found_center = ((found.x0 + found.x1) / 2, (found.y0 + found.y1) / 2)
    assert abs(truth_center[0] - found_center[0]) < 15
    assert abs(truth_center[1] - found_center[1]) < 15


def test_find_pii_works_on_ocr_words():
    findings = find_pii(extract_words_ocr(SCANNED))
    found = {f.detection.entity_type for f in findings}
    assert {"PAN", "PHONE_IN", "EMAIL"} <= found
