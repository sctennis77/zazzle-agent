import glob
import json
import logging
import os
import shutil
import sys
from datetime import datetime
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.affiliate_linker import (
    InvalidProductDataError,
    ZazzleAffiliateLinker,
    ZazzleAffiliateLinkerError,
)
from app.async_image_generator import IMAGE_GENERATION_BASE_PROMPTS
from app.models import ProductIdea, ProductInfo, RedditContext


@pytest.fixture(autouse=True)
def setup():
    # Mock necessary environment variables for tests
    with patch.dict(
        os.environ,
        {
            "ZAZZLE_AFFILIATE_ID": "test_affiliate_id",
            "ZAZZLE_TEMPLATE_ID": "test_template_id",
            "ZAZZLE_TRACKING_CODE": "test_tracking_code",
        },
    ):
        yield


@pytest.fixture
def reddit_context():
    return RedditContext(
        post_id="test_post_id",
        post_title="Test Post Title",
        post_url="https://reddit.com/test",
        subreddit="test_subreddit",
    )


@pytest.fixture
def mock_product_info(reddit_context):
    return ProductInfo(
        product_id="test_product_id",
        name="Test Product",
        product_type="sticker",
        zazzle_template_id="test_template_id",
        zazzle_tracking_code="test_tracking_code",
        image_url="https://example.com/image.jpg",
        product_url="https://example.com/product",
        theme="test_theme",
        model="dall-e-3",
        prompt_version=IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]["version"],
        reddit_context=reddit_context,
        design_instructions={"image": "https://example.com/image.jpg"},
        image_local_path="/path/to/image.jpg",
    )


@pytest.fixture
def mock_product_idea():
    return ProductIdea(
        title="Test Post",
        url="https://reddit.com/test",
        subreddit="test_subreddit",
        post_id="test_post_id",
    )


@pytest.mark.asyncio
class TestZazzleAffiliateLinker:
    @pytest.fixture
    def affiliate_linker(self):
        return ZazzleAffiliateLinker(
            zazzle_affiliate_id="test_affiliate_id",
            zazzle_tracking_code="test_tracking_code",
        )

    async def test_generate_links_batch_success(
        self, affiliate_linker, mock_product_info
    ):
        # Mock the _generate_affiliate_link method
        affiliate_linker._generate_affiliate_link = AsyncMock(
            return_value="https://www.zazzle.com/product/test_product_id?rf=test_affiliate_id"
        )

        # Test generating links for a batch of products
        products = [mock_product_info]
        result = await affiliate_linker.generate_links_batch(products)

        # Verify the result
        assert len(result) == 1
        assert (
            result[0].affiliate_link
            == "https://www.zazzle.com/product/test_product_id?rf=test_affiliate_id"
        )
        assert result[0].product_id == mock_product_info.product_id

    async def test_generate_links_batch_empty(self, affiliate_linker):
        # Test with empty product list
        result = await affiliate_linker.generate_links_batch([])
        assert len(result) == 0

    async def test_generate_links_batch_error(
        self, affiliate_linker, mock_product_info
    ):
        # Mock the _generate_affiliate_link method to raise an error
        affiliate_linker._generate_affiliate_link = AsyncMock(
            side_effect=ZazzleAffiliateLinkerError("API Error")
        )

        # Test error handling
        products = [mock_product_info]
        result = await affiliate_linker.generate_links_batch(products)
        assert result[0].affiliate_link is None

    async def test_generate_links_batch_invalid_data(self, affiliate_linker):
        # Test with invalid product data
        invalid_product = ProductInfo(
            product_id="",  # Empty product ID
            name="Test Product",
            product_type="sticker",
            zazzle_template_id="test_template_id",
            zazzle_tracking_code="test_tracking_code",
            image_url="https://example.com/image.jpg",
            product_url="https://example.com/product",
            theme="test_theme",
            model="dall-e-3",
            prompt_version=IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]["version"],
            reddit_context=RedditContext(
                post_id="test_post_id",
                post_title="Test Post Title",
                post_url="https://reddit.com/test",
                subreddit="test_subreddit",
            ),
            design_instructions={"image": "https://example.com/image.jpg"},
            image_local_path="/path/to/image.jpg",
        )

        products = [invalid_product]
        result = await affiliate_linker.generate_links_batch(products)
        assert result[0].affiliate_link is None

    async def test_generate_affiliate_link(self, affiliate_linker, mock_product_info):
        # Test generating a single affiliate link
        result = await affiliate_linker._generate_affiliate_link(mock_product_info)
        # Verify the result
        expected_url = f"{mock_product_info.product_url}?rf=test_affiliate_id&tc=test_tracking_code"
        assert result == expected_url

    async def test_generate_affiliate_link_error(
        self, affiliate_linker, mock_product_info
    ):
        # Mock the _generate_affiliate_link method to raise an error
        affiliate_linker._generate_affiliate_link = AsyncMock(
            side_effect=ZazzleAffiliateLinkerError("API Error")
        )

        # Test error handling
        with pytest.raises(ZazzleAffiliateLinkerError):
            await affiliate_linker._generate_affiliate_link(mock_product_info)
