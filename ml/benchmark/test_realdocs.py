import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import realdocs  # noqa: E402
from realdocs import (  # noqa: E402
    build_row, cmd_build, cmd_extract, find_fuzzy, find_occurrences, guess_lang, parse_labels, words_to_text,
)


def _w(text, x0, y0, x1=None, y1=None, page=0):
    return SimpleNamespace(page=page, text=text, x0=x0, y0=y0, x1=x1 or x0 + 40, y1=y1 or y0 + 10)


# --- text ---------------------------------------------------------------------------

def test_words_on_one_row_share_a_line_and_a_new_row_starts_a_new_line():
    words = [_w("Name:", 10, 100), _w("Ramesh", 60, 101), _w("Kumar", 110, 100), _w("Address:", 10, 120)]
    text, spans = words_to_text(words)
    assert text == "Name: Ramesh Kumar\nAddress:"
    assert all(text[a:b] == w.text for (a, b), w in zip(spans, words))


def test_a_new_page_always_starts_a_new_line():
    text, _ = words_to_text([_w("end", 10, 100), _w("start", 10, 100, page=1)])
    assert text == "end\nstart"


def test_slightly_misaligned_words_stay_on_the_same_line():
    text, _ = words_to_text([_w("A", 10, 100, y1=110), _w("B", 60, 103, y1=113)])
    assert text == "A B"


# --- labels -------------------------------------------------------------------------

LABELS_TXT = """
# comment
== legal_01 | legal
PERSON: Ramesh Kumar ; Sunita Verma
ADDRESS: Flat 4, Shanti Nagar, Dhanbad 826004
== id_01 | id_card | hi
NONE
"""


def test_labels_file_is_parsed_into_blocks():
    legal, idcard = parse_labels(LABELS_TXT)
    assert legal["name"] == "legal_01" and legal["doc_type"] == "legal" and legal["lang"] is None
    assert legal["labels"]["PERSON"] == ["Ramesh Kumar", "Sunita Verma"]
    assert legal["labels"]["ADDRESS"] == ["Flat 4, Shanti Nagar, Dhanbad 826004"]
    assert idcard["none"] is True and idcard["lang"] == "hi"


def test_an_unknown_label_or_a_missing_header_is_an_error_with_a_line_number():
    with pytest.raises(ValueError, match="line 2"):
        parse_labels("== a | legal\nCOLOUR: red")
    with pytest.raises(ValueError, match="header"):
        parse_labels("PERSON: x")


def test_every_occurrence_is_found_including_across_a_line_break():
    text = "Ramesh Kumar signed. Later Ramesh\nKumar paid. Ramesh Kumarsingh left."
    hits = find_occurrences(text, "Ramesh Kumar")
    assert [text[a:b].replace("\n", " ") for a, b in hits] == ["Ramesh Kumar", "Ramesh Kumar"]


def test_devanagari_names_are_matched_whole_words_only():
    text = "श्री मनोज दास आए। मनोज दासगुप्ता भी।"
    assert len(find_occurrences(text, "मनोज दास")) == 1


def test_language_guess():
    assert guess_lang("Ramesh Kumar signed") == "en"
    assert guess_lang("रमेश कुमार ने हस्ताक्षर किए") == "hi"
    assert guess_lang("12345") == "en"


def test_build_row_labels_every_mention_and_reports_strings_it_could_not_find():
    block = parse_labels("== d | legal\nPERSON: Ramesh Kumar ; Missing Person")[0]
    text = "Ramesh Kumar met Ramesh Kumar."
    row, problems = build_row(block, text)
    assert row is not None
    assert [(e["label"], e["text"]) for e in row["entities"]] == [("PERSON", "Ramesh Kumar")] * 2
    assert len(problems) == 1 and "Missing Person" in problems[0]


def test_a_shorter_value_inside_a_longer_one_of_the_same_label_is_dropped():
    block = parse_labels("== d | legal\nPERSON: Ramesh ; Ramesh Kumar")[0]
    row, _ = build_row(block, "Ramesh Kumar")
    assert row is not None
    assert [e["text"] for e in row["entities"]] == ["Ramesh Kumar"]


def test_a_document_with_no_labels_is_skipped_unless_marked_none():
    skipped, problems = build_row(parse_labels("== d | legal\nPERSON: ")[0], "text")
    assert skipped is None and "skipped" in problems[0]
    row, _ = build_row(parse_labels("== d | legal\nNONE")[0], "text")
    assert row is not None
    assert row["entities"] == []


# --- commands -----------------------------------------------------------------------

def test_extract_writes_text_and_a_template_without_overwriting_existing_labels(tmp_path):
    for name in ("legal_01", "bank_02"):
        (tmp_path / f"{name}.pdf").write_bytes(b"%PDF")
    cmd_extract(tmp_path, extractor=lambda path, lang: f"text of {Path(path).stem}")
    labels = (tmp_path / "labels.txt").read_text(encoding="utf-8")
    assert "== legal_01 | legal" in labels and "== bank_02 | bank_statement" in labels
    assert (tmp_path / "text" / "legal_01.txt").read_text(encoding="utf-8") == "text of legal_01"
    (tmp_path / "labels.txt").write_text(labels.replace("PERSON: \n", "PERSON: Ramesh\n", 1), encoding="utf-8")
    cmd_extract(tmp_path, extractor=lambda path, lang: "x")
    assert "PERSON: Ramesh" in (tmp_path / "labels.txt").read_text(encoding="utf-8")


def test_build_writes_a_dataset_in_the_benchmark_format(tmp_path):
    (tmp_path / "text").mkdir()
    (tmp_path / "text" / "legal_01.txt").write_text("Signed by Ramesh Kumar on 12 March 2024.", encoding="utf-8")
    (tmp_path / "labels.txt").write_text("== legal_01 | legal\nPERSON: Ramesh Kumar\nDATE: 12 March 2024\n", encoding="utf-8")
    rows, problems = cmd_build(tmp_path)
    assert problems == []
    saved = [json.loads(l) for l in (tmp_path / "real_v1.jsonl").read_text(encoding="utf-8").splitlines()]
    assert saved == rows and saved[0]["id"] == "real-legal_01"
    for e in saved[0]["entities"]:
        assert saved[0]["text"][e["start"]:e["end"]] == e["text"]


def test_the_dataset_runs_through_the_benchmark_scoring(tmp_path):
    from metrics import evaluate

    (tmp_path / "text").mkdir()
    (tmp_path / "text" / "id_01.txt").write_text("Name: Ramesh Kumar\n", encoding="utf-8")
    (tmp_path / "labels.txt").write_text("== id_01 | id_card\nPERSON: Ramesh Kumar\n", encoding="utf-8")
    rows, _ = cmd_build(tmp_path)
    from cue_baseline import predict

    preds = {rows[0]["id"]: predict(rows[0]["text"])}
    assert evaluate(rows, preds)["by_label"]["PERSON"]["full_cover"] == 1.0


def test_real_extraction_of_a_digital_sample_keeps_line_structure():
    sample = realdocs.REPO / "samples" / "sample_digital_en.pdf"
    if not sample.exists():
        pytest.skip("sample PDF not present")
    text = realdocs.extract_pdf(sample)
    assert len(text) > 50 and "\n" in text


# --- fuzzy matching for OCR-garbled copies -------------------------------------------

def test_a_name_garbled_by_ocr_is_still_matched():
    text = "Signed by Rahul Verrna on the date above."
    [(a, b)] = find_fuzzy(text, "Rahul Verma")
    assert text[a:b] == "Rahul Verrna"


def test_a_different_person_with_a_similar_name_is_not_matched():
    assert find_fuzzy("Rahul Sharma signed.", "Rahul Verma") == []


def test_short_values_must_match_exactly():
    assert find_fuzzy("Neha Das and Neha Dar", "Neha Dag") == []


def test_fuzzy_matches_never_overlap_exact_hits():
    text = "Rahul Verma met Rahul Verrna."
    exact = find_occurrences(text, "Rahul Verma")
    assert [text[a:b] for a, b in find_fuzzy(text, "Rahul Verma", taken=exact)] == ["Rahul Verrna"]


def test_build_row_counts_fuzzy_entities_and_does_not_report_them_as_missing():
    block = parse_labels("== d | legal\nPERSON: Rahul Verma")[0]
    row, problems = build_row(block, "Signed Rahul Verrna today.")
    assert row is not None
    assert problems == [] and row["fuzzy_entities"] == 1
    assert [e["text"] for e in row["entities"]] == ["Rahul Verrna"]
