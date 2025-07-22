"""
Tests for the new Reddit interaction API endpoints.

Tests the clean comment vs post separation introduced in the Reddit interaction refactor.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import app, get_db
from app.db.models import (
    Base,
    PipelineRun,
    ProductInfo,
    ProductRedditComment,
    ProductSubredditPost,
    RedditPost,
    Subreddit,
)
from app.pipeline_status import PipelineStatus

# Create test database
TEST_DATABASE_URL = "sqlite:///./test_reddit_interaction.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables
Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override the get_db dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    """Setup and teardown database for each test."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables after test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Create test client with database override."""
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def db_session():
    """Create a database session for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_product_data(db_session):
    """Create sample product data for testing."""
    # Create or get subreddit
    subreddit = db_session.query(Subreddit).filter_by(subreddit_name="test").first()
    if not subreddit:
        subreddit = Subreddit(subreddit_name="test")
        db_session.add(subreddit)
        db_session.flush()

    # Create pipeline run
    pipeline_run = PipelineRun(
        start_time=datetime(2024, 1, 1, 0, 0, 0),
        end_time=datetime(2024, 1, 1, 1, 0, 0),
        status=PipelineStatus.COMPLETED.value,
        retry_count=0,
    )
    db_session.add(pipeline_run)
    db_session.flush()

    # Create reddit post
    reddit_post = RedditPost(
        pipeline_run_id=pipeline_run.id,
        post_id="test123",
        title="Test Post",
        content="Test content",
        subreddit_id=subreddit.id,
        url="https://reddit.com/r/test/comments/test123",
        permalink="/r/test/comments/test123",
    )
    db_session.add(reddit_post)
    db_session.flush()

    # Create product info
    product_info = ProductInfo(
        pipeline_run_id=pipeline_run.id,
        reddit_post_id=reddit_post.id,
        theme="Test Theme",
        image_url="https://example.com/image.jpg",
        product_url="https://zazzle.com/product",
        template_id="template123",
        model="dall-e-3",
        prompt_version="1.0.0",
        product_type="sticker",
        design_description="Test design",
        image_quality="standard",
    )
    db_session.add(product_info)
    db_session.commit()

    return {
        "pipeline_run": pipeline_run,
        "reddit_post": reddit_post,
        "product_info": product_info,
    }


class TestRedditCommentEndpoints:
    """Test comment-specific endpoints."""

    def test_get_product_comment_not_found(self, client, sample_product_data):
        """Test getting a comment that doesn't exist."""
        product_id = sample_product_data["product_info"].id
        response = client.get(f"/api/reddit/product/{product_id}/comment")
        assert response.status_code == 404
        assert "No Reddit comment found" in response.json()["detail"]

    def test_get_product_comment_exists(self, client, sample_product_data, db_session):
        """Test getting an existing comment."""
        product_id = sample_product_data["product_info"].id

        # Create a comment
        comment = ProductRedditComment(
            product_info_id=product_id,
            original_post_id="test123",
            comment_id="comment456",
            comment_url="https://reddit.com/r/test/comments/test123/comment456",
            subreddit_name="test",
            commented_at=datetime(2024, 1, 1, 12, 0, 0),
            comment_content="Test comment content",
            dry_run=True,
            status="success",
        )
        db_session.add(comment)
        db_session.commit()

        response = client.get(f"/api/reddit/product/{product_id}/comment")
        assert response.status_code == 200
        data = response.json()
        assert data["product_info_id"] == product_id
        assert data["comment_content"] == "Test comment content"
        assert data["dry_run"] is True

    @patch("app.api.RedditCommenter")
    def test_submit_product_comment_success(
        self, mock_commenter_class, client, sample_product_data
    ):
        """Test successful comment submission."""
        product_id = sample_product_data["product_info"].id

        # Mock the commenter
        mock_commenter = Mock()
        mock_commenter_class.return_value = mock_commenter
        mock_commenter.comment_on_original_post.return_value = {
            "id": 1,
            "product_info_id": product_id,
            "original_post_id": "test123",
            "comment_id": "comment456",
            "comment_url": "https://reddit.com/r/test/comments/test123/comment456",
            "subreddit": "test",
            "commented_at": datetime(2024, 1, 1, 12, 0, 0).isoformat(),
            "comment_content": "Test comment content",
            "dry_run": True,
            "status": "success",
        }

        response = client.post(f"/api/reddit/product/{product_id}/comment?dry_run=true")
        assert response.status_code == 200
        data = response.json()
        assert data["product_info_id"] == product_id
        assert data["dry_run"] is True

        # Verify commenter was called correctly
        mock_commenter_class.assert_called_once()
        mock_commenter.comment_on_original_post.assert_called_once_with(str(product_id))

    @patch("app.api.RedditCommenter")
    def test_submit_product_comment_failure(
        self, mock_commenter_class, client, sample_product_data
    ):
        """Test comment submission failure."""
        product_id = sample_product_data["product_info"].id

        # Mock the commenter to raise an exception
        mock_commenter = Mock()
        mock_commenter_class.return_value = mock_commenter
        mock_commenter.comment_on_original_post.side_effect = Exception(
            "Reddit API error"
        )

        response = client.post(f"/api/reddit/product/{product_id}/comment")
        assert response.status_code == 500
        assert "Failed to submit comment" in response.json()["detail"]


class TestRedditPostEndpoints:
    """Test post-specific endpoints."""

    def test_get_product_post_not_found(self, client, sample_product_data):
        """Test getting a post that doesn't exist."""
        product_id = sample_product_data["product_info"].id
        response = client.get(f"/api/reddit/product/{product_id}/post")
        assert response.status_code == 404
        assert "No Reddit post found" in response.json()["detail"]

    def test_get_product_post_exists(self, client, sample_product_data, db_session):
        """Test getting an existing post."""
        product_id = sample_product_data["product_info"].id

        # Create a post
        post = ProductSubredditPost(
            product_info_id=product_id,
            subreddit_name="clouvel",
            reddit_post_id="post789",
            reddit_post_url="https://reddit.com/r/clouvel/comments/post789",
            reddit_post_title="Test Post Title",
            submitted_at=datetime(2024, 1, 1, 12, 0, 0),
            dry_run=False,
            status="success",
        )
        db_session.add(post)
        db_session.commit()

        response = client.get(f"/api/reddit/product/{product_id}/post")
        assert response.status_code == 200
        data = response.json()
        assert data["product_info_id"] == product_id
        assert data["subreddit_name"] == "clouvel"
        assert data["dry_run"] is False

    def test_submit_product_post_success(self, client, sample_product_data, db_session):
        """Test successful post submission."""
        product_id = sample_product_data["product_info"].id

        # Create a post that will be "found" after publication
        post = ProductSubredditPost(
            product_info_id=product_id,
            subreddit_name="clouvel",
            reddit_post_id="post789",
            reddit_post_url="https://reddit.com/r/clouvel/comments/post789",
            reddit_post_title="Test Post Title",
            submitted_at=datetime(2024, 1, 1, 12, 0, 0),
            dry_run=True,
            status="success",
        )
        db_session.add(post)
        db_session.commit()

        # Mock the publisher
        with patch(
            "app.subreddit_publisher.SubredditPublisher"
        ) as mock_publisher_class:
            mock_publisher = Mock()
            mock_publisher_class.return_value = mock_publisher
            mock_publisher.publish_product.return_value = {"success": True}

            response = client.post(
                f"/api/reddit/product/{product_id}/post?dry_run=true"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["product_info_id"] == product_id
            assert data["subreddit_name"] == "clouvel"

            # Verify publisher was called correctly
            mock_publisher_class.assert_called_once()
            mock_publisher.publish_product.assert_called_once_with(str(product_id))


class TestUnifiedInteractionEndpoint:
    """Test the unified interaction endpoint with mode parameter."""

    def test_get_interaction_comment_mode(
        self, client, sample_product_data, db_session
    ):
        """Test getting interaction in comment mode."""
        product_id = sample_product_data["product_info"].id

        # Create a comment
        comment = ProductRedditComment(
            product_info_id=product_id,
            original_post_id="test123",
            comment_id="comment456",
            subreddit_name="test",
            commented_at=datetime(2024, 1, 1, 12, 0, 0),
            dry_run=True,
            status="success",
        )
        db_session.add(comment)
        db_session.commit()

        response = client.get(
            f"/api/reddit/product/{product_id}/interaction?mode=comment"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["product_info_id"] == product_id
        assert "comment_id" in data  # This indicates it's a comment response

    def test_get_interaction_post_mode(self, client, sample_product_data, db_session):
        """Test getting interaction in post mode."""
        product_id = sample_product_data["product_info"].id

        # Create a post
        post = ProductSubredditPost(
            product_info_id=product_id,
            subreddit_name="clouvel",
            reddit_post_id="post789",
            submitted_at=datetime(2024, 1, 1, 12, 0, 0),
            dry_run=False,
            status="success",
        )
        db_session.add(post)
        db_session.commit()

        response = client.get(f"/api/reddit/product/{product_id}/interaction?mode=post")
        assert response.status_code == 200
        data = response.json()
        assert data["product_info_id"] == product_id
        assert "reddit_post_id" in data  # This indicates it's a post response

    def test_get_interaction_invalid_mode(self, client, sample_product_data):
        """Test getting interaction with invalid mode."""
        product_id = sample_product_data["product_info"].id

        response = client.get(
            f"/api/reddit/product/{product_id}/interaction?mode=invalid"
        )
        assert response.status_code == 400
        assert "Invalid interaction mode" in response.json()["detail"]

    def test_get_interaction_default_mode(
        self, client, sample_product_data, db_session
    ):
        """Test getting interaction with default mode (comment)."""
        product_id = sample_product_data["product_info"].id

        # Create a comment (should be found by default mode)
        comment = ProductRedditComment(
            product_info_id=product_id,
            original_post_id="test123",
            subreddit_name="test",
            commented_at=datetime(2024, 1, 1, 12, 0, 0),
            dry_run=True,
            status="success",
        )
        db_session.add(comment)
        db_session.commit()

        # No mode parameter - should default to comment
        response = client.get(f"/api/reddit/product/{product_id}/interaction")
        assert response.status_code == 200
        data = response.json()
        assert "comment_id" in data or "original_post_id" in data  # Comment response


class TestBackwardCompatibility:
    """Test that legacy endpoints still work."""

    def test_legacy_publish_endpoint_still_works(
        self, client, sample_product_data, db_session
    ):
        """Test that the old /api/publish/product/{id} endpoint still works."""
        product_id = sample_product_data["product_info"].id

        # Create a comment that should be returned by the legacy endpoint
        comment = ProductRedditComment(
            product_info_id=product_id,
            original_post_id="test123",
            subreddit_name="test",
            commented_at=datetime(2024, 1, 1, 12, 0, 0),
            dry_run=True,
            status="success",
        )
        db_session.add(comment)
        db_session.commit()

        response = client.get(f"/api/publish/product/{product_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["product_info_id"] == product_id
