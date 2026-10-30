from pydantic import BaseModel, ConfigDict


class BoxOut(BaseModel):
    page: int
    x0: float
    y0: float
    x1: float
    y1: float


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    tier: str
    score: float
    source: str
    checksum_ok: bool | None
    decision: str
    page: int
    boxes: list[BoxOut]