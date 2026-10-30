MANDATORY = {"AADHAAR", "PAN", "CREDIT_CARD"}
OPTIONAL = {"ORGANIZATION", "LOCATION", "DATE"}  # used once the ML model arrives


def tier_for(entity_type: str) -> str:
    if entity_type in MANDATORY:
        return "mandatory"
    if entity_type in OPTIONAL:
        return "optional"
    return "recommended"  # also the safe default for entity types we don't know yet


def default_decision(tier: str) -> str:
    return "keep" if tier == "optional" else "redact"