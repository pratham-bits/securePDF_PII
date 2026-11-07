import logging

from dataclasses import asdict

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Document, Finding
from app.pipeline.document import extract_document
from app.pipeline.locate import find_pii
from app.pipeline.policy import default_decision, tier_for
from app.services import storage
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.jobs import slots
logger = logging.getLogger("uvicorn.error")


def _mark_failed(db: Session, document_id: str) -> None:
    document = db.get(Document, document_id)  # reload after the rollback
    if document is not None and document.status == "analyzing":
        document.status = "failed"
        document.error_code = "analysis_error"
        db.commit()


def analyze_document(db: Session, document: Document) -> None:
    """Find PII in a stored document and save the findings (metadata only).

    The caller sets the status to "analyzing" first. On success it becomes "ready",
    on any failure "failed". The document is decrypted in memory only.
    """
    document_id = document.id
    try:
        if document.storage_key is None or document.wrapped_key is None:
            raise ValueError(f"Document {document_id} is missing storage or encryption keys")

        data = storage.read_decrypted(
            document.storage_key, document.wrapped_key, document_id
        )
        extraction = extract_document(data, lang=settings.ocr_languages)
        findings = find_pii(extraction.words)

        db.refresh(document)
        if document.status != "analyzing":  # deleted or expired while we worked
            return

        db.execute(delete(Finding).where(Finding.document_id == document_id))
        for finding in findings:
            if not finding.boxes:
                continue
            detection = finding.detection
            tier = tier_for(detection.entity_type)
            db.add(
                Finding(
                    document_id=document_id,
                    entity_type=detection.entity_type,
                    tier=tier,
                    score=detection.score,
                    source=detection.source,
                    checksum_ok=detection.checksum_ok,
                    decision=default_decision(tier),
                    page=finding.boxes[0].page,
                    boxes=[asdict(box) for box in finding.boxes],
                )
            )
        document.page_modes = extraction.modes
        document.error_code = None
        document.status = "ready"
        db.commit()
    except Exception as exc:
        db.rollback()
        # The error type only: messages could contain document content.
        logger.error("analysis failed: %s", type(exc).__name__)
        _mark_failed(db, document_id)




def run_analysis(document_id: str) -> None:
    """Background entry point: own database session, limited concurrency."""
    with slots, SessionLocal() as db:
        document = db.get(Document, document_id)
        if document is not None and document.status == "analyzing":
            analyze_document(db, document)


def recover_interrupted_analyses(db: Session) -> int:
    """After a restart, jobs still marked "analyzing" will never finish."""
    stuck = list(db.scalars(select(Document).where(Document.status == "analyzing")))
    for document in stuck:
        document.status = "failed"
        document.error_code = "interrupted"
    db.commit()
    return len(stuck)


def run_recovery() -> int:
    with SessionLocal() as db:
        return recover_interrupted_analyses(db)