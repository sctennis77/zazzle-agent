import os
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import PipelineRun, ProductInfo, RedditPost, Subreddit
from app.models import GeneratedProductSchema, PipelineRunSchema
from app.models import ProductInfo as ProductInfoDataClass
from app.models import ProductInfoSchema, RedditContext, RedditPostSchema

# Create an in-memory SQLite database for testing
engine = create_engine("sqlite:///:memory:")
Session = sessionmaker(bind=engine)


def create_test_data():
    """Create test data in the database."""
    from app.db.models import Base

    Base.metadata.create_all(engine)

    session = Session()

    # Create a subreddit first
    subreddit = Subreddit(id=1, subreddit_name="test", display_name="Test Subreddit")
    session.add(subreddit)

    # Create a pipeline run
    pipeline_run = PipelineRun(
        id=1, start_time=datetime.now(timezone.utc), status="completed", retry_count=0
    )
    session.add(pipeline_run)

    # Create a reddit post
    reddit_post = RedditPost(
        id=1,
        pipeline_run_id=1,
        post_id="test123",
        title="Test Post",
        content="Test Content",
        subreddit_id=1,  # Use the subreddit ID instead of string
        url="https://reddit.com/test",
        permalink="/r/test/test123",
        author="test_user",
        score=100,
        num_comments=25,
    )
    session.add(reddit_post)

    # Create a product info
    product_info = ProductInfo(
        id=1,
        pipeline_run_id=1,
        reddit_post_id=1,
        theme="Test Theme",
        image_url="https://example.com/image.jpg",
        product_url="https://zazzle.com/product",
        template_id="template123",
        model="dall-e-3",
        prompt_version="1.0.0",
        product_type="sticker",
        design_description="Test design",
    )
    session.add(product_info)

    session.commit()
    return session


def test_serialization():
    """Test the serialization of models to Pydantic schemas."""
    session = create_test_data()

    # Fetch the test data
    pipeline_run = session.query(PipelineRun).first()
    product_info = session.query(ProductInfo).first()
    reddit_post = session.query(RedditPost).first()

    # Test individual schema conversions
    pipeline_schema = PipelineRunSchema.model_validate(pipeline_run)
    product_schema = ProductInfoSchema.model_validate(product_info)
    reddit_schema = RedditPostSchema.model_validate(reddit_post)

    # Test combined schema
    combined = GeneratedProductSchema(
        product_info=product_schema,
        pipeline_run=pipeline_schema,
        reddit_post=reddit_schema,
    )

    # Verify the data
    assert combined.product_info.theme == "Test Theme"
    assert combined.pipeline_run.status == "completed"
    assert combined.reddit_post.post_id == "test123"

    # Test JSON serialization
    json_data = combined.model_dump_json()
    assert isinstance(json_data, str)

    # Test deserialization
    deserialized = GeneratedProductSchema.model_validate_json(json_data)
    assert deserialized.product_info.theme == "Test Theme"

    session.close()


if __name__ == "__main__":
    test_serialization()
    print("All tests passed!")
