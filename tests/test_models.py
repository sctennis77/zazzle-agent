import pytest
from app.models import ProductInfo, RedditContext, ProductIdea, PipelineConfig, AffiliateLinker
import os
import csv

def test_product_info_to_csv():
    """Test saving product to CSV file."""
    # Create test data
    reddit_context = RedditContext(
        post_id='test_post_id',
        post_title='Test Post Title',
        post_url='https://reddit.com/test',
        subreddit='test_subreddit'
    )

    # Create a test product
    product = ProductInfo(
        product_id='test_id',
        name='Test Product',
        product_type='sticker',
        zazzle_template_id='template123',
        zazzle_tracking_code='tracking456',
        image_url='https://example.com/image.jpg',
        product_url='https://example.com/product',
        theme='test_theme',
        model='dall-e-3',
        prompt_version='1.0.0',
        reddit_context=reddit_context,
        design_instructions={'image': 'https://example.com/image.jpg'},
        affiliate_link='https://example.com/affiliate',
        image_local_path='/path/to/image.jpg'
    )

    # Save to CSV
    test_file = 'test_products.csv'
    try:
        product.to_csv(test_file)

        # Verify CSV file exists and contains correct data
        assert os.path.exists(test_file)

        with open(test_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            row = rows[0]
            
            # Check required fields
            assert row['product_id'] == 'test_id'
            assert row['name'] == 'Test Product'
            assert row['product_type'] == 'sticker'
            assert row['zazzle_template_id'] == 'template123'
            assert row['zazzle_tracking_code'] == 'tracking456'
            assert row['image_url'] == 'https://example.com/image.jpg'
            assert row['product_url'] == 'https://example.com/product'
            assert row['theme'] == 'test_theme'
            assert row['model'] == 'dall-e-3'
            assert row['prompt_version'] == '1.0.0'
            assert row['affiliate_link'] == 'https://example.com/affiliate'
            assert row['image_local_path'] == '/path/to/image.jpg'

    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)

def test_pipeline_config():
    """Test PipelineConfig creation and logging."""
    config = PipelineConfig(
        model='dall-e-3',
        zazzle_template_id='template123',
        zazzle_tracking_code='tracking456',
        prompt_version='1.0.0'
    )
    
    assert config.model == 'dall-e-3'
    assert config.zazzle_template_id == 'template123'
    assert config.zazzle_tracking_code == 'tracking456'
    assert config.prompt_version == '1.0.0'

def test_reddit_context():
    """Test RedditContext creation and logging."""
    context = RedditContext(
        post_id='test_post_id',
        post_title='Test Post Title',
        post_url='https://reddit.com/test',
        subreddit='test_subreddit',
        post_content='Test post content',
        comments=[{'id': 'comment1', 'text': 'Test comment'}]
    )
    
    assert context.post_id == 'test_post_id'
    assert context.post_title == 'Test Post Title'
    assert context.post_url == 'https://reddit.com/test'
    assert context.subreddit == 'test_subreddit'
    assert context.post_content == 'Test post content'
    assert len(context.comments) == 1

def test_product_idea():
    """Test ProductIdea creation and logging."""
    reddit_context = RedditContext(
        post_id='test_post_id',
        post_title='Test Post Title',
        post_url='https://reddit.com/test',
        subreddit='test_subreddit'
    )
    
    idea = ProductIdea(
        theme='test_theme',
        image_description='Test image description',
        design_instructions={'image': 'https://example.com/image.jpg'},
        reddit_context=reddit_context,
        model='dall-e-3',
        prompt_version='1.0.0'
    )
    
    assert idea.theme == 'test_theme'
    assert idea.image_description == 'Test image description'
    assert idea.design_instructions['image'] == 'https://example.com/image.jpg'
    assert idea.model == 'dall-e-3'
    assert idea.prompt_version == '1.0.0'
    assert idea.reddit_context == reddit_context 

def test_affiliate_linker():
    linker = AffiliateLinker(zazzle_affiliate_id="test_affiliate_id", zazzle_tracking_code="test_tracking_code")
    product_url = "https://example.com/product"
    expected_link = f"{product_url}?rf=test_affiliate_id&tc=test_tracking_code"
    assert linker.compose_affiliate_link(product_url) == expected_link 