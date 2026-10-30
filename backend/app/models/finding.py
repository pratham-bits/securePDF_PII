from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Finding(Base):
    """One detected item. Metadata only: there is deliberately no column for the text."""

    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    entity_type: Mapped[str] = mapped_column(String(32))
    tier: Mapped[str] = mapped_column(String(16))
    score: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(16))
    checksum_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    decision: Mapped[str] = mapped_column(String(8))
    page: Mapped[int] = mapped_column(Integer)
    boxes: Mapped[list] = mapped_column(JSON)