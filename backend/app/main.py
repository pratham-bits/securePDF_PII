import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.core.config import settings
from app.services.retention import retention_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(retention_loop()) if settings.retention_enabled else None
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