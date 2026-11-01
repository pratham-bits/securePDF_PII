import os
import time
import uuid
from datetime import timedelta
from pathlib import Path

import pymupdf
import pytest
from sqlalchemy import select

from app.core.clock import utcnow
from app.core.config import settings
from app.models import Document, Finding, User
from app.pipeline.extract import extract_words
from app.services import redaction as redaction_module
from app.services import storage
from app.services.analysis import analyze_document
from app.services.redaction import (
    output_context,
    recover_interrupted_redactions,
    redact_document,
)
from app.services.retention import purge_document, sweep_orphan_files

SAMPLES = Path(__file__).resolve().parents[2] / "samples"


@pytest.fixture(autouse=True)
def _temp_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", tmp_path / "files")


@pytest.fixture()
def user(db_session):
    user = User(email="u@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()
    return user


def _analyzed(db, user, sample="sample_digital_en.pdf"):
    """An analyzed document, switched to "redacting" as the endpoint would do."""
    data = (SAMPLES / sample).read_bytes()
    document_id = str(uuid.uuid4())
    storage_key, wrapped_key = storage.save_encrypted(data, document_id)
    now = utcnow()
    document = Document(
        id=document_id,
        user_id=user.id,
        status="analyzing",
        page_count=1,
        size_bytes=len(data),
        storage_key=storage_key,
        wrapped_key=wrapped_key,
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )
    db.add(document)
    db.commit()
    analyze_document(db, document)
    document.status = "redacting"
    db.commit()
    return document


def _output_text(document) -> str:
    assert document.output_storage_key and document.output_wrapped_key
    data = storage.read_decrypted(
        document.output_storage_key,
        document.output_wrapped_key,
        output_context(document.id),
    )
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        return "".join(str(page.get_text()) for page in doc)


def _output_path(document) -> Path:
    return settings.storage_dir / f"{document.output_storage_key}.bin"


def test_redaction_produces_a_verified_encrypted_output(db_session, user):
    document = _analyzed(db_session, user)
    redact_document(db_session, document)
    assert document.status == "redacted"
    assert document.has_output
    text = _output_text(document)
    for secret in ("ABCDE1234F", "rahul.verma@example.com", "98765", "43210"):
        assert secret not in text
    assert "RENT AGREEMENT" in text
    assert b"%PDF" not in _output_path(document).read_bytes()


def test_findings_marked_keep_stay_visible(db_session, user):
    document = _analyzed(db_session, user)
    email = db_session.scalars(
        select(Finding).where(
            Finding.document_id == document.id, Finding.entity_type == "EMAIL"
        )
    ).one()
    email.decision = "keep"
    db_session.commit()
    redact_document(db_session, document)
    text = _output_text(document)
    assert "rahul.verma@example.com" in text
    assert "ABCDE1234F" not in text


def test_manual_boxes_are_redacted(db_session, user):
    document = _analyzed(db_session, user)
    words = extract_words(SAMPLES / "sample_digital_en.pdf")
    title = next(w for w in words if w.text == "RENT")
    db_session.add(
        Finding(
            document_id=document.id,
            entity_type="MANUAL",
            tier="manual",
            score=1.0,
            source="user",
            checksum_ok=None,
            decision="redact",
            page=0,
            boxes=[
                {"page": 0, "x0": title.x0, "y0": title.y0, "x1": title.x1, "y1": title.y1}
            ],
        )
    )
    db_session.commit()
    redact_document(db_session, document)
    assert document.status == "redacted"
    text = _output_text(document)
    assert "RENT" not in text
    assert "AGREEMENT" in text


def test_scanned_documents_are_verified_with_a_second_ocr_pass(db_session, user):
    document = _analyzed(db_session, user, "sample_scanned_en.pdf")
    redact_document(db_session, document)
    assert document.status == "redacted"
    assert document.error_code is None


def test_a_failed_verification_never_produces_an_output(db_session, user, monkeypatch):
    document = _analyzed(db_session, user)
    # A broken redactor that returns the file unchanged.
    monkeypatch.setattr(redaction_module, "redact_bytes", lambda data, boxes: data)
    redact_document(db_session, document)
    assert document.status == "ready"
    assert document.error_code == "verification_failed"
    assert not document.has_output
    assert len(list(settings.storage_dir.glob("*.bin"))) == 1  # only the original


def test_a_redaction_error_is_recorded(db_session, user):
    document = _analyzed(db_session, user)
    document.wrapped_key = bytes(60)  # wrong key: the file cannot be decrypted
    db_session.commit()
    redact_document(db_session, document)
    assert document.status == "ready"
    assert document.error_code == "redaction_error"


def test_purging_also_wipes_the_redacted_output(db_session, user):
    document = _analyzed(db_session, user)
    redact_document(db_session, document)
    output_path = _output_path(document)
    assert output_path.exists()
    purge_document(db_session, document, "deleted")
    assert document.output_storage_key is None
    assert document.output_wrapped_key is None
    assert not output_path.exists()


def test_orphan_sweep_does_not_delete_a_referenced_output(db_session, user):
    document = _analyzed(db_session, user)
    redact_document(db_session, document)
    output_path = _output_path(document)
    long_ago = time.time() - 2 * 3600
    os.utime(output_path, (long_ago, long_ago))
    assert sweep_orphan_files(db_session) == 0
    assert output_path.exists()


def test_interrupted_redactions_return_to_ready(db_session, user):
    document = _analyzed(db_session, user)  # status: redacting
    assert recover_interrupted_redactions(db_session) == 1
    assert document.status == "ready"
    assert document.error_code == "interrupted"
