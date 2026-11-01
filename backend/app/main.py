import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.findings import router as findings_router
from app.api.health import router as health_router
from app.api.output import router as output_router
from app.core.config import settings
from app.services.analysis import run_recovery
from app.services.redaction import run_redaction_recovery
from app.services.retention import retention_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    if settings.retention_enabled:  # this flag gates all background jobs
        await asyncio.to_thread(run_recovery)
        await asyncio.to_thread(run_redaction_recovery)
        task = asyncio.create_task(retention_loop())
    try:
        yield
    finally:
        if task:
            task.cancel()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(findings_router, prefix="/api")
app.include_router(output_router, prefix="/api")