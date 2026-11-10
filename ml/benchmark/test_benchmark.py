import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[1] / "data_gen"))

from analyze_misses import classify  # noqa: E402
from cue_baseline import predict  # noqa: E402
from make_synthetic_ner import generate  # noqa: E402
from metrics import evaluate  # noqa: E402
from postprocess import merge  # noqa: E402
from run_benchmark import chunk_text, dump_predictions, load, run, variant_spans  # noqa: E402


def _doc(entities, lang="en", doc_type="legal"):
    return {"id": "d", "lang": lang, "doc_type": doc_type, "text": "x" * 100, "entities": entities}


def _e(label, a, b):
    return {"label": label, "start": a, "end": b}


def _s(label, a, b, score=0.9):
    return {"label": label, "start": a, "end": b, "score": score}


# --- metrics ------------------------------------------------------------------------

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


# --- chunking and cue baseline -----------------------------------------------------

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


# --- post-processing ----------------------------------------------------------------

def test_address_fragments_separated_by_commas_are_joined():
    text = "Flat 4B, Shanti Nagar, Dhanbad 826004"
    pieces = [_s("ADDRESS", 0, 7), _s("ADDRESS", 9, 21), _s("ADDRESS", 23, 37)]
    [joined] = merge(pieces, text)
    assert text[joined["start"]:joined["end"]] == text


def test_two_people_in_a_list_are_not_merged_across_a_comma():
    text = "Ramesh Kumar, Sunita Verma"
    result = merge([_s("PERSON", 0, 12), _s("PERSON", 14, 26)], text)
    assert len(result) == 2


def test_name_fragments_split_by_one_space_are_joined():
    text = "Ramesh Kumar"
    [joined] = merge([_s("PERSON", 0, 6), _s("PERSON", 7, 12)], text)
    assert (joined["start"], joined["end"]) == (0, 12)


def test_pieces_on_different_lines_or_with_different_labels_stay_apart():
    text = "Dhanbad\nRanchi"
    assert len(merge([_s("ADDRESS", 0, 7), _s("ADDRESS", 8, 14)], text)) == 2
    assert len(merge([_s("PERSON", 0, 7), _s("ADDRESS", 0, 7)], text)) == 2


def test_overlapping_same_label_spans_become_one_with_the_best_score():
    [joined] = merge([_s("DATE", 0, 8, 0.4), _s("DATE", 5, 12, 0.9)], "x" * 20)
    assert (joined["start"], joined["end"], joined["score"]) == (0, 12, 0.9)


def test_merged_plus_cue_adds_cue_findings_the_model_missed():
    text = "Name: Ramesh Kumar\n"
    assert variant_spans(text, [], "raw") == []
    got = variant_spans(text, [], "merged+cue")
    assert [(e["label"], text[e["start"]:e["end"]]) for e in got] == [("PERSON", "Ramesh Kumar")]


def test_merging_repairs_a_model_that_returns_addresses_in_pieces():
    docs = generate()[:60]
    gold = {d["id"]: [e for e in d["entities"] if e["label"] == "ADDRESS"] for d in docs}

    def fragmenting_model(text):
        """Pretend model: finds every address, but one comma-separated piece at a time."""
        doc = next(d for d in docs if d["text"] == text)
        out = []
        for e in gold[doc["id"]]:
            pos = e["start"]
            for piece in e["text"].split(", "):
                out.append(_s("ADDRESS", pos, pos + len(piece)))
                pos += len(piece) + 2
        return out

    report = run(docs, fragmenting_model, [0.5], ("raw", "merged"))
    raw = report["results"]["0.5|raw"]["by_label"]["ADDRESS"]
    merged = report["results"]["0.5|merged"]["by_label"]["ADDRESS"]
    assert raw["full_cover"] == 0.0 or raw["full_cover"] < 0.2
    assert merged["full_cover"] == 1.0


# --- miss analysis ------------------------------------------------------------------

def test_classify_covers_each_kind_of_failure():
    gold = {"label": "PERSON", "start": 10, "end": 20}
    assert classify(gold, [_s("PERSON", 8, 22)]) == "covered"
    assert classify(gold, [_s("PERSON", 10, 15)]) == "partial"
    assert classify(gold, [_s("ORGANIZATION", 10, 20)]) == "wrong_label"
    assert classify(gold, [_s("ORGANIZATION", 10, 15)]) == "wrong_label_partial"
    assert classify(gold, [_s("PERSON", 30, 40)]) == "missed"


# --- run and dump -------------------------------------------------------------------

def test_run_reports_speed_and_one_result_per_threshold_and_variant():
    docs = generate()[:6]
    report = run(docs, predict, [0.0, 0.5], ("raw", "merged"))
    assert report["n_docs"] == 6
    assert set(report["results"]) == {"0.0|raw", "0.0|merged", "0.5|raw", "0.5|merged"}
    assert report["results"]["0.0|raw"]["by_label"]["ANY"]["gold"] > 0


def test_dumped_predictions_contain_no_document_text(tmp_path):
    docs = generate()[:3]
    report = run(docs, predict, [0.0])
    path = tmp_path / "preds.jsonl"
    dump_predictions(path, report["raw_predictions"])
    content = path.read_text(encoding="utf-8")
    assert all(d["text"][:20] not in content for d in docs)
    assert len(load(path)) == 3
