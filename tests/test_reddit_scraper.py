import pytest
from app.reddit_scraper import RedditScraper
from app.models import RedditContext, ProductIdea
import os
import json

@pytest.fixture
def reddit_scraper():
    """Create a RedditScraper instance for testing."""
    return RedditScraper()

@pytest.fixture
def sample_reddit_context():
    """Create a sample RedditContext for testing."""
    return RedditContext(
        post_id='test_post_id',
        post_title='Test Post Title',
        post_url='https://reddit.com/test',
        subreddit='test_subreddit',
        post_content='Test post content',
        comments=[{'id': 'comment1', 'text': 'Test comment'}]
    )

def test_generate_product_ideas(reddit_scraper, sample_reddit_context):
    """Test generating product ideas from a RedditContext."""
    # Mock the idea generation
    def mock_generate_ideas(context):
        return [
            ProductIdea(
                theme='theme1',
                image_description='Description 1',
                design_instructions={'image': 'https://example.com/image1.jpg'},
                reddit_context=context,
                model='dall-e-3',
                prompt_version='1.0.0'
            ),
            ProductIdea(
                theme='theme2',
                image_description='Description 2',
                design_instructions={'image': 'https://example.com/image2.jpg'},
                reddit_context=context,
                model='dall-e-3',
                prompt_version='1.0.0'
            )
        ]
    
    reddit_scraper._generate_ideas = mock_generate_ideas
    
    # Generate product ideas
    ideas = reddit_scraper.generate_product_ideas(sample_reddit_context)
    
    # Verify results
    assert len(ideas) == 2
    assert all(isinstance(idea, ProductIdea) for idea in ideas)
    assert ideas[0].theme == 'theme1'
    assert ideas[1].theme == 'theme2'
    assert all(idea.reddit_context == sample_reddit_context for idea in ideas)

def test_generate_product_ideas_empty(reddit_scraper, sample_reddit_context):
    """Test generating product ideas when no ideas are generated."""
    # Mock the idea generation to return an empty list
    def mock_generate_ideas(context):
        return []
    
    reddit_scraper._generate_ideas = mock_generate_ideas
    
    # Generate product ideas
    ideas = reddit_scraper.generate_product_ideas(sample_reddit_context)
    
    # Verify results
    assert len(ideas) == 0

def test_generate_product_ideas_error(reddit_scraper, sample_reddit_context):
    """Test error handling in generate_product_ideas."""
    # Mock the idea generation to raise an exception
    def mock_generate_ideas(context):
        raise Exception("Test error")
    
    reddit_scraper._generate_ideas = mock_generate_ideas
    
    # Verify that the error is caught and logged
    with pytest.raises(Exception):
        reddit_scraper.generate_product_ideas(sample_reddit_context)

def test_generate_product_ideas_batch(reddit_scraper):
    """Test generating product ideas for a batch of RedditContexts."""
    # Create sample RedditContexts
    contexts = [
        RedditContext(
            post_id=f'test_post_id_{i}',
            post_title=f'Test Post Title {i}',
            post_url=f'https://reddit.com/test{i}',
            subreddit='test_subreddit',
            post_content=f'Test post content {i}',
            comments=[{'id': f'comment{i}', 'text': f'Test comment {i}'}]
        )
        for i in range(2)
    ]
    
    # Mock the idea generation
    def mock_generate_ideas(context):
        # Get the context index from the post_id
        context_idx = int(context.post_id.split('_')[-1])
        return [
            ProductIdea(
                theme=f'theme{context_idx}_{j}',
                image_description=f'Description {context_idx}_{j}',
                design_instructions={'image': f'https://example.com/image{context_idx}_{j}.jpg'},
                reddit_context=context,
                model='dall-e-3',
                prompt_version='1.0.0'
            )
            for j in range(2)
        ]
    
    reddit_scraper._generate_ideas = mock_generate_ideas
    
    # Generate product ideas
    all_ideas = reddit_scraper.generate_product_ideas_batch(contexts)
    
    # Verify results
    assert len(all_ideas) == 4  # 2 contexts * 2 ideas per context
    assert all(isinstance(idea, ProductIdea) for idea in all_ideas)
    assert all(idea.reddit_context in contexts for idea in all_ideas)

def test_generate_product_ideas_batch_empty(reddit_scraper):
    """Test generating product ideas for an empty batch of RedditContexts."""
    ideas = reddit_scraper.generate_product_ideas_batch([])
    assert len(ideas) == 0 