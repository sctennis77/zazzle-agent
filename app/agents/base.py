"""
Base agent interface for the Zazzle Agent application.

Defines the abstract interface for channel agents, which are responsible for posting content
and interacting with users on various platforms (e.g., Reddit, Twitter).
"""

from abc import ABC, abstractmethod


class ChannelAgent(ABC):
    """
    Abstract base class for channel agents.

    Channel agents are responsible for posting content and interacting with users
    on specific platforms. Subclasses must implement the required methods.
    """

    @abstractmethod
    def post_content(self, product, content):
        """
        Post content related to a product on the channel.

        Args:
            product: The product to post about
            content: The content to post
        """
        pass

    @abstractmethod
    def interact_with_users(self, product, context=None):
        """
        Interact with users on the channel regarding a product.

        Args:
            product: The product to interact about
            context: Optional additional context for interaction
        """
        pass
