import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from make_synthetic_ner import generate  # noqa: E402


def test_every_span_matches_the_text_it_points_at():
    for doc in generate():
        for e in doc["entities"]:
            assert doc["text"][e["start"]:e["end"]] == e["text"], doc["id"]


def test_spans_never_overlap_and_are_in_order():
    for doc in generate():
        spans = [(e["start"], e["end"]) for e in doc["entities"]]
        assert spans == sorted(spans), doc["id"]
        assert all(a[1] <= b[0] for a, b in zip(spans, spans[1:])), doc["id"]


def test_generation_is_repeatable():
    assert generate() == generate()


def test_all_labels_languages_and_doc_types_are_present():
    docs = generate()
    assert {e["label"] for d in docs for e in d["entities"]} == {"PERSON", "ADDRESS", "ORGANIZATION", "DATE"}
    assert {d["lang"] for d in docs} == {"en", "hi"}
    assert {d["doc_type"] for d in docs} == {"legal", "id_card", "bank_statement"}


def test_hindi_documents_contain_devanagari_names():
    hindi = [d for d in generate() if d["lang"] == "hi"]
    persons = [e["text"] for d in hindi for e in d["entities"] if e["label"] == "PERSON"]
    assert all(any("ऀ" <= ch <= "ॿ" for ch in p) for p in persons)