from sqlalchemy import text

from app.db.session import engine

HINDI = "नमस्ते"

with engine.connect() as conn:
    version = conn.execute(text("SELECT VERSION()")).scalar()
    charset = conn.execute(text("SELECT @@character_set_database")).scalar()
    collation = conn.execute(text("SELECT @@collation_database")).scalar()
    echoed = conn.execute(text("SELECT :s"), {"s": HINDI}).scalar()

print(f"MySQL version: {version}")
print(f"database charset: {charset}, collation: {collation}")
print(f"Hindi round trip ok: {echoed == HINDI}")