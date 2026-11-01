from app.pipeline.validators import luhn_valid, verhoeff_check_digit, verhoeff_valid

from app.pipeline.validators import gstin_check_char, gstin_valid


def test_gstin_known_vector():
    assert gstin_check_char("27AAPFU0939F1Z") == "V"
    assert gstin_valid("27AAPFU0939F1ZV")
    assert not gstin_valid("27AAPFU0939F1ZW")

def test_verhoeff_known_vector():
    assert verhoeff_check_digit("236") == "3"
    assert verhoeff_valid("2363")


def test_verhoeff_detects_single_digit_error():
    assert not verhoeff_valid("2364")


def test_verhoeff_roundtrip_for_aadhaar_like_number():
    body = "23456789012"
    assert verhoeff_valid(body + verhoeff_check_digit(body))


def test_luhn_valid_and_invalid():
    assert luhn_valid("4111111111111111")
    assert not luhn_valid("4111111111111112")