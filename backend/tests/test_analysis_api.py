from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.models import Document
from app.services.analysis import analyze_document

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


def test_analyze_requires_login(client):
    assert client.post("/api/documents/x/analyze").status_code == 401


def test_analyze_marks_the_document_and_schedules_the_job(client, monkeypatch):
    calls = []
    monkeypatch.setattr("app.api.documents.run_analysis", calls.append)
    _login(client)
    document_id = _upload(client).json()["id"]

    response = client.post(f"/api/documents/{document_id}/analyze")

    assert response.status_code == 202
    assert response.json()["status"] == "analyzing"
    assert calls == [document_id]
    assert client.post(f"/api/documents/{document_id}/analyze").status_code == 409


def test_another_user_cannot_analyze_or_read_findings(client):
    _login(client, "a@example.com")
    document_id = _upload(client).json()["id"]
    with TestClient(app) as other:
        _login(other, "b@example.com")
        assert other.post(f"/api/documents/{document_id}/analyze").status_code == 404
        assert other.get(f"/api/documents/{document_id}/findings").status_code == 404


def test_findings_endpoint_returns_boxes_and_tiers(client, db_session):
    _login(client)
    document_id = _upload(client).json()["id"]
    document = db_session.get(Document, document_id)
    document.status = "analyzing"
    db_session.commit()
    analyze_document(db_session, document)

    response = client.get(f"/api/documents/{document_id}/findings")

    assert response.status_code == 200
    findings = response.json()
    assert {f["entity_type"] for f in findings} == {"PAN", "AADHAAR", "PHONE_IN", "EMAIL"}
    assert all(f["boxes"] and f["decision"] == "redact" for f in findings)
    assert client.get(f"/api/documents/{document_id}").json()["status"] == "ready"