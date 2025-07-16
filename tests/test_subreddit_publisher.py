"""
Tests for the SubredditPublisher class.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.models import (
    GeneratedProductSchema,
    PipelineRunSchema,
    PipelineRunUsageSchema,
    ProductInfoSchema,
    RedditPostSchema,
)
from app.subreddit_publisher import SubredditPublisher


class TestSubredditPublisher:
    """Test cases for SubredditPublisher."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return Mock()

    @pytest.fixture
    def mock_reddit_client(self):
        """Create a mock Reddit client."""
        client = Mock()
        client.submit_image_post.return_value = {
            "type": "image_post",
            "action": "would submit image post",
            "subreddit": "clouvel",
            "title": "Test Title",
            "content": "Test Content",
            "image_url": "https://example.com/image.jpg",
            "post_id": "dryrun_post_id",
            "post_url": "https://reddit.com/r/clouvel/comments/dryrun_post_id",
        }
        return client

    @pytest.fixture
    def sample_generated_product(self):
        """Create a sample GeneratedProductSchema for testing."""
        product_info = ProductInfoSchema(
            id=1,
            pipeline_run_id=1,
            reddit_post_id=1,
            theme="Test Theme",
            image_title="Test Image",
            image_url="https://example.com/image.jpg",
            product_url="https://zazzle.com/product",
            affiliate_link="https://zazzle.com/product?ref=test",
            template_id="test_template",
            model="dall-e-3",
            prompt_version="1.0.0",
            product_type="sticker",
            design_description="Test design description",
            available_actions={},
            donation_info={},
        )

        reddit_post = RedditPostSchema(
            id=1,
            pipeline_run_id=1,
            post_id="test_post_id",
            title="Original Reddit Post",
            content="Original post content",
            subreddit="golf",
            url="https://reddit.com/r/golf/comments/test_post_id",
            permalink="/r/golf/comments/test_post_id",
            comment_summary="Test comment summary",
            author="test_user",
            score=100,
            num_comments=50,
        )

        pipeline_run = PipelineRunSchema(
            id=1,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            status="completed",
            summary="Test pipeline run",
            config={},
            metrics={},
            duration=60,
            retry_count=0,
            last_error=None,
            version="1.0.0",
        )

        return GeneratedProductSchema(
            product_info=product_info,
            pipeline_run=pipeline_run,
            reddit_post=reddit_post,
            usage=None,
        )

    @patch("app.subreddit_publisher.RedditClient")
    @patch("app.subreddit_publisher.SessionLocal")
    def test_init(self, mock_session_local, mock_reddit_client_class, mock_session):
        """Test SubredditPublisher initialization."""
        mock_session_local.return_value = mock_session
        mock_reddit_client_class.return_value = Mock()

        publisher = SubredditPublisher(dry_run=True, session=mock_session)

        assert publisher.dry_run is True
        assert publisher.subreddit == "clouvel"
        assert publisher.session == mock_session
        assert publisher.reddit_client is not None

    @patch("app.subreddit_publisher.RedditClient")
    @patch("app.subreddit_publisher.SessionLocal")
    def test_get_product_from_db_success(
        self,
        mock_session_local,
        mock_reddit_client_class,
        mock_session,
        sample_generated_product,
    ):
        """Test successful product retrieval from database."""
        # Mock the database queries
        mock_product_info = Mock()
        mock_reddit_post = Mock()
        mock_pipeline_run = Mock()
        mock_usage = Mock()

        # Set up the mock objects to return the expected data
        mock_product_info.id = 1
        mock_reddit_post.id = 1
        mock_pipeline_run.id = 1

        mock_session.query.return_value.filter.return_value.first.side_effect = [
            mock_product_info,  # ProductInfo query
            mock_reddit_post,  # RedditPost query
            mock_pipeline_run,  # PipelineRun query
            mock_usage,  # PipelineRunUsage query
        ]

        mock_session_local.return_value = mock_session
        mock_reddit_client_class.return_value = Mock()

        publisher = SubredditPublisher(dry_run=True, session=mock_session)

        # Mock the schema conversion
        with (
            patch.object(
                ProductInfoSchema,
                "from_orm",
                return_value=sample_generated_product.product_info,
            ),
            patch.object(
                RedditPostSchema,
                "from_orm",
                return_value=sample_generated_product.reddit_post,
            ),
            patch.object(
                PipelineRunSchema,
                "from_orm",
                return_value=sample_generated_product.pipeline_run,
            ),
            patch.object(PipelineRunUsageSchema, "from_orm", return_value=None),
        ):

            result = publisher.get_product_from_db("1")

            assert result is not None
            assert isinstance(result, GeneratedProductSchema)
            assert result.product_info.id == 1
            assert result.reddit_post.subreddit == "golf"

    @patch("app.subreddit_publisher.RedditClient")
    @patch("app.subreddit_publisher.SessionLocal")
    def test_get_product_from_db_not_found(
        self, mock_session_local, mock_reddit_client_class, mock_session
    ):
        """Test product retrieval when product is not found."""
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session_local.return_value = mock_session
        mock_reddit_client_class.return_value = Mock()

        publisher = SubredditPublisher(dry_run=True, session=mock_session)

        result = publisher.get_product_from_db("999")

        assert result is None

    def test_submit_image_post(self, sample_generated_product):
        """Test image post submission."""
        import io
        from unittest.mock import MagicMock, patch

        from PIL import Image

        # Create a minimal valid PNG image for testing
        test_image = Image.new("RGB", (10, 10), color="red")
        img_buffer = io.BytesIO()
        test_image.save(img_buffer, format="JPEG")
        img_buffer.seek(0)
        fake_image_bytes = img_buffer.read()

        # Patch requests.get to return a fake response with image bytes
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = fake_image_bytes
            mock_response.raise_for_status = lambda: None
            mock_get.return_value = mock_response

            publisher = SubredditPublisher(dry_run=True)
            result = publisher.submit_image_post(sample_generated_product)

        assert result["type"] == "image_post"
        assert result["action"] == "would submit image post"
        assert result["subreddit"] == "clouvel"
        assert result["title"] == "🎨 Test Image - commissioned by u/test_user"
        assert "Commissioned Artwork: Test Theme" in result["content"]
        assert result["image_url"] == "https://example.com/image.jpg"

    @patch("app.subreddit_publisher.RedditClient")
    @patch("app.subreddit_publisher.SessionLocal")
    def test_submit_image_post_with_reddit_client(
        self,
        mock_session_local,
        mock_reddit_client_class,
        mock_reddit_client,
        sample_generated_product,
    ):
        """Test submitting an image post using the Reddit client."""
        mock_session_local.return_value = Mock()
        mock_reddit_client_class.return_value = mock_reddit_client

        publisher = SubredditPublisher(dry_run=True)

        result = publisher.submit_image_post(sample_generated_product)

        mock_reddit_client.submit_image_post.assert_called_once_with(
            subreddit_name="clouvel",
            title="🎨 Test Image - commissioned by u/test_user",
            content=mock_reddit_client.submit_image_post.call_args[1]["content"],
            image_url="https://example.com/image.jpg",
        )
        assert result is not None

    @patch("app.subreddit_publisher.RedditClient")
    @patch("app.subreddit_publisher.SessionLocal")
    def test_publish_product_success(
        self,
        mock_session_local,
        mock_reddit_client_class,
        mock_session,
        sample_generated_product,
        mock_reddit_client,
    ):
        """Test successful product publication."""
        # Mock the database queries
        mock_product_info = Mock()
        mock_reddit_post = Mock()
        mock_pipeline_run = Mock()
        mock_usage = Mock()

        mock_product_info.id = 1
        mock_reddit_post.id = 1
        mock_pipeline_run.id = 1

        # Mock the queries: ProductInfo exists, ProductSubredditPost doesn't exist
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            mock_product_info,  # ProductInfo query (get_product_from_db)
            mock_reddit_post,  # RedditPost query (get_product_from_db)
            mock_pipeline_run,  # PipelineRun query (get_product_from_db)
            mock_usage,  # PipelineRunUsage query (get_product_from_db)
            None,  # ProductSubredditPost query (_is_product_already_posted) - no existing post
        ]

        mock_session_local.return_value = mock_session
        mock_reddit_client_class.return_value = mock_reddit_client

        publisher = SubredditPublisher(dry_run=True, session=mock_session)

        # Mock the schema conversion
        with (
            patch.object(
                ProductInfoSchema,
                "from_orm",
                return_value=sample_generated_product.product_info,
            ),
            patch.object(
                RedditPostSchema,
                "from_orm",
                return_value=sample_generated_product.reddit_post,
            ),
            patch.object(
                PipelineRunSchema,
                "from_orm",
                return_value=sample_generated_product.pipeline_run,
            ),
            patch.object(PipelineRunUsageSchema, "from_orm", return_value=None),
        ):

            result = publisher.publish_product("1")

            assert result["success"] is True
            assert result["product_id"] == "1"
            assert result["subreddit"] == "clouvel"
            assert result["dry_run"] is True
            assert "submitted_post" in result
            assert "saved_post" in result

    @patch("app.subreddit_publisher.RedditClient")
    @patch("app.subreddit_publisher.SessionLocal")
    def test_publish_product_not_found(
        self, mock_session_local, mock_reddit_client_class, mock_session
    ):
        """Test product publication when product is not found."""
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session_local.return_value = mock_session
        mock_reddit_client_class.return_value = Mock()

        publisher = SubredditPublisher(dry_run=True, session=mock_session)

        result = publisher.publish_product("999")

        assert result["success"] is False
        assert "Product with ID 999 not found" in result["error"]
        assert result["dry_run"] is True

    @patch("app.subreddit_publisher.RedditClient")
    @patch("app.subreddit_publisher.SessionLocal")
    def test_publish_product_already_posted(
        self, mock_session_local, mock_reddit_client_class, mock_session
    ):
        """Test product publication when product has already been posted."""
        # Mock existing ProductSubredditPost
        mock_existing_post = Mock()
        mock_existing_post.subreddit_name = "clouvel"
        mock_existing_post.reddit_post_id = "abc123"
        mock_existing_post.dry_run = True

        # Mock ProductInfo exists but ProductSubredditPost also exists
        mock_product_info = Mock()
        mock_reddit_post = Mock()
        mock_pipeline_run = Mock()
        mock_usage = Mock()

        mock_product_info.id = 1
        mock_reddit_post.id = 1
        mock_pipeline_run.id = 1

        # Mock the queries: ProductInfo exists, but ProductSubredditPost also exists
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            mock_product_info,  # ProductInfo query (get_product_from_db)
            mock_reddit_post,  # RedditPost query (get_product_from_db)
            mock_pipeline_run,  # PipelineRun query (get_product_from_db)
            mock_usage,  # PipelineRunUsage query (get_product_from_db)
            mock_existing_post,  # ProductSubredditPost query (_is_product_already_posted) - existing post found
        ]

        mock_session_local.return_value = mock_session
        mock_reddit_client_class.return_value = Mock()

        publisher = SubredditPublisher(dry_run=True, session=mock_session)

        # Create proper mock schemas with required attributes to avoid Pydantic validation errors
        mock_product_schema = Mock()
        mock_product_schema.id = 1
        mock_product_schema.pipeline_run_id = 1
        mock_product_schema.reddit_post_id = 1
        mock_product_schema.theme = "Test Theme"
        mock_product_schema.image_title = "Test Image"
        mock_product_schema.image_url = "https://example.com/image.jpg"
        mock_product_schema.product_url = "https://zazzle.com/product"
        mock_product_schema.affiliate_link = "https://zazzle.com/product?ref=test"
        mock_product_schema.template_id = "test_template"
        mock_product_schema.model = "dall-e-3"
        mock_product_schema.prompt_version = "1.0.0"
        mock_product_schema.product_type = "sticker"
        mock_product_schema.design_description = "Test design description"
        mock_product_schema.image_quality = "standard"
        mock_product_schema.available_actions = {}
        mock_product_schema.donation_info = {}

        mock_reddit_schema = Mock()
        mock_reddit_schema.id = 1
        mock_reddit_schema.pipeline_run_id = 1
        mock_reddit_schema.post_id = "test_post_id"
        mock_reddit_schema.title = "Original Reddit Post"
        mock_reddit_schema.content = "Original post content"
        mock_reddit_schema.subreddit = "golf"
        mock_reddit_schema.url = "https://reddit.com/r/golf/comments/test_post_id"
        mock_reddit_schema.permalink = "/r/golf/comments/test_post_id"
        mock_reddit_schema.comment_summary = "Test comment summary"
        mock_reddit_schema.author = "test_user"
        mock_reddit_schema.score = 100
        mock_reddit_schema.num_comments = 50

        mock_pipeline_schema = Mock()
        mock_pipeline_schema.id = 1
        mock_pipeline_schema.start_time = datetime.now(timezone.utc)
        mock_pipeline_schema.end_time = datetime.now(timezone.utc)
        mock_pipeline_schema.status = "completed"
        mock_pipeline_schema.summary = "Test pipeline run"
        mock_pipeline_schema.config = {}
        mock_pipeline_schema.metrics = {}
        mock_pipeline_schema.duration = 60
        mock_pipeline_schema.retry_count = 0
        mock_pipeline_schema.last_error = None
        mock_pipeline_schema.version = "1.0.0"

        # Mock the schema conversion to return proper mock objects
        with (
            patch.object(
                ProductInfoSchema, "from_orm", return_value=mock_product_schema
            ),
            patch.object(RedditPostSchema, "from_orm", return_value=mock_reddit_schema),
            patch.object(
                PipelineRunSchema, "from_orm", return_value=mock_pipeline_schema
            ),
            patch.object(PipelineRunUsageSchema, "from_orm", return_value=None),
        ):

            result = publisher.publish_product("1")

            assert result["success"] is False
            assert "has already been posted" in result["error"]
            assert result["dry_run"] is True

    def test_close(self, mock_session):
        """Test closing the database session."""
        publisher = SubredditPublisher(dry_run=True, session=mock_session)
        publisher.close()

        mock_session.close.assert_called_once()

    def test_dry_run_cleanup_when_going_live(self, mock_session):
        """Test that dry run posts are cleaned up when publishing in live mode."""
        # Mock existing dry run ProductSubredditPost
        mock_existing_post = Mock()
        mock_existing_post.dry_run = True
        mock_existing_post.reddit_post_id = "dryrun_post_id"
        
        mock_session.query.return_value.filter.return_value.first.return_value = mock_existing_post
        
        # Create publisher in LIVE mode (dry_run=False)
        publisher = SubredditPublisher(dry_run=False, session=mock_session)
        
        # Should return False (not already posted) after deleting dry run post
        result = publisher._is_product_already_posted("1")
        
        assert result is False
        mock_session.delete.assert_called_once_with(mock_existing_post)
        mock_session.commit.assert_called_once()

    def test_live_post_blocks_republishing(self, mock_session):
        """Test that existing live posts still block republishing."""
        # Mock existing live ProductSubredditPost
        mock_existing_post = Mock()
        mock_existing_post.dry_run = False
        mock_existing_post.reddit_post_id = "live_post_id"
        
        mock_session.query.return_value.filter.return_value.first.return_value = mock_existing_post
        
        # Create publisher in LIVE mode
        publisher = SubredditPublisher(dry_run=False, session=mock_session)
        
        # Should return True (already posted) and NOT delete the post
        result = publisher._is_product_already_posted("1")
        
        assert result is True
        mock_session.delete.assert_not_called()
        mock_session.commit.assert_not_called()
