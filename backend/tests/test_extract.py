from pathlib import Path

from app.pipeline.extract import extract_words

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "sample_digital_en.pdf"


def test_extract_words_finds_pan_with_box():
    words = extract_words(SAMPLE)
    pan = [w for w in words if w.text == "ABCDE1234F"]
    assert len(pan) == 1
    assert pan[0].x1 > pan[0].x0
    assert pan[0].y1 > pan[0].y0