from sqlalchemy import inspect, text

import app.models  # noqa: F401
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine


def migrate() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    print(f"Connecting to database: {engine.url.database} on {engine.url.host}:{engine.url.port}")

    # 1. Create any tables that don't exist yet (e.g., audit_events)
    Base.metadata.create_all(engine)

    # 2. Add newly added columns to existing tables if missing
    if "documents" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("documents")}
        with engine.begin() as conn:
            if "output_storage_key" not in existing_cols:
                print("Adding output_storage_key to documents table...")
                conn.execute(text("ALTER TABLE documents ADD COLUMN output_storage_key VARCHAR(32) NULL"))
            if "output_wrapped_key" not in existing_cols:
                print("Adding output_wrapped_key to documents table...")
                conn.execute(text("ALTER TABLE documents ADD COLUMN output_wrapped_key VARBINARY(64) NULL"))

    print("Database schema is up to date!")


if __name__ == "__main__":
    migrate()

