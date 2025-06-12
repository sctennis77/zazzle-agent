import pytest
from app.db.database import engine, Base, SessionLocal, init_db
from app.db.models import PipelineRun, RedditPost, CommentSummary, ProductInfo, ErrorLog
from sqlalchemy.exc import IntegrityError
import uuid
from app.services.database_service import DatabaseService

def setup_module(module):
    # Drop and recreate all tables before the test module runs
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

def test_pipeline_run_crud():
    session = SessionLocal()
    db_service = DatabaseService(session)
    # Create PipelineRun
    run = db_service.create_pipeline_run({'status': 'started', 'summary': 'Test run'})
    assert run.id is not None

    # Create RedditPost
    post = db_service.add_reddit_post(run.id, {
        'id': str(uuid.uuid4()),
        'title': 'Test Post',
        'content': 'This is a test post.',
        'subreddit': 'golf',
        'url': 'https://reddit.com/test'
    })
    assert post.id is not None

    # Create CommentSummary
    comment = db_service.add_comment_summary(post.id, 'Great post!')
    assert comment.id is not None

    # Create ProductInfo
    product = db_service.add_product_info(run.id, post.id, {
        'theme': 'Golf Journey',
        'image_url': 'https://imgur.com/test.png',
        'product_url': 'https://zazzle.com/test',
        'affiliate_link': 'https://zazzle.com/aff',
        'template_id': 'tmpl123',
        'model': 'dall-e-3',
        'prompt_version': '1.0.0',
        'product_type': 'sticker',
        'design_description': 'A golfer on a course.'
    })
    assert product.id is not None

    # Create ErrorLog
    error = db_service.log_error(run.id, {'error_message': 'Something went wrong'})
    assert error.id is not None

    # Query relationships
    loaded_run = session.query(PipelineRun).filter_by(id=run.id).first()
    assert loaded_run.products[0].theme == 'Golf Journey'
    assert loaded_run.reddit_posts[0].title == 'Test Post'
    assert loaded_run.errors[0].error_message == 'Something went wrong'

    loaded_post = session.query(RedditPost).filter_by(id=post.id).first()
    assert loaded_post.comments[0].summary == 'Great post!'
    assert loaded_post.products[0].theme == 'Golf Journey'

    session.close()

def test_unique_post_id_constraint():
    session = SessionLocal()
    db_service = DatabaseService(session)
    run = db_service.create_pipeline_run({'status': 'started'})
    unique_id = str(uuid.uuid4())
    post1 = db_service.add_reddit_post(run.id, {
        'id': unique_id,
        'title': 'A',
        'content': 'A',
        'subreddit': 'golf',
        'url': 'url'
    })
    with pytest.raises(Exception):
        post2 = db_service.add_reddit_post(run.id, {
            'id': unique_id,
            'title': 'B',
            'content': 'B',
            'subreddit': 'golf',
            'url': 'url2'
        })
    session.rollback()
    session.close()

def test_error_log_without_pipeline_run():
    session = SessionLocal()
    db_service = DatabaseService(session)
    with pytest.raises(Exception):
        db_service.log_error(None, {'error_message': 'Orphan error log'})
    session.rollback()
    session.close()

def test_cascade_delete_pipeline_run():
    session = SessionLocal()
    db_service = DatabaseService(session)
    run = db_service.create_pipeline_run({'status': 'to-delete'})
    post = db_service.add_reddit_post(run.id, {
        'id': str(uuid.uuid4()),
        'title': 'Del',
        'content': 'Del',
        'subreddit': 'golf',
        'url': 'url'
    })
    product = db_service.add_product_info(run.id, post.id, {
        'theme': 'Del',
        'image_url': 'url',
        'product_url': 'url',
        'affiliate_link': 'url',
        'template_id': 't',
        'model': 'm',
        'prompt_version': 'v',
        'product_type': 'sticker',
        'design_description': 'desc'
    })
    error = db_service.log_error(run.id, {'error_message': 'del'})
    # Delete pipeline run
    session.delete(run)
    session.commit()
    # Check that related records are also deleted or orphaned
    assert session.query(RedditPost).filter_by(title='Del').count() == 0
    assert session.query(ProductInfo).filter_by(theme='Del').count() == 0
    assert session.query(ErrorLog).filter_by(error_message='del').count() == 0
    session.close() 