"""
Base agent interface for the Zazzle Agent application.

Defines the abstract interface for channel agents, which are responsible for posting content
and interacting with users on various platforms (e.g., Reddit, Twitter).
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from app.models import ProductInfo


class ChannelAgent(ABC):
    """
    Abstract base class for channel agents.

    Channel agents are responsible for posting content and interacting with users
    on specific platforms. Subclasses must implement the required methods.
    """

    @abstractmethod
    def post_content(self, product: ProductInfo, content: str) -> None:
        """
        Post content related to a product on the channel.

        Args:
            product: The product to post about
            content: The content to post
        """
        pass

    @abstractmethod
    def interact_with_users(self, product: ProductInfo, context: Optional[Any] = None) -> None:
        """
        Interact with users on the channel regarding a product.

        Args:
            product: The product to interact about
            context: Optional additional context for interaction
        """
        pass
