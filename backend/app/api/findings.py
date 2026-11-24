from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.documents import _owned_document
from app.db.session import get_db
from app.models import AuditEvent, Document, Finding, User
from app.schemas.finding import FindingOut, FindingUpdate, ManualBox
from app.pipeline.extract import extract_page_words, open_pdf
from app.pipeline.locate import Box, snap_box
from app.services import storage
from app.services.redaction import clear_output

router = APIRouter(prefix="/documents/{document_id}/findings", tags=["review"])

REVIEWABLE = ("ready", "redacted")
MAX_MANUAL_BOXES = 200


def _reviewable_document(db: Session, user: User, document_id: str) -> Document:
    document = _owned_document(db, user, document_id)
    if document.status not in REVIEWABLE:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Document is {document.status}")
    return document


def _finding(db: Session, document: Document, finding_id: int) -> Finding:
    finding = db.get(Finding, finding_id)
    if finding is None or finding.document_id != document.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Finding not found")
    return finding


def _discard_stale_output(db: Session, document: Document) -> None:
    """A redacted file no longer matches the decisions once they change."""
    if document.status == "redacted":
        clear_output(db, document)
        document.status = "ready"


def _snapped(document: Document, body: ManualBox) -> dict:
    """On pages with a text layer, grow the box to whole words (see snap_box)."""
    box = body.model_dump()
    modes = document.page_modes or []
    if body.page >= len(modes) or modes[body.page] not in ("digital", "mixed"):
        return box
    if document.storage_key is None or document.wrapped_key is None:
        return box
    data = storage.read_decrypted(document.storage_key, document.wrapped_key, document.id)
    with open_pdf(data) as pdf:
        words = extract_page_words(pdf[body.page], body.page)
    snapped = snap_box(Box(**box), words)
    return {"page": snapped.page, "x0": snapped.x0, "y0": snapped.y0, "x1": snapped.x1, "y1": snapped.y1}


@router.post("", response_model=FindingOut, status_code=status.HTTP_201_CREATED)
def add_manual_box(
    document_id: str,
    body: ManualBox,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _reviewable_document(db, user, document_id)
    if body.page >= document.page_count:
        raise HTTPException(422, "Page is out of range")
    manual_count = (
        db.scalar(
            select(func.count())
            .select_from(Finding)
            .where(Finding.document_id == document.id, Finding.source == "user")
        )
        or 0
    )
    if manual_count >= MAX_MANUAL_BOXES:
        raise HTTPException(status.HTTP_409_CONFLICT, "Too many manual boxes")
    finding = Finding(
        document_id=document.id,
        entity_type="MANUAL",
        tier="manual",
        score=1.0,
        source="user",
        checksum_ok=None,
        decision="redact",
        page=body.page,
        boxes=[_snapped(document, body)],
    )
    db.add(finding)
    _discard_stale_output(db, document)
    db.commit()
    return finding


@router.patch("/{finding_id}", response_model=FindingOut)
def update_decision(
    document_id: str,
    finding_id: int,
    body: FindingUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _reviewable_document(db, user, document_id)
    finding = _finding(db, document, finding_id)
    if finding.tier == "mandatory" and body.decision == "keep":
        if not body.confirm_override:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Confirmation required to keep a mandatory item",
            )
        if finding.decision != "keep":
            db.add(
                AuditEvent(
                    user_id=user.id,
                    document_id=document.id,
                    action="override_mandatory",
                    entity_type=finding.entity_type,
                )
            )
    if finding.decision != body.decision:
        _discard_stale_output(db, document)
    finding.decision = body.decision
    db.commit()
    return finding


@router.delete("/{finding_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_manual_box(
    document_id: str,
    finding_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _reviewable_document(db, user, document_id)
    finding = _finding(db, document, finding_id)
    if finding.source != "user":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only manual boxes can be deleted; set the decision to keep instead",
        )
    db.delete(finding)
    _discard_stale_output(db, document)
    db.commit()