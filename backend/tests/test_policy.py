from app.pipeline.policy import default_decision, tier_for


def test_government_ids_and_card_numbers_are_mandatory():
    for entity in ("AADHAAR", "PAN", "CREDIT_CARD"):
        assert tier_for(entity) == "mandatory"
        assert default_decision("mandatory") == "redact"


def test_contact_details_are_recommended():
    for entity in ("EMAIL", "PHONE_IN"):
        assert tier_for(entity) == "recommended"
    assert default_decision("recommended") == "redact"


def test_optional_entities_are_kept_and_unknown_ones_are_redacted():
    assert tier_for("ORGANIZATION") == "optional"
    assert default_decision("optional") == "keep"
    assert tier_for("SOMETHING_NEW") == "recommended"

def test_expansion_pack_tiers():
    for entity in ("BANK_ACCOUNT", "PASSPORT_IN", "VOTER_ID", "DRIVING_LICENCE", "AADHAAR_VID"):
        assert tier_for(entity) == "mandatory"
    for entity in ("IFSC", "GSTIN", "UPI_ID", "VEHICLE_REG", "DATE_OF_BIRTH"):
        assert tier_for(entity) == "recommended"