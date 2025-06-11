import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.agents.reddit_agent import RedditAgent
from app.db.database import SessionLocal, Base, engine
from app.db.models import PipelineRun, RedditPost
from app.models import PipelineConfig
import asyncio

@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    # Drop and recreate all tables before each test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.mark.asyncio
def test_reddit_agent_persists_reddit_post(monkeypatch):
    # Create a pipeline run and session
    session = SessionLocal()
    pipeline_run = PipelineRun(status='started')
    session.add(pipeline_run)
    session.commit()
    pipeline_run_id = pipeline_run.id

    # Mock trending post
    mock_post = MagicMock()
    mock_post.id = 'mock123'
    mock_post.title = 'Mock Post Title'
    mock_post.url = 'https://reddit.com/r/golf/comments/mock123/mock_post_title/'
    mock_post.subreddit.display_name = 'golf'
    mock_post.selftext = 'This is a mock post.'
    mock_post.permalink = '/r/golf/comments/mock123/mock_post_title/'
    mock_post.comment_summary = 'Mock comment summary'

    # Patch _find_trending_post to return the mock post
    monkeypatch.setattr(RedditAgent, '_find_trending_post', AsyncMock(return_value=mock_post))
    # Patch image generation and product designer to avoid side effects
    monkeypatch.setattr(RedditAgent, '_determine_product_idea', lambda self, ctx: MagicMock(theme='Theme', image_description='desc', design_instructions={'image': None, 'theme': 'Theme'}, reddit_context=ctx, model='dall-e-3', prompt_version='1.0.0'))
    monkeypatch.setattr('app.agents.reddit_agent.ImageGenerator.generate_image', AsyncMock(return_value=('mock_imgur_url', 'mock_local_path')))
    monkeypatch.setattr('app.agents.reddit_agent.ZazzleProductDesigner.create_product', AsyncMock(return_value=MagicMock()))

    # Create RedditAgent with session and pipeline_run_id
    config = PipelineConfig(
        model='dall-e-3',
        zazzle_template_id='test_template_id',
        zazzle_tracking_code='test_tracking_code',
        prompt_version='1.0.0'
    )
    agent = RedditAgent(config, pipeline_run_id=pipeline_run_id, session=session)
    # Run find_and_create_product
    asyncio.run(agent.find_and_create_product())
    # Check that a RedditPost was created in the DB
    posts = session.query(RedditPost).filter_by(post_id='mock123').all()
    assert len(posts) == 1
    post = posts[0]
    assert post.title == 'Mock Post Title'
    assert post.subreddit == 'golf'
    assert post.content == 'This is a mock post.'
    assert post.pipeline_run_id == pipeline_run_id
    session.close() 