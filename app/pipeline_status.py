from enum import Enum

class PipelineStatus(Enum):
    """Enum for pipeline run statuses."""
    STARTED = "started"
    NO_PRODUCT = "no-product"
    COMPLETED = "completed"
    FAILED = "failed" 