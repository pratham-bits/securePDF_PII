import logging

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Document, Finding
from app.pipeline.document import verify_output
from app.pipeline.locate import Box
from app.pipeline.redact import redact_bytes
from app.services import storage
from app.services.jobs import slots

logger = logging.getLogger("uvicorn.error")


def output_context(document_id: str) -> str:
    """Bound into the encryption, so an output cannot be swapped with the original."""
    return f"{document_id}:output"


def clear_output(db: Session, document: Document) -> None:
    """Erase a previous redacted output: key first, then the file."""
    key = document.output_storage_key
    document.output_storage_key = None
    document.output_wrapped_key = None
    db.commit()
    if key:
        storage.delete_file(key)


def _fail(db: Session, document_id: str, code: str) -> None:
    document = db.get(Document, document_id)  # reload after any rollback
    if document is not None and document.status == "redacting":
        document.status = "ready"
        document.error_code = code
        db.commit()


def redact_document(db: Session, document: Document) -> None:
    """Apply the reviewed decisions, verify the result, and store it encrypted.

    The caller sets the status to "redacting" first. An output is stored only
    if verification passes; otherwise the document returns to "ready".
    """
    document_id = document.id
    try:
        if document.storage_key is None or document.wrapped_key is None:
            raise ValueError(f"Document {document_id} is missing storage or encryption keys")

        data = storage.read_decrypted(
            document.storage_key, document.wrapped_key, document_id
        )
        findings = db.scalars(
            select(Finding).where(
                Finding.document_id == document_id, Finding.decision == "redact"
            )
        )
        boxes = [Box(**box) for finding in findings for box in finding.boxes]
        modes = list(document.page_modes or [])

        output = redact_bytes(data, boxes)
        leaks = verify_output(output, boxes, modes, lang=settings.ocr_languages)
        if leaks:
            db.rollback()
            logger.error("redaction verification failed: %d box(es)", len(leaks))
            _fail(db, document_id, "verification_failed")
            return

        db.refresh(document)
        if document.status != "redacting":  # deleted or expired while we worked
            return
        key, wrapped = storage.save_encrypted(output, output_context(document_id))
        document.output_storage_key = key
        document.output_wrapped_key = wrapped
        document.error_code = None
        document.status = "redacted"
        db.commit()
    except Exception as exc:
        db.rollback()
        # The error type only: messages could contain document content.
        logger.error("redaction failed: %s", type(exc).__name__)
        _fail(db, document_id, "redaction_error")


def run_redaction(document_id: str) -> None:
    """Background entry point: own database session, shared concurrency limit."""
    with slots, SessionLocal() as db:
        document = db.get(Document, document_id)
        if document is not None and document.status == "redacting":
            redact_document(db, document)


def recover_interrupted_redactions(db: Session) -> int:
    stuck = list(db.scalars(select(Document).where(Document.status == "redacting")))
    for document in stuck:
        document.status = "ready"
        document.error_code = "interrupted"
    db.commit()
    return len(stuck)


def run_redaction_recovery() -> int:
    with SessionLocal() as db:
        return recover_interrupted_redactions(db)
