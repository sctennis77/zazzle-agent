import pytest
from app.db.database import engine, Base, SessionLocal, init_db
from app.db.models import PipelineRun, RedditPost, CommentSummary, ProductInfo, ErrorLog
from sqlalchemy.exc import IntegrityError
import uuid

def setup_module(module):
    # Drop and recreate all tables before the test module runs
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

def test_pipeline_run_crud():
    session = SessionLocal()
    # Create PipelineRun
    run = PipelineRun(status='started', summary='Test run')
    session.add(run)
    session.commit()
    assert run.id is not None

    # Create RedditPost
    post = RedditPost(
        pipeline_run_id=run.id,
        post_id=str(uuid.uuid4()),
        title='Test Post',
        content='This is a test post.',
        subreddit='golf',
        url='https://reddit.com/test'
    )
    session.add(post)
    session.commit()
    assert post.id is not None

    # Create CommentSummary
    comment = CommentSummary(reddit_post_id=post.id, summary='Great post!')
    session.add(comment)
    session.commit()
    assert comment.id is not None

    # Create ProductInfo
    product = ProductInfo(
        pipeline_run_id=run.id,
        reddit_post_id=post.id,
        theme='Golf Journey',
        image_url='https://imgur.com/test.png',
        product_url='https://zazzle.com/test',
        affiliate_link='https://zazzle.com/aff',
        template_id='tmpl123',
        model='dall-e-3',
        prompt_version='1.0.0',
        product_type='sticker',
        design_description='A golfer on a course.'
    )
    session.add(product)
    session.commit()
    assert product.id is not None

    # Create ErrorLog
    error = ErrorLog(pipeline_run_id=run.id, error_message='Something went wrong')
    session.add(error)
    session.commit()
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
    run = PipelineRun(status='started')
    session.add(run)
    session.commit()
    unique_id = str(uuid.uuid4())
    post1 = RedditPost(pipeline_run_id=run.id, post_id=unique_id, title='A', content='A', subreddit='golf', url='url')
    post2 = RedditPost(pipeline_run_id=run.id, post_id=unique_id, title='B', content='B', subreddit='golf', url='url2')
    session.add(post1)
    session.commit()
    session.add(post2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    session.close()

def test_error_log_without_pipeline_run():
    session = SessionLocal()
    error = ErrorLog(error_message='Orphan error log')
    session.add(error)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    session.close()

def test_cascade_delete_pipeline_run():
    session = SessionLocal()
    run = PipelineRun(status='to-delete')
    session.add(run)
    session.commit()
    post = RedditPost(pipeline_run_id=run.id, post_id=str(uuid.uuid4()), title='Del', content='Del', subreddit='golf', url='url')
    session.add(post)
    session.commit()
    product = ProductInfo(pipeline_run_id=run.id, reddit_post_id=post.id, theme='Del', image_url='url', product_url='url', affiliate_link='url', template_id='t', model='m', prompt_version='v', product_type='sticker', design_description='desc')
    session.add(product)
    session.commit()
    error = ErrorLog(pipeline_run_id=run.id, error_message='del')
    session.add(error)
    session.commit()
    # Delete pipeline run
    session.delete(run)
    session.commit()
    # Check that related records are also deleted or orphaned
    assert session.query(RedditPost).filter_by(title='Del').count() == 0
    assert session.query(ProductInfo).filter_by(theme='Del').count() == 0
    assert session.query(ErrorLog).filter_by(error_message='del').count() == 0
    session.close() 