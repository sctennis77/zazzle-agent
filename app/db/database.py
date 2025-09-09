import logging
import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from .models import Base

logger = logging.getLogger(__name__)

# Get the absolute path to the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent


def get_database_url():
    """Get the appropriate database URL based on environment."""
    if os.getenv("TESTING") == "true":
        # Use in-memory database for testing
        logger.info("Using in-memory database for testing")
        return "sqlite:///:memory:"
    else:
        # Use the DATABASE_URL environment variable if set, otherwise use default path
        DB_URL = os.getenv("DATABASE_URL")
        if DB_URL:
            logger.info(f"Using database URL from environment: {DB_URL}")
            return DB_URL
        else:
            # Fallback to default path in data/ directory
            DB_PATH = PROJECT_ROOT / "data" / "zazzle_pipeline.db"
            DB_URL = f"sqlite:///{DB_PATH}"
            logger.info(f"Using default database at: {DB_PATH}")
            return DB_URL


def create_database_engine(database_url=None):
    """Create a database engine with the given URL."""
    if database_url is None:
        database_url = get_database_url()

    # Get pool settings from environment variables
    pool_size = int(os.getenv("DB_POOL_SIZE", "20"))  # Increased from default 5
    max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "30"))  # Increased from default 10
    pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "60"))  # Connection timeout
    pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # Recycle after 1 hour

    # Configure engine with pool settings
    engine_kwargs = {
        "echo": False,
        "future": True,
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "pool_timeout": pool_timeout,
        "pool_recycle": pool_recycle,
    }
    
    # SQLite doesn't support connection pooling the same way
    if database_url.startswith("sqlite"):
        # For SQLite, we still want some pool settings but remove the problematic ones
        engine_kwargs = {"echo": False, "future": True}
        logger.info("Using SQLite - connection pooling disabled")
    else:
        logger.info(f"Configuring connection pool: size={pool_size}, max_overflow={max_overflow}")

    engine = create_engine(database_url, **engine_kwargs)

    # Enable foreign key support for SQLite
    def _fk_pragma_on_connect(dbapi_con, con_record):
        dbapi_con.execute("PRAGMA foreign_keys=ON")

    if database_url.startswith("sqlite"):
        event.listen(engine, "connect", _fk_pragma_on_connect)

    return engine


# Create the main engine
engine = create_database_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_test_engine():
    """Get a test-specific engine that uses in-memory database."""
    test_engine = create_database_engine("sqlite:///:memory:")
    return test_engine


def init_db():
    """Initialize the database by creating all tables."""
    if os.getenv("TESTING") == "true":
        logger.info("Initializing in-memory test database")
    else:
        DB_PATH = PROJECT_ROOT / "data" / "zazzle_pipeline.db"
        if not DB_PATH.exists():
            logger.info(f"Creating new database at {DB_PATH}")
        else:
            logger.info(f"Using existing database at {DB_PATH}")
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
