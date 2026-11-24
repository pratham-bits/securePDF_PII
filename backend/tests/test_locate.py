from pathlib import Path

from app.pipeline.extract import Word, extract_words
from app.pipeline.locate import Box, build_text, find_pii, snap_box

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "sample_digital_en.pdf"


def _w(text: str, x0: float = 0.0, page: int = 0) -> Word:
    return Word(page, text, x0, 0.0, x0 + 10.0, 10.0)


def test_build_text_spans_point_at_each_word():
    words = [_w("Hello"), _w("big", 20), _w("world", 40)]
    text, spans = build_text(words)
    assert text == "Hello big world"
    assert [text[s:e] for s, e in spans] == ["Hello", "big", "world"]


def test_pan_box_matches_its_word_box():
    words = extract_words(SAMPLE)
    findings = find_pii(words)
    pan = next(f for f in findings if f.detection.entity_type == "PAN")
    target = next(w for w in words if w.text == "ABCDE1234F")
    assert len(pan.boxes) == 1
    box = pan.boxes[0]
    assert (box.page, box.x0, box.y0, box.x1, box.y1) == (
        target.page, target.x0, target.y0, target.x1, target.y1,
    )


def test_multi_word_phone_gets_one_box_per_word():
    findings = find_pii(extract_words(SAMPLE))
    phone = next(f for f in findings if f.detection.entity_type == "PHONE_IN")
    assert len(phone.boxes) == 3
    xs = [b.x0 for b in phone.boxes]
    ys = [b.y0 for b in phone.boxes]
    assert xs == sorted(xs)
    assert max(ys) - min(ys) < 1


def test_partial_word_match_redacts_the_whole_word():
    words = [Word(0, "PAN:ABCDE1234F", 10.0, 10.0, 100.0, 20.0)]
    findings = find_pii(words)
    assert [f.detection.entity_type for f in findings] == ["PAN"]
    box = findings[0].boxes[0]
    assert (box.x0, box.x1) == (10.0, 100.0)


def test_every_finding_has_at_least_one_box():
    findings = find_pii(extract_words(SAMPLE))
    assert findings
    assert all(f.boxes for f in findings)


def test_snap_box_grows_to_cover_whole_words_it_touches():
    words = [_w("Rajesh", 0), _w("Kumar", 30)]  # 10pt wide each
    snapped = snap_box(Box(0, 4, 2, 6, 8), words)
    assert (snapped.x0, snapped.x1) == (0, 10)


def test_snap_box_leaves_untouched_words_and_other_pages_alone():
    words = [_w("a", 0), _w("b", 50), _w("c", 3, page=1)]
    snapped = snap_box(Box(0, 1, 1, 9, 9), words)
    assert (snapped.x0, snapped.x1) == (0, 10)


def test_snap_box_never_shrinks_a_box_with_no_words_under_it():
    box = Box(0, 100, 100, 150, 120)
    assert snap_box(box, [_w("a", 0)]) == box