import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.agents.reddit_agent import RedditAgent
from app.db.database import SessionLocal, Base, engine
from app.db.models import PipelineRun, RedditPost
from app.models import PipelineConfig
from app.models import ProductIdea
from app.models import RedditContext
from types import SimpleNamespace
from app.services.database_service import DatabaseService

@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    # Drop and recreate all tables before each test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.mark.asyncio
def test_reddit_agent_persists_reddit_post(monkeypatch):
    session = SessionLocal()
    pipeline_run = PipelineRun(status='started')
    session.add(pipeline_run)
    session.commit()
    pipeline_run_id = pipeline_run.id

    mock_post = SimpleNamespace(
        id='mock123',
        title='Mock Post Title',
        url='https://reddit.com/r/golf/comments/mock123/mock_post_title/',
        subreddit=SimpleNamespace(display_name='golf'),
        selftext='This is a mock post.',
        permalink='/r/golf/comments/mock123/mock_post_title/',
        comment_summary='Mock comment summary'
    )

    monkeypatch.setattr(RedditAgent, '_find_trending_post', AsyncMock(return_value=mock_post))
    monkeypatch.setattr(RedditAgent, '_determine_product_idea', lambda self, ctx: ProductIdea(
        theme='Theme',
        image_description='desc',
        design_instructions={'image': 'mock_imgur_url', 'theme': 'Theme'},
        reddit_context=type('RedditContext', (), dict(
            post_id='mock123',
            post_title='Mock Post Title',
            post_url='https://reddit.com/r/golf/comments/mock123/mock_post_title/',
            subreddit='golf',
            post_content='This is a mock post.',
            comments=[{'text': 'Mock comment summary'}],
            permalink='/r/golf/comments/mock123/mock_post_title/'
        ))(),
        model='dall-e-3',
        prompt_version='1.0.0'
    ))
    monkeypatch.setattr('app.image_generator.ImageGenerator.generate_image', AsyncMock(return_value=(
        'mock_imgur_url', 'mock_local_path')))
    monkeypatch.setattr('app.agents.reddit_agent.ZazzleProductDesigner.create_product', AsyncMock(return_value=MagicMock()))

    config = PipelineConfig(
        model='dall-e-3',
        zazzle_template_id='test_template_id',
        zazzle_tracking_code='test_tracking_code',
        prompt_version='1.0.0'
    )
    agent = RedditAgent(config, pipeline_run_id=pipeline_run_id, session=session)
    
    db_service = DatabaseService(session)
    # Await the async method
    import asyncio
    loop = asyncio.get_event_loop()
    product_info = loop.run_until_complete(agent.find_and_create_product())
    # Persist RedditContext to DB
    real_context = RedditContext(
        post_id='mock123',
        post_title='Mock Post Title',
        post_url='https://reddit.com/r/golf/comments/mock123/mock_post_title/',
        subreddit='golf',
        post_content='This is a mock post.',
        comments=[{'text': 'Mock comment summary'}],
        permalink='/r/golf/comments/mock123/mock_post_title/'
    )
    db_service.add_reddit_post(pipeline_run_id, {
        'id': real_context.post_id,
        'title': real_context.post_title,
        'content': real_context.post_content,
        'subreddit': real_context.subreddit,
        'url': real_context.post_url,
        'permalink': real_context.permalink
    })
    session.commit()
    posts = session.query(RedditPost).filter_by(post_id='mock123').all()
    assert len(posts) == 1
    post = posts[0]
    assert post.post_id == 'mock123'
    assert post.title == 'Mock Post Title'
    assert post.url == 'https://reddit.com/r/golf/comments/mock123/mock_post_title/'
    assert post.subreddit == 'golf'
    assert post.content == 'This is a mock post.'
    assert post.permalink == '/r/golf/comments/mock123/mock_post_title/'
    session.close() 