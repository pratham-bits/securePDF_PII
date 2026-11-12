import random
import sys
import unicodedata
from pathlib import Path

import pymupdf
import pytest

sys.path.insert(0, str(Path(__file__).parent))

from make_realistic_docs import degrade, find_font, generate, render_digital, to_scan  # noqa: E402
from realistic_docs import DOCS, split_markers  # noqa: E402


def test_there_are_32_documents_of_every_type_and_both_languages():
    assert len(DOCS) == 32
    assert {d.doc_type for d in DOCS} == {"legal", "id_card", "bank_statement"}
    assert {d.lang for d in DOCS} == {"en", "hi"}
    assert all(d.name.startswith(("legal_", "id_", "bank_")) for d in DOCS)


def test_markers_are_clean_and_every_document_has_labelled_entities():
    for d in DOCS:
        clean, entities = split_markers(d.html)
        assert "[[" not in clean and "]]" not in clean, d.name
        assert entities, d.name
        assert all(";" not in value for _, value in entities), d.name


def test_all_four_labels_are_present_overall():
    labels = {l for d in DOCS for l, _ in split_markers(d.html)[1]}
    assert labels == {"PERSON", "ADDRESS", "ORGANIZATION", "DATE"}


def test_honorifics_are_left_outside_the_markers():
    entities = [v for d in DOCS for _, v in split_markers(d.html)[1]]
    assert not any(v.startswith(("Mr.", "Ms.", "Mrs.", "श्री", "श्रीमती")) for v in entities)


def test_digital_english_documents_keep_every_entity_in_their_text_layer():
    missing = []
    for d in DOCS:
        if d.scan or d.lang != "en":
            continue
        html, entities = split_markers(d.html)
        doc = render_digital(html, hindi=False, font_dir=".")
        text = unicodedata.normalize("NFKC", " ".join(str(doc[0].get_text()).split()))
        missing += [(d.name, v) for _, v in entities if v not in text]
    assert not missing, missing[:5]


def test_a_scan_is_an_image_only_page():
    d = next(x for x in DOCS if x.name == "legal_03")
    scan = to_scan(render_digital(split_markers(d.html)[0], False, "."), seed="legal_03")
    assert str(scan[0].get_text()).strip() == ""
    assert len(scan[0].get_images()) == 1


def test_degrading_is_repeatable_for_the_same_seed():
    d = next(x for x in DOCS if x.name == "bank_06")
    page = render_digital(split_markers(d.html)[0], False, ".")[0]
    assert degrade(page, random.Random("x")) == degrade(page, random.Random("x"))


def test_generate_writes_pdfs_and_a_labels_file_that_names_every_document(tmp_path):
    written, skipped = generate(tmp_path, font=None, force=True)
    labels = (tmp_path / "labels.txt").read_text(encoding="utf-8")
    pdfs = {p.stem for p in tmp_path.glob("*.pdf")}
    assert written == len(pdfs)
    assert all(f"== {name} |" in labels for name in pdfs)
    if not find_font(None):
        assert len(skipped) == sum(d.lang == "hi" for d in DOCS)


def test_generate_refuses_to_overwrite_existing_labels(tmp_path):
    (tmp_path / "labels.txt").write_text("mine", encoding="utf-8")
    with pytest.raises(SystemExit):
        generate(tmp_path, font=None)
    assert (tmp_path / "labels.txt").read_text(encoding="utf-8") == "mine"
