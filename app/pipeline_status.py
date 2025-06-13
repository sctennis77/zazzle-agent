from enum import Enum

class PipelineStatus(Enum):
    """Enum for pipeline run statuses."""
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed" 