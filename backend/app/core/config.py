from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


# Resolve the backend directory independently of the current working directory.
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "SecurePDF API"
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Database configuration
    db_host: str = "127.0.0.1"
    db_port: int = 3307
    db_user: str = "securepdf_app"
    db_password: str
    db_name: str = "securepdf"

    # Authentication and session security
    secret_key: str
    access_token_minutes: int = 60
    cookie_secure: bool = False  # Set to True when served over HTTPS.

    # Uploaded file storage
    storage_dir: Path = BACKEND_DIR / "storage" / "files"
    file_encryption_key: str  # base64 of 32 random bytes; never commit
    max_upload_mb: int = 20
    max_pages: int = 30
    retention_hours: int = 12
    purge_interval_minutes: int = 10
    orphan_grace_minutes: int = 60  # unreferenced files younger than this are left alone
    max_concurrent_analyses: int = 1  # OCR is CPU-heavy
    retention_enabled: bool = True  # tests switch this off

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> URL:
        return URL.create(
            "mysql+pymysql",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"charset": "utf8mb4"},
        )


settings = Settings()
