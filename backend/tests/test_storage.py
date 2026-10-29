import pytest

from app.core.config import settings
from app.services import storage


@pytest.fixture(autouse=True)
def _temp_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", tmp_path / "files")


def test_save_and_read_roundtrip():
    key, wrapped = storage.save_encrypted(b"hello pdf", "doc-1")
    assert storage.read_decrypted(key, wrapped, "doc-1") == b"hello pdf"


def test_file_on_disk_is_encrypted():
    key, _ = storage.save_encrypted(b"Aadhaar 2345", "doc-1")
    on_disk = (settings.storage_dir / f"{key}.bin").read_bytes()
    assert b"Aadhaar" not in on_disk


def test_delete_removes_the_file_and_is_idempotent():
    key, _ = storage.save_encrypted(b"x", "doc-1")
    storage.delete_file(key)
    storage.delete_file(key)  # a second call must not fail
    assert not (settings.storage_dir / f"{key}.bin").exists()


@pytest.mark.parametrize("bad_key", ["../secret", "..\\secret", "abc", "G" * 32])
def test_storage_keys_cannot_escape_the_folder(bad_key):
    with pytest.raises(ValueError):
        storage.delete_file(bad_key)