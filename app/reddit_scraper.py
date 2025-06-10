"""
Reddit scraper module for the Zazzle Agent application.

This module provides functionality for generating product ideas from Reddit context data.
It supports both single and batch idea generation, and is designed to be extensible for
custom idea generation strategies.
"""

from app.models import RedditContext, ProductIdea

class RedditScraper:
    """
    Generates product ideas from Reddit context data.
    
    This class provides methods to generate product ideas from a single RedditContext
    or a batch of RedditContext objects. It can be extended with custom idea generation
    logic by defining a _generate_ideas method.
    """
    def generate_product_ideas(self, reddit_context):
        """
        Generate product ideas from a single RedditContext.
        
        Args:
            reddit_context: RedditContext object containing post data
        
        Returns:
            List of ProductIdea objects
        """
        if hasattr(self, '_generate_ideas'):
            return self._generate_ideas(reddit_context)
        return [
            ProductIdea(
                theme='mock_theme',
                image_description='mock description',
                design_instructions={'image': 'https://example.com/image.jpg'},
                reddit_context=reddit_context,
                model='dall-e-3',
                prompt_version='1.0.0'
            )
        ]

    def generate_product_ideas_batch(self, reddit_contexts):
        """
        Generate product ideas from a batch of RedditContext objects.
        
        Args:
            reddit_contexts: List of RedditContext objects
        
        Returns:
            List of ProductIdea objects
        """
        ideas = []
        for context in reddit_contexts:
            ideas.extend(self.generate_product_ideas(context))
        return ideas 