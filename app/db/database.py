from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from .models import Base
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Get the absolute path to the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_ROOT / 'zazzle_pipeline.db'
DB_URL = os.getenv('DATABASE_URL', f'sqlite:///{DB_PATH}')

logger.info(f"Using database at: {DB_PATH}")

engine = create_engine(DB_URL, echo=False, future=True)

# Enable foreign key support for SQLite
def _fk_pragma_on_connect(dbapi_con, con_record):
    dbapi_con.execute('PRAGMA foreign_keys=ON')

if DB_URL.startswith('sqlite'):
    event.listen(engine, 'connect', _fk_pragma_on_connect)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize the database by creating all tables."""
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