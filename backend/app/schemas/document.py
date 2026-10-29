from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, field_serializer


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    page_count: int
    size_bytes: int
    created_at: datetime
    expires_at: datetime

    @field_serializer("created_at", "expires_at")
    def _as_utc(self, value: datetime) -> str:
        return value.replace(tzinfo=timezone.utc).isoformat()