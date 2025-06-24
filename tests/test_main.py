import csv
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, Mock, mock_open, patch

import pytest

from app.affiliate_linker import ZazzleAffiliateLinker
from app.agents.reddit_agent import AVAILABLE_SUBREDDITS, RedditAgent
from app.content_generator import ContentGenerator
from app.db.database import Base, engine
from app.main import (
    ensure_output_dir,
    log_product_info,
    main,
    run_full_pipeline,
    run_generate_image_pipeline,
    save_to_csv,
    validate_subreddit,
)
from app.models import PipelineConfig, ProductIdea, ProductInfo, RedditContext


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_product_info():
    reddit_context = RedditContext(
        post_id="test_post_id",
        post_title="Test Post",
        post_url="https://reddit.com/r/test/comments/test_post_id",
        subreddit="test",
        post_content="Test content",
    )
    return ProductInfo(
        product_id="test_product_id",
        name="Test Product",
        product_type="sticker",
        zazzle_template_id="test_template_id",
        zazzle_tracking_code="test_tracking_code",
        image_url="https://example.com/test.jpg",
        product_url="https://zazzle.com/test_product",
        theme="test theme",
        model="test_model",
        prompt_version="1.0.0",
        reddit_context=reddit_context,
        design_instructions={
            "content": "Test content",
            "image": "https://example.com/test.jpg",
        },
        image_local_path="/tmp/test.jpg",
    )


def test_ensure_output_dir_creates_directory(tmp_path):
    output_dir = tmp_path / "output"
    ensure_output_dir(str(output_dir))
    assert output_dir.exists()
    assert output_dir.is_dir()


def test_save_to_csv_success(mock_product_info, tmp_path):
    output_file = tmp_path / "test_output.csv"
    mock_writer = MagicMock()
    mock_writer.writeheader = MagicMock()
    mock_writer.writerows = MagicMock()

    with patch("builtins.open", mock_open()) as m:
        with patch("csv.DictWriter", return_value=mock_writer):
            save_to_csv([mock_product_info], str(output_file))

    m.assert_called_once_with(str(output_file), "w", newline="")
    mock_writer.writeheader.assert_called_once()
    mock_writer.writerows.assert_called_once()


@pytest.mark.asyncio
async def test_run_full_pipeline_success(mock_product_info):
    with (
        patch("app.main.RedditAgent") as mock_reddit_agent_class,
        patch("app.agents.reddit_agent.RedditAgent") as mock_reddit_agent_impl,
    ):
        mock_agent = AsyncMock(spec=RedditAgent)
        mock_agent.get_product_info = AsyncMock(return_value=[mock_product_info])

        # Create mock subreddit and hot iterator
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = iter([])
        mock_reddit = MagicMock()
        mock_reddit.subreddit.return_value = mock_subreddit
        mock_agent.reddit = mock_reddit

        mock_reddit_agent_class.return_value = mock_agent
        mock_reddit_agent_impl.return_value = mock_agent

        with patch("app.main.save_to_csv") as mock_save:
            config = PipelineConfig(
                model="dall-e-3",
                zazzle_template_id="test_template_id",
                zazzle_tracking_code="test_tracking_code",
                prompt_version="1.0.0",
            )
            result = await run_full_pipeline(config)
            assert result == [mock_product_info]
            mock_save.assert_called_once()


@pytest.mark.asyncio
async def test_run_full_pipeline_no_product_generated():
    with (
        patch("app.main.RedditAgent") as mock_reddit_agent_class,
        patch("app.agents.reddit_agent.RedditAgent") as mock_reddit_agent_impl,
    ):
        mock_agent = AsyncMock(spec=RedditAgent)
        mock_agent.get_product_info = AsyncMock(return_value=[])

        # Create mock subreddit and hot iterator
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = iter([])
        mock_reddit = MagicMock()
        mock_reddit.subreddit.return_value = mock_subreddit
        mock_agent.reddit = mock_reddit

        mock_reddit_agent_class.return_value = mock_agent
        mock_reddit_agent_impl.return_value = mock_agent

        with patch("app.main.save_to_csv") as mock_save:
            config = PipelineConfig(
                model="dall-e-3",
                zazzle_template_id="test_template_id",
                zazzle_tracking_code="test_tracking_code",
                prompt_version="1.0.0",
            )
            with pytest.raises(Exception) as exc_info:
                await run_full_pipeline(config)
            assert "No products were generated" in str(exc_info.value)
            assert "pipeline_run_id" in str(exc_info.value)
            mock_save.assert_not_called()


@pytest.mark.asyncio
async def test_run_full_pipeline_error_handling():
    with (
        patch("app.main.RedditAgent") as mock_reddit_agent_class,
        patch("app.agents.reddit_agent.RedditAgent") as mock_reddit_agent_impl,
    ):
        mock_agent = AsyncMock(spec=RedditAgent)
        mock_agent.get_product_info.side_effect = Exception("Test error")
        mock_agent.reddit = MagicMock()  # Add mock reddit client
        mock_reddit_agent_class.return_value = mock_agent
        mock_reddit_agent_impl.return_value = mock_agent

        with patch("app.main.save_to_csv") as mock_save:
            config = PipelineConfig(
                model="dall-e-3",
                zazzle_template_id="test_template_id",
                zazzle_tracking_code="test_tracking_code",
                prompt_version="1.0.0",
            )
            # Verify that the error is raised
            with pytest.raises(Exception) as exc_info:
                await run_full_pipeline(config)
            assert str(exc_info.value) == "Test error"
            # Verify the mock was called
            mock_agent.get_product_info.assert_called_once()
            mock_save.assert_not_called()
            # Verify RedditAgent was initialized (no arguments expected)
            mock_reddit_agent_class.assert_called_once()


@pytest.mark.asyncio
class TestMain:
    """Test the main application entry points."""

    @patch("app.main.run_full_pipeline")
    async def test_main_full_mode(self, mock_run_full):
        test_argv = ["script.py", "--mode", "full"]
        with patch.object(sys, "argv", test_argv):
            await main()
        mock_run_full.assert_called_once()

    @patch("app.main.run_generate_image_pipeline")
    async def test_main_image_mode(self, mock_run_image):
        test_argv = [
            "script.py",
            "--mode",
            "image",
            "--prompt",
            "Test prompt",
            "--model",
            "dall-e-2",
        ]
        with patch.object(sys, "argv", test_argv):
            await main()
        mock_run_image.assert_called_once_with("Test prompt", "dall-e-2")

    @patch("app.main.run_full_pipeline")
    async def test_main_default_mode(self, mock_run_full):
        test_argv = ["script.py"]
        with patch.object(sys, "argv", test_argv):
            await main()
        mock_run_full.assert_called_once()

    @patch("app.main.run_full_pipeline")
    async def test_main_invalid_mode(self, mock_run_full):
        test_argv = ["script.py", "--mode", "invalid"]
        with patch.object(sys, "argv", test_argv):
            with pytest.raises(SystemExit):
                await main()
        mock_run_full.assert_not_called()

    @patch("app.main.run_generate_image_pipeline")
    async def test_main_image_mode_missing_prompt(self, mock_run_image, caplog):
        test_argv = ["script.py", "--mode", "image"]
        with patch.object(sys, "argv", test_argv):
            with caplog.at_level("ERROR", logger="app.main"):
                with pytest.raises(SystemExit):
                    await main()
        assert any("prompt is required" in record.message for record in caplog.records)
        mock_run_image.assert_not_called()

    @patch("app.main.run_generate_image_pipeline")
    async def test_main_image_mode_default_model(self, mock_run_image):
        test_argv = ["script.py", "--mode", "image", "--prompt", "Test prompt"]
        with patch.object(sys, "argv", test_argv):
            await main()
        mock_run_image.assert_called_once_with("Test prompt", "dall-e-3")

    @patch("app.main.run_full_pipeline")
    async def test_main_with_subreddit_argument(self, mock_run_full):
        """Test main function with --subreddit argument."""
        test_argv = ["script.py", "--subreddit", "golf"]
        with patch.object(sys, "argv", test_argv):
            await main()
        mock_run_full.assert_called_once_with(subreddit_name="golf")

    @patch("app.main.run_full_pipeline")
    async def test_main_without_subreddit_argument(self, mock_run_full):
        """Test main function without --subreddit argument (should pass None)."""
        test_argv = ["script.py"]
        with patch.object(sys, "argv", test_argv):
            await main()
        mock_run_full.assert_called_once_with(subreddit_name=None)


def test_save_to_csv():
    """Test saving product information to CSV with model and version."""
    # Test data
    reddit_context = RedditContext(
        post_id="test_post_id",
        post_title="Test Post Title",
        post_url="https://reddit.com/test",
        subreddit="test_subreddit",
    )

    product_info = ProductInfo(
        product_id="test_id",
        name="Test Product",
        product_type="sticker",
        zazzle_template_id="template123",
        zazzle_tracking_code="tracking456",
        image_url="https://example.com/image.jpg",
        product_url="https://example.com/product",
        theme="test_theme",
        model="dall-e-3",
        prompt_version="1.0.0",
        reddit_context=reddit_context,
        design_instructions={"image": "https://example.com/image.jpg"},
        image_local_path="/path/to/image.jpg",
    )

    # Save to CSV
    test_file = "test_products.csv"
    try:
        product_info.to_csv(test_file)

        # Verify CSV file exists and contains correct data
        assert os.path.exists(test_file)

        with open(test_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            row = rows[0]

            # Check required fields
            assert row["product_id"] == "test_id"
            assert row["name"] == "Test Product"
            assert row["product_type"] == "sticker"
            assert row["zazzle_template_id"] == "template123"
            assert row["zazzle_tracking_code"] == "tracking456"
            assert row["image_url"] == "https://example.com/image.jpg"
            assert row["product_url"] == "https://example.com/product"
            assert row["theme"] == "test_theme"
            assert row["model"] == "dall-e-3"
            assert row["prompt_version"] == "1.0.0"
            assert row["image_local_path"] == "/path/to/image.jpg"

    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)


def test_save_to_csv_missing_fields():
    """Test saving product information to CSV with missing fields."""
    # Test data with missing fields
    reddit_context = RedditContext(
        post_id="test_post_id",
        post_title="Test Post Title",
        post_url="https://reddit.com/test",
        subreddit="test_subreddit",
    )

    product_info = ProductInfo(
        product_id="test_id",
        name="Test Product",
        product_type="sticker",
        zazzle_template_id="template123",
        zazzle_tracking_code="tracking456",
        image_url="https://example.com/image.jpg",
        product_url="https://example.com/product",
        theme="test_theme",
        model="dall-e-3",
        prompt_version="1.0.0",
        reddit_context=reddit_context,
        design_instructions={"image": "https://example.com/image.jpg"},
        image_local_path="/path/to/image.jpg",
    )

    # Save to CSV
    test_file = "test_products.csv"
    try:
        product_info.to_csv(test_file)

        # Verify CSV file exists and contains correct data
        assert os.path.exists(test_file)

        with open(test_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            row = rows[0]

            # Check required fields
            assert row["product_id"] == "test_id"
            assert row["name"] == "Test Product"
            assert row["product_type"] == "sticker"
            assert row["zazzle_template_id"] == "template123"
            assert row["zazzle_tracking_code"] == "tracking456"
            assert row["image_url"] == "https://example.com/image.jpg"
            assert row["product_url"] == "https://example.com/product"
            assert row["theme"] == "test_theme"
            assert row["model"] == "dall-e-3"
            assert row["prompt_version"] == "1.0.0"
            assert row["image_local_path"] == "/path/to/image.jpg"

    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)


def test_validate_subreddit_valid():
    """Test that validate_subreddit accepts valid subreddits."""
    for subreddit in AVAILABLE_SUBREDDITS:
        validate_subreddit(subreddit)  # Should not raise


def test_validate_subreddit_invalid():
    """Test that validate_subreddit raises ValueError for invalid subreddits."""
    with pytest.raises(
        ValueError, match="Subreddit 'invalid_subreddit' is not available"
    ):
        validate_subreddit("invalid_subreddit")


@pytest.mark.asyncio
async def test_run_full_pipeline_with_specified_subreddit(mock_product_info):
    """Test run_full_pipeline with a specified subreddit."""
    with patch("app.main.Pipeline") as mock_pipeline_class:
        mock_pipeline = AsyncMock()
        mock_pipeline.run_pipeline = AsyncMock(return_value=[mock_product_info])
        mock_pipeline_class.return_value = mock_pipeline

        with patch("app.main.save_to_csv") as mock_save:
            config = PipelineConfig(
                model="dall-e-3",
                zazzle_template_id="test_template_id",
                zazzle_tracking_code="test_tracking_code",
                prompt_version="1.0.0",
            )
            result = await run_full_pipeline(config, subreddit_name="golf")
            assert result == [mock_product_info]
            mock_save.assert_called_once()
            # Verify Pipeline was called with the correct arguments
            mock_pipeline_class.assert_called_once()
            call_args = mock_pipeline_class.call_args
            # Check that the reddit_agent was passed with the correct subreddit
            reddit_agent = call_args[1]["reddit_agent"]
            assert reddit_agent.subreddit_name == "golf"


@pytest.mark.asyncio
async def test_run_full_pipeline_with_random_subreddit(mock_product_info):
    """Test run_full_pipeline with no subreddit specified (should pick randomly)."""
    with (
        patch("app.main.Pipeline") as mock_pipeline_class,
        patch("app.main.pick_subreddit", return_value="space") as mock_pick_subreddit,
    ):
        mock_pipeline = AsyncMock()
        mock_pipeline.run_pipeline = AsyncMock(return_value=[mock_product_info])
        mock_pipeline_class.return_value = mock_pipeline

        with patch("app.main.save_to_csv") as mock_save:
            config = PipelineConfig(
                model="dall-e-3",
                zazzle_template_id="test_template_id",
                zazzle_tracking_code="test_tracking_code",
                prompt_version="1.0.0",
            )
            result = await run_full_pipeline(config, subreddit_name=None)
            assert result == [mock_product_info]
            mock_save.assert_called_once()
            # Verify pick_subreddit was called
            mock_pick_subreddit.assert_called_once()
            # Verify Pipeline was called with the correct arguments
            mock_pipeline_class.assert_called_once()
            call_args = mock_pipeline_class.call_args
            # Check that the reddit_agent was passed with the picked subreddit
            reddit_agent = call_args[1]["reddit_agent"]
            assert reddit_agent.subreddit_name == "space"


@pytest.mark.asyncio
async def test_run_full_pipeline_invalid_subreddit():
    """Test run_full_pipeline with an invalid subreddit."""
    with pytest.raises(
        ValueError, match="Subreddit 'invalid_subreddit' is not available"
    ):
        await run_full_pipeline(subreddit_name="invalid_subreddit")
