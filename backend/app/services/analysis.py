import logging
from dataclasses import asdict

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import Document, Finding
from app.pipeline.document import extract_document
from app.pipeline.locate import find_pii
from app.pipeline.policy import default_decision, tier_for
from app.services import storage

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
        extraction = extract_document(data)
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
