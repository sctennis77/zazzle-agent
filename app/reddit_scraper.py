"""
Reddit scraper module for the Zazzle Agent application.

This module provides functionality for generating product ideas from Reddit context data.
It supports both single and batch idea generation, and is designed to be extensible for
custom idea generation strategies.

The module handles:
- Single RedditContext processing
- Batch processing of multiple RedditContext objects
- Extensible idea generation through subclassing
- Default mock idea generation for testing
"""

from typing import List, Optional

from app.models import ProductIdea, RedditContext


class RedditScraper:
    """
    Generates product ideas from Reddit context data.

    This class provides methods to generate product ideas from a single RedditContext
    or a batch of RedditContext objects. It can be extended with custom idea generation
    logic by defining a _generate_ideas method.

    The class supports:
    - Single context idea generation
    - Batch processing of multiple contexts
    - Extensible idea generation through subclassing
    - Default mock idea generation for testing
    """

    def generate_product_ideas(
        self, reddit_context: RedditContext
    ) -> List[ProductIdea]:
        """
        Generate product ideas from a single RedditContext.

        Args:
            reddit_context (RedditContext): RedditContext object containing post data
                and metadata for idea generation

        Returns:
            List[ProductIdea]: List of generated product ideas. If no custom _generate_ideas
                method is defined, returns a single mock idea for testing.
        """
        if hasattr(self, "_generate_ideas"):
            return self._generate_ideas(reddit_context)
        return [
            ProductIdea(
                theme="mock_theme",
                image_description="mock description",
                design_instructions={"image": "https://example.com/image.jpg"},
                reddit_context=reddit_context,
                model="dall-e-3",
                prompt_version="1.0.0",
            )
        ]

    def generate_product_ideas_batch(
        self, reddit_contexts: List[RedditContext]
    ) -> List[ProductIdea]:
        """
        Generate product ideas from a batch of RedditContext objects.

        Args:
            reddit_contexts (List[RedditContext]): List of RedditContext objects to process

        Returns:
            List[ProductIdea]: List of all generated product ideas from all contexts
        """
        ideas = []
        for context in reddit_contexts:
            ideas.extend(self.generate_product_ideas(context))
        return ideas
