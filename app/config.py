import os
from urllib.parse import urlparse

from app.affiliate_linker import AffiliateLinker

# Initialize affiliate linker
affiliate_linker = AffiliateLinker(
    zazzle_affiliate_id=os.getenv("ZAZZLE_AFFILIATE_ID", ""),
    zazzle_tracking_code=os.getenv("ZAZZLE_TRACKING_CODE", ""),
)

# Redis Configuration - Parse REDIS_URL if available, otherwise use individual vars
REDIS_URL = os.getenv("REDIS_URL")
if REDIS_URL:
    parsed = urlparse(REDIS_URL)
    REDIS_HOST = parsed.hostname or "localhost"
    REDIS_PORT = parsed.port or 6379
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD = parsed.password
    REDIS_SSL = parsed.scheme == "rediss"
else:
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
    REDIS_SSL = os.getenv("REDIS_SSL", "false").lower() == "true"

# WebSocket Redis Channel
WEBSOCKET_TASK_UPDATES_CHANNEL = "task_updates"
WEBSOCKET_GENERAL_UPDATES_CHANNEL = "general_updates"

# Base URL Configuration
BASE_URL = os.getenv("BASE_URL", "https://clouvel.ai")
