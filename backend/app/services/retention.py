import asyncio
import logging
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Document
from app.services import storage

logger = logging.getLogger("uvicorn.error")  # shows up in the server log

HIDDEN_STATUSES = ("deleted", "expired")


def purge_document(db: Session, document: Document, new_status: str) -> None:
    """Erase the key first (crypto-shredding), then the file."""
    storage_key = document.storage_key
    document.storage_key = None
    document.wrapped_key = None
    document.status = new_status
    db.commit()  # once this succeeds, the stored file can no longer be decrypted
    if storage_key:
        storage.delete_file(storage_key)


def purge_expired(db: Session) -> int:
    stmt = select(Document).where(
        Document.expires_at < utcnow(), Document.status.not_in(HIDDEN_STATUSES)
    )
    documents = list(db.scalars(stmt))
    for document in documents:
        purge_document(db, document, "expired")
    return len(documents)


def sweep_orphan_files(db: Session) -> int:
    """Delete stored files that no document row references (for example after a crash)."""
    directory = settings.storage_dir
    if not directory.exists():
        return 0
    referenced = set(
        db.scalars(select(Document.storage_key).where(Document.storage_key.is_not(None)))
    )
    cutoff = time.time() - settings.orphan_grace_minutes * 60
    removed = 0
    for path in directory.iterdir():
        if not path.is_file() or path.suffix not in (".bin", ".tmp"):
            continue
        if path.suffix == ".bin" and path.stem in referenced:
            continue
        if path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True)
            removed += 1
    return removed


def run_cycle() -> None:
    with SessionLocal() as db:
        expired = purge_expired(db)
        orphans = sweep_orphan_files(db)
    # Counts only: never log file names, keys or document content.
    logger.info("retention cycle: expired=%d orphan_files=%d", expired, orphans)


async def retention_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(run_cycle)
        except Exception:
            logger.exception("retention cycle failed")
        await asyncio.sleep(settings.purge_interval_minutes * 60)