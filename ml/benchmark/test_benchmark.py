import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[1] / "data_gen"))

from cue_baseline import predict  # noqa: E402
from make_synthetic_ner import generate  # noqa: E402
from metrics import evaluate  # noqa: E402
from run_benchmark import chunk_text, run  # noqa: E402


def _doc(entities, lang="en", doc_type="legal"):
    return {"id": "d", "lang": lang, "doc_type": doc_type, "text": "x" * 100, "entities": entities}


def _e(label, a, b):
    return {"label": label, "start": a, "end": b}


def test_exact_match_scores_perfectly():
    gold = [_e("PERSON", 0, 10)]
    r = evaluate([_doc(gold)], {"d": gold})["by_label"]["PERSON"]
    assert (r["precision"], r["recall"], r["full_cover"], r["char_recall"]) == (1.0, 1.0, 1.0, 1.0)


def test_partly_covered_name_is_not_an_exact_hit_and_counts_as_a_leak():
    r = evaluate([_doc([_e("PERSON", 0, 10)])], {"d": [_e("PERSON", 0, 6)]})["by_label"]["PERSON"]
    assert r["recall"] == 0.0
    assert r["full_cover"] == 0.0
    assert r["char_recall"] == 0.6


def test_a_wider_prediction_covers_fully_but_loses_precision():
    r = evaluate([_doc([_e("PERSON", 2, 8)])], {"d": [_e("PERSON", 0, 10)]})["by_label"]["PERSON"]
    assert r["full_cover"] == 1.0 and r["precision"] == 0.0
    assert r["char_precision"] == 0.6


def test_any_label_ignores_which_label_was_predicted():
    res = evaluate([_doc([_e("PERSON", 0, 10)])], {"d": [_e("ORGANIZATION", 0, 10)]})
    assert res["by_label"]["PERSON"]["recall"] == 0.0
    assert res["by_label"]["ANY"]["recall"] == 1.0


def test_missing_prediction_for_a_document_means_nothing_was_found():
    r = evaluate([_doc([_e("DATE", 0, 5)])], {})["by_label"]["DATE"]
    assert r["recall"] == 0.0 and r["precision"] is None


def test_chunks_cover_the_text_exactly_and_offsets_map_back():
    text = "\n".join(f"line number {i} with some words" for i in range(60))
    chunks = chunk_text(text, limit=200)
    assert "".join(piece for _, piece in chunks) == text
    assert all(len(piece) <= 200 for _, piece in chunks)
    assert all(text[off:off + len(piece)] == piece for off, piece in chunks)


def test_a_long_line_without_breaks_is_still_split():
    text = "a" * 2000
    assert "".join(p for _, p in chunk_text(text, limit=800)) == text


def test_cue_baseline_finds_labelled_and_inline_people_and_addresses():
    text = ("Name: Ramesh Kumar\nAddress: Flat 4, Ram Nagar, Dhanbad 826001\n"
            "20/05/1995  UPI/Sunita Verma  500.00\nSigned by Mr. Amit Singh on 12 March 2020.\n")
    got = {(e["label"], text[e["start"]:e["end"]]) for e in predict(text)}
    assert ("PERSON", "Ramesh Kumar") in got
    assert ("ADDRESS", "Flat 4, Ram Nagar, Dhanbad 826001") in got
    assert ("PERSON", "Sunita Verma") in got
    assert ("PERSON", "Mr. Amit Singh") in got


def test_cue_baseline_ignores_plain_sentences():
    assert predict("The parties agree to the terms set out below.") == []


def test_run_reports_speed_and_per_threshold_results():
    docs = generate()[:6]
    report = run(docs, predict, [0.0])
    assert report["n_docs"] == 6 and "0.0" in report["results"]
    assert report["results"]["0.0"]["by_label"]["ANY"]["gold"] > 0
