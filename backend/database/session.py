"""Database session management with SSL enforcement and standardized config."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import settings

DATABASE_URL = settings.DATABASE_URL

connect_args = {}
engine_kwargs = {}

if DATABASE_URL.startswith("postgresql"):
    connect_args["sslmode"] = "require"
    engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
elif DATABASE_URL.startswith("sqlite"):
    from sqlalchemy.pool import StaticPool
    connect_args["check_same_thread"] = False
    engine_kwargs["poolclass"] = StaticPool
else:
    engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    **engine_kwargs,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Provide request-scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
