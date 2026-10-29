
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


# Resolve the backend directory independently of the working directory.
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "SecurePDF API"
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Database configuration loaded from environment variables / .env
    db_host: str = "127.0.0.1"
    db_port: int = 3307
    db_user: str = "securepdf_app"
    db_password: str
    db_name: str = "securepdf"
    db_charset: str = "utf8mb4"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> URL:
        # Safely handles special characters in the password.
        return URL.create(
            "mysql+pymysql",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"charset": self.db_charset},
        )


settings = Settings()
