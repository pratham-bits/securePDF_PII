from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.main import app
from app.models import Document
from app.services import storage

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


def _upload(client, data=None, name="whatever.pdf"):
    data = SAMPLE.read_bytes() if data is None else data
    return client.post(
        "/api/documents", files={"file": (name, data, "application/pdf")}
    )


def test_upload_requires_login(client):
    assert _upload(client).status_code == 401


def test_upload_stores_an_encrypted_file_and_metadata_only(client, db_session):
    _login(client)
    response = _upload(client, name="Rahul_Verma_Aadhaar.pdf")
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "uploaded"
    assert body["page_count"] == 1
    assert "Rahul" not in response.text  # the filename is never stored or returned
    row = db_session.scalars(select(Document)).one()
    assert row.wrapped_key
    on_disk = (settings.storage_dir / f"{row.storage_key}.bin").read_bytes()
    assert b"%PDF" not in on_disk
    hours = (row.expires_at - row.created_at).total_seconds() / 3600
    assert 11.9 < hours < 12.1


def test_upload_rejects_a_file_that_is_not_a_pdf(client):
    _login(client)
    assert _upload(client, b"hello world", "x.pdf").status_code == 400


def test_upload_rejects_a_fake_pdf(client):
    _login(client)
    assert _upload(client, b"%PDF-1.4\n garbage", "x.pdf").status_code == 400


def test_upload_rejects_oversized_files(client, monkeypatch):
    _login(client)
    monkeypatch.setattr(settings, "max_upload_mb", 0)
    assert _upload(client).status_code == 413


def test_upload_rejects_too_many_pages(client, monkeypatch):
    _login(client)
    monkeypatch.setattr(settings, "max_pages", 0)
    assert _upload(client).status_code == 400


def test_users_only_see_their_own_documents(client):
    _login(client, "a@example.com")
    _upload(client)
    with TestClient(app) as other:
        _login(other, "b@example.com")
        assert other.get("/api/documents").json() == []
    assert len(client.get("/api/documents").json()) == 1


def test_another_users_document_looks_like_it_does_not_exist(client):
    _login(client, "a@example.com")
    document_id = _upload(client).json()["id"]
    assert client.get(f"/api/documents/{document_id}").status_code == 200
    with TestClient(app) as other:
        _login(other, "b@example.com")
        assert other.get(f"/api/documents/{document_id}").status_code == 404


def test_stored_file_decrypts_back_to_the_original(client, db_session):
    _login(client)
    _upload(client)
    row = db_session.scalars(select(Document)).one()
    stored = storage.read_decrypted(row.storage_key, row.wrapped_key, row.id)
    assert stored == SAMPLE.read_bytes()