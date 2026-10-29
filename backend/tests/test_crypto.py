import pytest
from cryptography.exceptions import InvalidTag

from app.core.crypto import decrypt_document, encrypt_document

SECRET = b"%PDF-1.7 Aadhaar 2345 6789 0123"


def test_roundtrip():
    encrypted, wrapped = encrypt_document(SECRET, b"doc-1")
    assert decrypt_document(encrypted, wrapped, b"doc-1") == SECRET


def test_plaintext_is_not_visible_in_the_encrypted_file():
    encrypted, _ = encrypt_document(SECRET, b"doc-1")
    assert b"Aadhaar" not in encrypted
    assert SECRET not in encrypted


def test_each_document_gets_its_own_key():
    _, wrapped_1 = encrypt_document(SECRET, b"doc-1")
    _, wrapped_2 = encrypt_document(SECRET, b"doc-1")
    assert wrapped_1 != wrapped_2


def test_tampering_is_detected():
    encrypted, wrapped = encrypt_document(SECRET, b"doc-1")
    tampered = encrypted[:-1] + bytes([encrypted[-1] ^ 1])
    with pytest.raises(InvalidTag):
        decrypt_document(tampered, wrapped, b"doc-1")


def test_file_cannot_be_moved_to_another_document():
    encrypted, wrapped = encrypt_document(SECRET, b"doc-1")
    with pytest.raises(InvalidTag):
        decrypt_document(encrypted, wrapped, b"doc-2")


def test_without_its_own_wrapped_key_the_file_is_unreadable():
    # This is crypto-shredding: once a document's key is erased, the file is noise.
    encrypted, _ = encrypt_document(SECRET, b"doc-1")
    _, someone_elses_key = encrypt_document(SECRET, b"doc-1")
    with pytest.raises(InvalidTag):
        decrypt_document(encrypted, someone_elses_key, b"doc-1")