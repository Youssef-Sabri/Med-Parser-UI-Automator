
import logging
import sys
from alembic.config import Config
from alembic import command
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("prestart")

def run_migrations():
    """
    Execute database migrations synchronously before the main app starts.
    This prevents multi-worker race conditions in production.
    """
    logger.info("Initializing pre-start sequence...")
    try:
        # Resolve config path relative to this script
        base_dir = Path(__file__).resolve().parent
        alembic_cfg = Config(str(base_dir / "alembic.ini"))
        
        logger.info("Running database migrations...")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied successfully.")
        
    except Exception as e:
        logger.critical(f"Database migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()
