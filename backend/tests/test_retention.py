import os
import time
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.clock import utcnow
from app.core.config import settings
from app.main import app
from app.models import Document, User
from app.services import storage
from app.services.retention import purge_expired, sweep_orphan_files

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "sample_digital_en.pdf"
PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def _temp_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", tmp_path / "files")


@pytest.fixture()
def user(db_session):
    user = User(email="u@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()
    return user


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


def _make_document(db, user, minutes):
    document_id = str(uuid.uuid4())
    storage_key, wrapped_key = storage.save_encrypted(b"%PDF-1.7 test", document_id)
    now = utcnow()
    document = Document(
        id=document_id,
        user_id=user.id,
        page_count=1,
        size_bytes=13,
        storage_key=storage_key,
        wrapped_key=wrapped_key,
        created_at=now,
        expires_at=now + timedelta(minutes=minutes),
    )
    db.add(document)
    db.commit()
    return document


def _file(key):
    return settings.storage_dir / f"{key}.bin"


def test_delete_requires_login(client):
    assert client.delete("/api/documents/anything").status_code == 401


def test_deleting_wipes_the_file_and_the_key(client, db_session):
    _login(client)
    document_id = _upload(client).json()["id"]
    row = db_session.get(Document, document_id)
    stored_path = _file(row.storage_key)
    assert stored_path.exists()

    assert client.delete(f"/api/documents/{document_id}").status_code == 204

    db_session.refresh(row)
    assert row.status == "deleted"
    assert row.storage_key is None and row.wrapped_key is None
    assert not stored_path.exists()
    assert client.get(f"/api/documents/{document_id}").status_code == 404
    assert client.get("/api/documents").json() == []


def test_cannot_delete_someone_elses_document(client, db_session):
    _login(client, "a@example.com")
    document_id = _upload(client).json()["id"]
    with TestClient(app) as other:
        _login(other, "b@example.com")
        assert other.delete(f"/api/documents/{document_id}").status_code == 404
    assert db_session.get(Document, document_id).status == "uploaded"


def test_purge_expired_removes_only_expired_documents(db_session, user):
    expired = _make_document(db_session, user, minutes=-1)
    fresh = _make_document(db_session, user, minutes=60)
    expired_path, fresh_path = _file(expired.storage_key), _file(fresh.storage_key)

    assert purge_expired(db_session) == 1

    assert expired.status == "expired" and expired.wrapped_key is None
    assert not expired_path.exists()
    assert fresh.status == "uploaded" and fresh_path.exists()


def test_orphan_sweep_removes_old_unreferenced_files_only(db_session, user):
    referenced = _make_document(db_session, user, minutes=60)
    referenced_path = _file(referenced.storage_key)
    old_key, _ = storage.save_encrypted(b"x", "ghost-1")
    new_key, _ = storage.save_encrypted(b"x", "ghost-2")

    long_ago = time.time() - 2 * 3600
    os.utime(_file(old_key), (long_ago, long_ago))
    os.utime(referenced_path, (long_ago, long_ago))  # old, but still referenced

    assert sweep_orphan_files(db_session) == 1
    assert not _file(old_key).exists()
    assert _file(new_key).exists()  # too recent to judge
    assert referenced_path.exists()