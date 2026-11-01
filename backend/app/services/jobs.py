import threading

from app.core.config import settings

# One pool of slots shared by every CPU-heavy job (analysis and redaction).
slots = threading.BoundedSemaphore(settings.max_concurrent_analyses)