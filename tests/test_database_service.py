import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.database_service import DatabaseService
from app.db.models import (
    PipelineRun, RedditPost, ProductInfo, ErrorLog, CommentSummary,
    Base
)

@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine('sqlite:///:memory:')
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    Base.metadata.create_all(bind=engine)
    yield session
    session.close()

@pytest.fixture
def db_service(db_session):
    """Create a DatabaseService instance with a test session."""
    return DatabaseService(db_session)

def test_create_tables(db_service):
    """Test that tables are created successfully."""
    db_service.create_tables()
    # No exception means success

def test_create_and_get_pipeline_run(db_service):
    """Test creating and retrieving a pipeline run."""
    config = {
        'model': 'test-model',
        'template_id': 'test-template'
    }
    
    # Create pipeline run
    run = db_service.create_pipeline_run(config)
    assert run.status == 'pending'
    assert run.config == config
    
    # Get pipeline run
    retrieved_run = db_service.get_pipeline_run(run.id)
    assert retrieved_run is not None
    assert retrieved_run.id == run.id
    assert retrieved_run.config == config

def test_update_pipeline_run_status(db_service):
    """Test updating a pipeline run's status."""
    # Create pipeline run
    run = db_service.create_pipeline_run()
    
    # Update status
    updated_run = db_service.update_pipeline_run_status(run.id, 'running', 'Test summary')
    assert updated_run is not None
    assert updated_run.status == 'running'
    assert updated_run.summary == 'Test summary'

def test_add_and_get_reddit_post(db_service):
    """Test adding and retrieving a Reddit post."""
    # Create pipeline run
    run = db_service.create_pipeline_run()
    
    post_data = {
        'id': 'test123',
        'title': 'Test Post',
        'content': 'Test Content',
        'subreddit': 'test',
        'url': 'http://test.com',
        'permalink': '/r/test/comments/test123'
    }
    
    # Add post
    post = db_service.add_reddit_post(run.id, post_data)
    assert post.post_id == 'test123'
    assert post.title == 'Test Post'
    
    # Get posts for pipeline run
    posts = db_service.get_reddit_posts(run.id)
    assert len(posts) == 1
    assert posts[0].post_id == 'test123'

def test_add_and_get_comment_summary(db_service):
    """Test adding and retrieving a comment summary."""
    # Create pipeline run and post
    run = db_service.create_pipeline_run()
    post = db_service.add_reddit_post(run.id, {
        'id': 'test123',
        'title': 'Test Post',
        'content': 'Test Content',
        'subreddit': 'test',
        'url': 'http://test.com'
    })
    
    # Add comment summary
    summary = "Test comment summary"
    comment = db_service.add_comment_summary(post.id, summary)
    assert comment.summary == summary
    assert comment.reddit_post_id == post.id

def test_add_and_get_product_info(db_service):
    """Test adding and retrieving product info."""
    # Create pipeline run and post
    run = db_service.create_pipeline_run()
    post = db_service.add_reddit_post(run.id, {
        'id': 'test123',
        'title': 'Test Post',
        'content': 'Test Content',
        'subreddit': 'test',
        'url': 'http://test.com'
    })
    
    product_data = {
        'theme': 'Test Theme',
        'image_url': 'http://test.com/image.jpg',
        'product_url': 'http://test.com/product',
        'affiliate_link': 'http://test.com/affiliate',
        'template_id': 'test-template',
        'model': 'test-model',
        'prompt_version': '1.0',
        'product_type': 'sticker',
        'design_description': 'Test design'
    }
    
    # Add product info
    product = db_service.add_product_info(run.id, post.id, product_data)
    assert product.theme == product_data['theme']
    assert product.image_url == product_data['image_url']
    
    # Get products for pipeline run
    products = db_service.get_product_infos(run.id)
    assert len(products) == 1
    assert products[0].theme == product_data['theme']

def test_log_and_get_error(db_service):
    """Test logging and retrieving errors."""
    # Create pipeline run
    run = db_service.create_pipeline_run()
    
    error_data = {
        'error_message': 'Test error',
        'error_type': 'TEST_ERROR',
        'component': 'TEST_COMPONENT',
        'stack_trace': 'Test stack trace',
        'context_data': {'test': 'data'},
        'severity': 'ERROR'
    }
    
    # Log error
    error = db_service.log_error(run.id, error_data)
    assert error.error_message == error_data['error_message']
    assert error.error_type == error_data['error_type']
    
    # Get errors for pipeline run
    errors = db_service.get_error_logs(run.id)
    assert len(errors) == 1
    assert errors[0].error_message == error_data['error_message']

def test_get_pipeline_runs_by_status(db_service):
    """Test getting pipeline runs filtered by status."""
    # Create pipeline runs with different statuses
    run1 = db_service.create_pipeline_run()
    run2 = db_service.create_pipeline_run()
    db_service.update_pipeline_run_status(run2.id, 'running')
    
    # Get all runs
    all_runs = db_service.get_pipeline_runs()
    assert len(all_runs) == 2
    
    # Get pending runs
    pending_runs = db_service.get_pipeline_runs(status='pending')
    assert len(pending_runs) == 1
    assert pending_runs[0].id == run1.id
    
    # Get running runs
    running_runs = db_service.get_pipeline_runs(status='running')
    assert len(running_runs) == 1
    assert running_runs[0].id == run2.id 