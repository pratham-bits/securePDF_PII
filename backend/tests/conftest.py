import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.config import settings
from app.db.base import Base


@pytest.fixture()
def db_session():
    engine = create_engine(settings.database_url.set(database="securepdf_test"))
    db_name = engine.url.database or ""
    assert db_name.endswith("_test")  # never touch the real database
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
