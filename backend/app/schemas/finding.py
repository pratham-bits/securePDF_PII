from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class FindingUpdate(BaseModel):
    decision: Literal["redact", "keep"]
    confirm_override: bool = False


class ManualBox(BaseModel):
    page: int = Field(ge=0)
    x0: float = Field(ge=0, le=14400)
    y0: float = Field(ge=0, le=14400)
    x1: float = Field(ge=0, le=14400)
    y1: float = Field(ge=0, le=14400)

    @model_validator(mode="after")
    def _check_size(self):
        if self.x1 - self.x0 < 2 or self.y1 - self.y0 < 2:
            raise ValueError("box is too small")
        return self