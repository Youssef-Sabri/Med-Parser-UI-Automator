"""Database Initialization & Schema Management."""

import sys
import time
from pathlib import Path
from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parent.parent))
from database.session import engine, SessionLocal, Base
# Import models so Base.metadata knows about them before create_all()
from database.schema import Extraction, PharmacistAction  # noqa: F401

def init_db():
    """
    Initialize database schema.
    Uses SQLAlchemy metadata for SQLite (no Alembic) and Alembic for PostgreSQL.
    """
    DATABASE_URL = str(engine.url)
    is_sqlite = DATABASE_URL.startswith("sqlite")

    if is_sqlite:
        Base.metadata.create_all(bind=engine)
    else:
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
        command.upgrade(alembic_cfg, "head")

if __name__ == "__main__":
    try:
        connected = False
        for i in range(5):
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                connected = True
                break
            except Exception:
                time.sleep(2 ** i)
        
        if not connected:
            raise RuntimeError("Failed to connect to database after retries.")

        init_db()
        print("[OK] Database Initialization Completed.")
    except Exception as e:
        print(f"[ERROR] Database Initialization Failed: {e}")
        sys.exit(1)
