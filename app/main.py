import logging
import os
from contextlib import contextmanager

from dotenv import load_dotenv

from app.db.database import SessionLocal, init_db
from app.utils.logging_config import setup_logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Debug environment variable loading
logger.info(f"Environment variables available: {list(os.environ.keys())}")
logger.info(f"Railway environment detected: {'RAILWAY_ENVIRONMENT' in os.environ}")

# Log the loaded API key (masked)
openai_api_key_loaded = os.getenv("OPENAI_API_KEY")
if openai_api_key_loaded:
    logger.info(
        f"OPENAI_API_KEY loaded: {openai_api_key_loaded[:5]}...{openai_api_key_loaded[-5:]}"
    )
else:
    logger.warning("OPENAI_API_KEY not loaded.")
    # Check if any env vars contain 'openai' or 'OPENAI'
    openai_vars = {k: v for k, v in os.environ.items() if "openai" in k.lower()}
    logger.info(
        f"Environment variables containing 'openai': {list(openai_vars.keys())}"
    )


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Expose FastAPI app for Uvicorn
from app.api import app
