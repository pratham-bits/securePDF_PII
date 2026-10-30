import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.clock import utcnow
from app.core.config import settings
from app.models import Document, Finding, User
from app.services import storage
from app.services.analysis import analyze_document
from app.services.retention import purge_document
from app.services import analysis as analysis_module
from app.services.analysis import recover_interrupted_analyses, run_analysis

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


def _document(db, user, sample="sample_digital_en.pdf"):
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
    return document


def _findings(db, document):
    return list(db.scalars(select(Finding).where(Finding.document_id == document.id)))


def test_findings_have_no_column_for_detected_text():
    assert "text" not in Finding.__table__.columns


def test_digital_document_gets_findings_with_tiers(db_session, user):
    document = _document(db_session, user)
    analyze_document(db_session, document)
    assert document.status == "ready"
    assert document.page_modes == ["digital"]
    by_type = {f.entity_type: f for f in _findings(db_session, document)}
    assert set(by_type) == {"PAN", "AADHAAR", "PHONE_IN", "EMAIL"}
    assert by_type["PAN"].tier == "mandatory"
    assert by_type["PAN"].decision == "redact"
    assert by_type["EMAIL"].tier == "recommended"
    assert all(f.boxes for f in by_type.values())


def test_scanned_document_goes_through_ocr(db_session, user):
    document = _document(db_session, user, "sample_scanned_en.pdf")
    analyze_document(db_session, document)
    assert document.status == "ready"
    assert document.page_modes == ["ocr"]
    types = {f.entity_type for f in _findings(db_session, document)}
    assert {"PAN", "PHONE_IN", "EMAIL"} <= types


def test_failed_analysis_is_recorded_without_findings(db_session, user):
    document = _document(db_session, user)
    document.wrapped_key = bytes(60)  # wrong key: the file cannot be decrypted
    db_session.commit()
    analyze_document(db_session, document)
    assert document.status == "failed"
    assert document.error_code == "analysis_error"
    assert _findings(db_session, document) == []


def test_analyzing_again_replaces_the_findings(db_session, user):
    document = _document(db_session, user)
    analyze_document(db_session, document)
    document.status = "analyzing"
    db_session.commit()
    analyze_document(db_session, document)
    assert len(_findings(db_session, document)) == 4


def test_purging_a_document_deletes_its_findings(db_session, user):
    document = _document(db_session, user)
    analyze_document(db_session, document)
    assert _findings(db_session, document)
    purge_document(db_session, document, "deleted")
    assert _findings(db_session, document) == []

def test_run_analysis_finishes_the_job_with_its_own_session(
    db_session, user, monkeypatch
):
    document = _document(db_session, user)
    document_id = document.id
    monkeypatch.setattr(analysis_module, "SessionLocal", lambda: db_session)
    run_analysis(document_id)
    assert db_session.get(Document, document_id).status == "ready"


def test_interrupted_analyses_are_marked_failed(db_session, user):
    stuck = _document(db_session, user)
    done = _document(db_session, user)
    done.status = "ready"
    db_session.commit()

    assert recover_interrupted_analyses(db_session) == 1
    assert stuck.status == "failed" and stuck.error_code == "interrupted"
    assert done.status == "ready"