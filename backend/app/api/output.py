from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.documents import _owned_document
from app.db.session import get_db
from app.models import AuditEvent, User
from app.schemas.document import DocumentOut
from app.services import storage
from app.services.redaction import clear_output, output_context, run_redaction

router = APIRouter(prefix="/documents/{document_id}", tags=["output"])


def _file_headers(disposition: str, filename: str) -> dict[str, str]:
    # Generic file names only: the original name is never stored or returned.
    return {
        "Content-Disposition": f'{disposition}; filename="{filename}"',
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    }


@router.post("/redact", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
def redact(
    document_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _owned_document(db, user, document_id)
    if document.status not in ("ready", "redacted"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Document is {document.status}")
    clear_output(db, document)  # an older output may no longer match the decisions
    document.status = "redacting"
    document.error_code = None
    db.commit()
    background_tasks.add_task(run_redaction, document.id)
    return document


@router.get("/download")
def download(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _owned_document(db, user, document_id)
    if (
        document.status != "redacted"
        or not document.output_storage_key
        or not document.output_wrapped_key
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "No redacted file available")
    data = storage.read_decrypted(
        document.output_storage_key,
        document.output_wrapped_key,
        output_context(document.id),
    )
    db.add(AuditEvent(user_id=user.id, document_id=document.id, action="download"))
    db.commit()
    return Response(
        content=data,
        media_type="application/pdf",
        headers=_file_headers("attachment", "redacted.pdf"),
    )


@router.get("/original")
def original(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _owned_document(db, user, document_id)
    if not document.storage_key or not document.wrapped_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    data = storage.read_decrypted(
        document.storage_key, document.wrapped_key, document.id
    )
    return Response(
        content=data,
        media_type="application/pdf",
        headers=_file_headers("inline", "document.pdf"),
    )
