from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.documents import _owned_document
from app.db.session import get_db
from app.models import AuditEvent, Document, Finding, User
from app.schemas.finding import FindingOut, FindingUpdate, ManualBox

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


@router.get("", response_model=list[FindingOut])
def list_findings(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _reviewable_document(db, user, document_id)
    stmt = (
        select(Finding)
        .where(Finding.document_id == document.id)
        .order_by(Finding.page, Finding.id)
    )
    return list(db.scalars(stmt))


@router.post("", response_model=FindingOut, status_code=status.HTTP_201_CREATED)
def add_manual_box(
    document_id: str,
    body: ManualBox,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _reviewable_document(db, user, document_id)
    if body.page >= document.page_count:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Page is out of range")
    manual_count = db.scalar(
        select(func.count())
        .select_from(Finding)
        .where(Finding.document_id == document.id, Finding.source == "user")
    ) or 0
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
        boxes=[body.model_dump()],
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)
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
    previous_decision = finding.decision
    if body.decision == previous_decision:
        return finding

    if finding.tier == "mandatory" and body.decision == "keep":
        if not body.confirm_override:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Overriding a mandatory finding requires confirmation",
            )
        db.add(
            AuditEvent(
                user_id=user.id,
                document_id=document.id,
                action="override_mandatory",
                entity_type=finding.entity_type,
            )
        )

    finding.decision = body.decision
    db.commit()
    db.refresh(finding)
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
            status.HTTP_409_CONFLICT, "Only manually added boxes can be deleted"
        )
    db.delete(finding)
    db.commit()
