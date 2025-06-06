class DistributionError(Exception):
    """Base exception for distribution-related errors."""
    pass


class DistributionChannelError(DistributionError):
    """Exception raised for channel-specific errors."""
    pass


class DistributionValidationError(DistributionError):
    """Exception raised for validation errors."""
    pass


class DistributionPublishError(DistributionError):
    """Exception raised for content publication errors."""
    pass 