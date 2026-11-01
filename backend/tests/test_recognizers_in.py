from pathlib import Path

from app.pipeline.extract import extract_words
from app.pipeline.recognizers import detect_rules

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "sample_digital_en.pdf"


def _types(text):
    return [d.entity_type for d in detect_rules(text)]


def test_bank_account_needs_a_label():
    assert _types("Bank account: 123456789012") == ["BANK_ACCOUNT"]
    assert _types("A/c No. 9876543210") == ["BANK_ACCOUNT"]  # beats the phone detector
    assert _types("Order id 123456789012") == []


def test_bank_account_in_hindi_with_devanagari_digits():
    detections = detect_rules("खाता संख्या: १२३४५६७८९०१२")
    assert [d.entity_type for d in detections] == ["BANK_ACCOUNT"]
    assert detections[0].text == "१२३४५६७८९०१२"


def test_ifsc_code():
    assert _types("IFSC: SBIN0001234") == ["IFSC"]


def test_passport_score_depends_on_context():
    near = detect_rules("Passport No: K1234567")[0]
    far = detect_rules("Ref K1234567")[0]
    assert near.entity_type == far.entity_type == "PASSPORT_IN"
    assert near.score == 0.90
    assert far.score == 0.45


def test_voter_id_score_depends_on_context():
    near = detect_rules("Voter ID: ABC1234567")[0]
    far = detect_rules("Code ABC1234567")[0]
    assert near.entity_type == far.entity_type == "VOTER_ID"
    assert near.score == 0.90
    assert far.score == 0.40


def test_driving_licence():
    detections = detect_rules("DL No: MH14 20110062821")
    assert [d.entity_type for d in detections] == ["DRIVING_LICENCE"]
    assert detections[0].score == 0.92


def test_gstin_checksum():
    valid = detect_rules("GSTIN 27AAPFU0939F1ZV")
    invalid = detect_rules("GSTIN 27AAPFU0939F1ZW")
    assert [d.entity_type for d in valid] == ["GSTIN"]  # no separate PAN inside it
    assert valid[0].checksum_ok is True and valid[0].score == 0.95
    assert invalid[0].checksum_ok is False and invalid[0].score == 0.50


def test_upi_id_is_not_confused_with_email():
    assert detect_rules("Pay rahul@okaxis")[0].entity_type == "UPI_ID"
    assert detect_rules("Pay rahul@okaxis")[0].score == 0.90
    assert detect_rules("Pay foo@somebank")[0].score == 0.50
    assert _types("Write to rahul@example.com") == ["EMAIL"]


def test_vehicle_registration_formats():
    assert _types("Vehicle MH12AB1234") == ["VEHICLE_REG"]
    assert _types("Vehicle MH 12 AB 1234") == ["VEHICLE_REG"]


def test_aadhaar_vid_needs_its_label():
    detections = detect_rules("VID: 1234 5678 9012 3456")
    assert [d.entity_type for d in detections] == ["AADHAAR_VID"]
    assert detections[0].text == "1234 5678 9012 3456"


def test_date_of_birth_needs_its_label():
    assert _types("DOB: 05/03/1990") == ["DATE_OF_BIRTH"]
    assert _types("Date of Birth: 5 March 1990") == ["DATE_OF_BIRTH"]
    assert _types("जन्म तिथि: 05-03-1990") == ["DATE_OF_BIRTH"]
    assert _types("Signed on 05/03/1990") == []


def test_sample_pdf_now_yields_all_planted_entities():
    text = " ".join(w.text for w in extract_words(SAMPLE))
    found = {d.entity_type for d in detect_rules(text)}
    assert found == {"PAN", "AADHAAR", "PHONE_IN", "EMAIL", "BANK_ACCOUNT", "IFSC"}