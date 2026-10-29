from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC time: the convention for every DateTime column in this project."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
    