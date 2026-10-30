from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.main import app
from app.models import AuditEvent, Document
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


def _ready_document(client, db_session, email="a@example.com"):
    _login(client, email)
    document_id = _upload(client).json()["id"]
    document = db_session.get(Document, document_id)
    document.status = "analyzing"
    db_session.commit()
    analyze_document(db_session, document)
    return document_id


def _findings_by_type(client, document_id):
    response = client.get(f"/api/documents/{document_id}/findings")
    return {f["entity_type"]: f for f in response.json()}


def _url(document_id, finding_id=None):
    base = f"/api/documents/{document_id}/findings"
    return base if finding_id is None else f"{base}/{finding_id}"


def test_changing_a_decision_requires_login(client):
    assert client.patch(_url("x", 1), json={"decision": "keep"}).status_code == 401


def test_a_recommended_finding_can_be_switched_freely(client, db_session):
    document_id = _ready_document(client, db_session)
    email = _findings_by_type(client, document_id)["EMAIL"]
    response = client.patch(_url(document_id, email["id"]), json={"decision": "keep"})
    assert response.status_code == 200
    assert response.json()["decision"] == "keep"


def test_keeping_a_mandatory_finding_needs_confirmation_and_is_audited(
    client, db_session
):
    document_id = _ready_document(client, db_session)
    pan = _findings_by_type(client, document_id)["PAN"]
    url = _url(document_id, pan["id"])

    refused = client.patch(url, json={"decision": "keep"})
    assert refused.status_code == 409
    assert _findings_by_type(client, document_id)["PAN"]["decision"] == "redact"

    allowed = client.patch(url, json={"decision": "keep", "confirm_override": True})
    assert allowed.status_code == 200
    assert allowed.json()["decision"] == "keep"
    events = list(db_session.scalars(select(AuditEvent)))
    assert len(events) == 1
    assert events[0].action == "override_mandatory"
    assert events[0].entity_type == "PAN"
    assert events[0].document_id == document_id

    back = client.patch(url, json={"decision": "redact"})
    assert back.status_code == 200
    assert back.json()["decision"] == "redact"


def test_a_manual_box_is_added_as_a_redaction(client, db_session):
    document_id = _ready_document(client, db_session)
    box = {"page": 0, "x0": 72, "y0": 100, "x1": 200, "y1": 120}
    response = client.post(_url(document_id), json=box)
    assert response.status_code == 201
    body = response.json()
    assert body["entity_type"] == "MANUAL"
    assert body["tier"] == "manual"
    assert body["decision"] == "redact"
    assert body["boxes"][0]["x1"] == 200
    assert len(client.get(_url(document_id)).json()) == 5


def test_manual_box_input_is_validated(client, db_session):
    document_id = _ready_document(client, db_session)
    good = {"page": 0, "x0": 72, "y0": 100, "x1": 200, "y1": 120}
    assert client.post(_url(document_id), json={**good, "page": 5}).status_code == 422
    assert client.post(_url(document_id), json={**good, "x0": -1}).status_code == 422
    assert client.post(_url(document_id), json={**good, "x1": 73}).status_code == 422


def test_only_manual_boxes_can_be_deleted(client, db_session):
    document_id = _ready_document(client, db_session)
    box = {"page": 0, "x0": 72, "y0": 100, "x1": 200, "y1": 120}
    manual_id = client.post(_url(document_id), json=box).json()["id"]
    pan = _findings_by_type(client, document_id)["PAN"]

    assert client.delete(_url(document_id, manual_id)).status_code == 204
    assert "MANUAL" not in _findings_by_type(client, document_id)
    assert client.delete(_url(document_id, pan["id"])).status_code == 409


def test_another_user_cannot_change_findings(client, db_session):
    document_id = _ready_document(client, db_session, "a@example.com")
    pan = _findings_by_type(client, document_id)["PAN"]
    with TestClient(app) as other:
        _login(other, "b@example.com")
        response = other.patch(
            _url(document_id, pan["id"]),
            json={"decision": "keep", "confirm_override": True},
        )
        assert response.status_code == 404


def test_review_is_blocked_until_the_document_is_analyzed(client):
    _login(client)
    document_id = _upload(client).json()["id"]  # status: uploaded
    box = {"page": 0, "x0": 72, "y0": 100, "x1": 200, "y1": 120}
    assert client.post(_url(document_id), json=box).status_code == 409


def test_audit_events_have_no_column_for_document_content():
    assert set(AuditEvent.__table__.columns.keys()) == {
        "id",
        "user_id",
        "document_id",
        "action",
        "entity_type",
        "created_at",
    }