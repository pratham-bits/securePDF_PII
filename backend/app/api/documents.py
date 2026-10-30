import uuid
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.clock import utcnow
from app.core.config import settings
from app.db.session import get_db
from app.models import Document, User,Finding
from app.schemas.document import DocumentOut
from app.services import storage
from app.services.pdf_validation import InvalidPdf, validate_pdf
from app.services.retention import HIDDEN_STATUSES, purge_document
from app.schemas.finding import FindingOut
from app.services.analysis import run_analysis

router = APIRouter(prefix="/documents", tags=["documents"])


def _owned_document(db: Session, user: User, document_id: str) -> Document:
    document = db.get(Document, document_id)
    # Someone else's document, a deleted one and a missing one all look the same.
    if (
        document is None
        or document.user_id != user.id
        or document.status in HIDDEN_STATUSES
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return document


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # file.filename and file.content_type are never used: the client controls them.
    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)
    try:
        page_count = validate_pdf(data, max_bytes, settings.max_pages)
    except InvalidPdf as exc:
        raise HTTPException(exc.status_code, exc.message)

    document_id = str(uuid.uuid4())
    storage_key, wrapped_key = storage.save_encrypted(data, document_id)
    now = utcnow()
    document = Document(
        id=document_id,
        user_id=user.id,
        page_count=page_count,
        size_bytes=len(data),
        storage_key=storage_key,
        wrapped_key=wrapped_key,
        created_at=now,
        expires_at=now + timedelta(hours=settings.retention_hours),
    )
    db.add(document)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete_file(storage_key)  # never leave an orphan file behind
        raise
    return document


@router.get("", response_model=list[DocumentOut])
def list_documents(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    stmt = (
        select(Document)
        .where(Document.user_id == user.id, Document.status.not_in(HIDDEN_STATUSES))
        .order_by(Document.created_at.desc())
    )
    return list(db.scalars(stmt))


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _owned_document(db, user, document_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    purge_document(db, _owned_document(db, user, document_id), "deleted")

@router.post(
    "/{document_id}/analyze",
    response_model=DocumentOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def analyze(
    document_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _owned_document(db, user, document_id)
    if document.status not in ("uploaded", "failed"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Document is {document.status}")
    document.status = "analyzing"
    document.error_code = None
    db.commit()
    background_tasks.add_task(run_analysis, document.id)
    return document


@router.get("/{document_id}/findings", response_model=list[FindingOut])
def list_findings(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _owned_document(db, user, document_id)
    stmt = (
        select(Finding)
        .where(Finding.document_id == document.id)
        .order_by(Finding.page, Finding.id)
    )
    return list(db.scalars(stmt))