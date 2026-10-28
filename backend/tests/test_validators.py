from app.pipeline.validators import luhn_valid, verhoeff_check_digit, verhoeff_valid


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