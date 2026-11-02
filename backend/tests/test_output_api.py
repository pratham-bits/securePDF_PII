from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.main import app
from app.models import AuditEvent, Document
from app.services.analysis import analyze_document
from app.services.redaction import redact_document

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "sample_digital_en.pdf"
PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def _temp_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", tmp_path / "files")


def _login(client, email="a@example.com"):
    client.post("/api/auth/register", json={"email": email, "password": PASSWORD})
    response = client.post(
        "/api/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200


def _upload(client):
    return client.post(
        "/api/documents", files={"file": ("x.pdf", SAMPLE.read_bytes(), "application/pdf")}
    )


def _ready_document(client, db_session, email="a@example.com"):
    _login(client, email)
    document_id = _upload(client).json()["id"]
    document = db_session.get(Document, document_id)
    document.status = "analyzing"
    db_session.commit()
    analyze_document(db_session, document)
    return document_id


def test_output_endpoints_require_login(client):
    assert client.post("/api/documents/x/redact").status_code == 401
    assert client.get("/api/documents/x/download").status_code == 401
    assert client.get("/api/documents/x/original").status_code == 401


def test_redact_schedules_the_job_and_rejects_early_or_repeat_requests(
    client, db_session, monkeypatch
):
    calls = []
    monkeypatch.setattr("app.api.output.run_redaction", calls.append)
    _login(client)
    uploaded_id = _upload(client).json()["id"]
    assert client.post(f"/api/documents/{uploaded_id}/redact").status_code == 409

    document_id = _ready_document(client, db_session)
    response = client.post(f"/api/documents/{document_id}/redact")
    assert response.status_code == 202
    assert response.json()["status"] == "redacting"
    assert calls == [document_id]
    assert client.post(f"/api/documents/{document_id}/redact").status_code == 409


def test_download_works_only_after_redaction(client, db_session):
    document_id = _ready_document(client, db_session)
    assert client.get(f"/api/documents/{document_id}/download").status_code == 409

    document = db_session.get(Document, document_id)
    document.status = "redacting"
    db_session.commit()
    redact_document(db_session, document)

    response = client.get(f"/api/documents/{document_id}/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert 'attachment; filename="redacted.pdf"' in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "no-store"
    assert response.content.startswith(b"%PDF")
    with pymupdf.open(stream=response.content, filetype="pdf") as doc:
        assert "ABCDE1234F" not in doc[0].get_text()
    actions = [event.action for event in db_session.scalars(select(AuditEvent))]
    assert actions == ["download"]


def test_original_is_served_inline_and_never_cached(client, db_session):
    document_id = _ready_document(client, db_session)
    response = client.get(f"/api/documents/{document_id}/original")
    assert response.status_code == 200
    assert response.content == SAMPLE.read_bytes()
    assert response.headers["content-disposition"].startswith("inline")
    assert response.headers["cache-control"] == "no-store"


def test_other_users_cannot_download_view_or_redact(client, db_session):
    document_id = _ready_document(client, db_session, "a@example.com")
    with TestClient(app) as other:
        _login(other, "b@example.com")
        assert other.get(f"/api/documents/{document_id}/original").status_code == 404
        assert other.get(f"/api/documents/{document_id}/download").status_code == 404
        assert other.post(f"/api/documents/{document_id}/redact").status_code == 404

def _redacted_document(client, db_session):
    document_id = _ready_document(client, db_session)
    document = db_session.get(Document, document_id)
    document.status = "redacting"
    db_session.commit()
    redact_document(db_session, document)
    assert document.status == "redacted"
    return document_id, document


def test_changing_a_decision_after_redaction_discards_the_stale_output(
    client, db_session
):
    document_id, document = _redacted_document(client, db_session)
    findings = client.get(f"/api/documents/{document_id}/findings").json()
    email = next(f for f in findings if f["entity_type"] == "EMAIL")

    response = client.patch(
        f"/api/documents/{document_id}/findings/{email['id']}",
        json={"decision": "keep"},
    )

    assert response.status_code == 200
    db_session.refresh(document)
    assert document.status == "ready"
    assert not document.has_output
    assert client.get(f"/api/documents/{document_id}/download").status_code == 409


def test_adding_a_box_after_redaction_also_discards_the_output(client, db_session):
    document_id, document = _redacted_document(client, db_session)
    box = {"page": 0, "x0": 72, "y0": 100, "x1": 200, "y1": 120}

    assert client.post(f"/api/documents/{document_id}/findings", json=box).status_code == 201

    db_session.refresh(document)
    assert document.status == "ready"
    assert not document.has_output