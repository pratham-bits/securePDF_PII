from pathlib import Path

from app.pipeline.extract import extract_words
from app.pipeline.recognizers import detect_rules
from app.pipeline.validators import verhoeff_check_digit

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "sample_digital_en.pdf"
TO_DEVANAGARI = str.maketrans("0123456789", "०१२३४५६७८९")


def _valid_aadhaar() -> str:
    body = "23456789012"
    return body + verhoeff_check_digit(body)


def _group(number: str) -> str:
    return f"{number[:4]} {number[4:8]} {number[8:]}"


def _types(detections) -> list[str]:
    return [d.entity_type for d in detections]


def test_pan_detected():
    dets = detect_rules("Landlord PAN: ABCDE1234F.")
    assert _types(dets) == ["PAN"]
    assert dets[0].text == "ABCDE1234F"


def test_email_detected():
    assert _types(detect_rules("Write to rahul.verma@example.com today")) == ["EMAIL"]


def test_email_wins_over_phone_lookalike():
    assert _types(detect_rules("write9876543210@example.com")) == ["EMAIL"]


def test_indian_phone_formats():
    for text in ["Call +91 98765 43210", "Call 9876543210", "Call 98765-43210"]:
        assert _types(detect_rules(text)) == ["PHONE_IN"], text


def test_phone_must_start_with_6_to_9():
    assert detect_rules("Ref no 12345 67890") == []


def test_aadhaar_with_valid_checksum():
    dets = detect_rules(f"Aadhaar: {_group(_valid_aadhaar())}")
    assert _types(dets) == ["AADHAAR"]
    assert dets[0].checksum_ok is True
    assert dets[0].score == 0.95


def test_aadhaar_with_bad_checksum_is_kept_with_low_score():
    number = _valid_aadhaar()
    bad = number[:-1] + str((int(number[-1]) + 1) % 10)
    dets = detect_rules(f"Aadhaar: {_group(bad)}")
    assert _types(dets) == ["AADHAAR"]
    assert dets[0].checksum_ok is False
    assert dets[0].score == 0.40


def test_aadhaar_in_devanagari_digits():
    deva = _group(_valid_aadhaar()).translate(TO_DEVANAGARI)
    dets = detect_rules(f"आधार संख्या: {deva}")
    assert _types(dets) == ["AADHAAR"]
    assert dets[0].checksum_ok is True
    assert dets[0].text == deva


def test_credit_card_needs_luhn():
    assert _types(detect_rules("Card 4111 1111 1111 1111")) == ["CREDIT_CARD"]
    assert detect_rules("Card 4111 1111 1111 1112") == []


def test_sample_pdf_detects_core_entities():
    text = " ".join(w.text for w in extract_words(SAMPLE))
    found = set(_types(detect_rules(text)))
    assert {"PAN", "AADHAAR", "PHONE_IN", "EMAIL"} <= found