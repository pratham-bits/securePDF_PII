import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

NONCE_SIZE = 12


def _master_key() -> bytes:
    key = base64.urlsafe_b64decode(settings.file_encryption_key)
    if len(key) != 32:
        raise ValueError("FILE_ENCRYPTION_KEY must decode to exactly 32 bytes")
    return key


def _seal(key: bytes, plaintext: bytes, context: bytes | None = None) -> bytes:
    nonce = os.urandom(NONCE_SIZE)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, context)


def _open(key: bytes, sealed: bytes, context: bytes | None = None) -> bytes:
    nonce, ciphertext = sealed[:NONCE_SIZE], sealed[NONCE_SIZE:]
    return AESGCM(key).decrypt(nonce, ciphertext, context)


def encrypt_document(plaintext: bytes, context: bytes) -> tuple[bytes, bytes]:
    """Return (encrypted_file, wrapped_key). Every document gets its own key.

    `context` (the document id) is bound into the encryption, so the file
    cannot be moved onto another document's record.
    """
    data_key = AESGCM.generate_key(bit_length=256)
    return _seal(data_key, plaintext, context), _seal(_master_key(), data_key)


def decrypt_document(encrypted_file: bytes, wrapped_key: bytes, context: bytes) -> bytes:
    data_key = _open(_master_key(), wrapped_key)
    return _open(data_key, encrypted_file, context)