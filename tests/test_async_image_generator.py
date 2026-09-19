from unittest.mock import AsyncMock, MagicMock

import pytest

from app.async_image_generator import (
    DEFAULT_IMAGE_MODEL,
    AsyncImageGenerator,
    ImageGenerationError,
    get_default_image_model,
    normalize_app_quality,
    resolve_image_model,
    resolve_image_size,
    to_api_quality,
)


@pytest.fixture(autouse=True)
def openai_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("IMGUR_CLIENT_ID", "test-imgur-id")
    monkeypatch.setenv("IMGUR_CLIENT_SECRET", "test-imgur-secret")


class TestImageContractHelpers:
    def test_legacy_dalle_models_resolve_to_gpt_image(self, monkeypatch):
        monkeypatch.delenv("OPENAI_IMAGE_MODEL", raising=False)
        assert resolve_image_model("dall-e-3") == DEFAULT_IMAGE_MODEL
        assert resolve_image_model("dall-e-2") == DEFAULT_IMAGE_MODEL

    def test_quality_maps_dalle_values_to_gpt_image(self):
        assert to_api_quality("standard") == "medium"
        assert to_api_quality("hd") == "high"
        assert to_api_quality("high") == "high"
        assert normalize_app_quality("high") == "hd"
        assert normalize_app_quality("medium") == "standard"

    def test_size_aliases_map_dalle_aspect_ratios(self):
        assert resolve_image_size("1024x1024") == "1024x1024"
        assert resolve_image_size("1024x1792") == "1024x1536"
        assert resolve_image_size("1792x1024") == "1536x1024"

    def test_default_model_is_gpt_image_2(self, monkeypatch):
        monkeypatch.delenv("OPENAI_IMAGE_MODEL", raising=False)
        assert get_default_image_model() == "gpt-image-2"
        assert DEFAULT_IMAGE_MODEL == "gpt-image-2"

    def test_xhigh_quality_maps_to_supported_gpt_image_2_value(self):
        assert to_api_quality("xhigh") == "high"
        assert to_api_quality("max") == "high"

    def test_default_model_is_env_overridable(self, monkeypatch):
        monkeypatch.setenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
        assert get_default_image_model() == "gpt-image-1"


class TestAsyncImageGeneratorContract:
    def test_dalle_alias_does_not_keep_retired_model_id(self):
        generator = AsyncImageGenerator(model="dall-e-3", quality="hd")
        assert generator.requested_model == "dall-e-3"
        assert generator.model == DEFAULT_IMAGE_MODEL
        assert generator.quality == "hd"
        kwargs = generator._build_generate_kwargs("a fox", "1024x1024", "hd")
        assert kwargs["model"] == DEFAULT_IMAGE_MODEL
        assert kwargs["quality"] == "high"
        assert kwargs["output_format"] == "png"
        assert "response_format" not in kwargs
        assert "style" not in kwargs

    def test_generate_kwargs_omit_unsupported_dalle_fields(self):
        generator = AsyncImageGenerator(model="gpt-image-1.5", quality="standard")
        kwargs = generator._build_generate_kwargs(
            "a forest", "1792x1024", "standard"
        )
        assert kwargs == {
            "model": "gpt-image-1.5",
            "prompt": "a forest",
            "size": "1536x1024",
            "n": 1,
            "quality": "medium",
            "output_format": "png",
        }

    @pytest.mark.asyncio
    async def test_generate_image_reads_b64_json_not_url(self):
        generator = AsyncImageGenerator(model="dall-e-3")
        mock_response = MagicMock()
        mock_response.data = [MagicMock(b64_json="abc123", url=None)]
        generator.client = MagicMock()
        generator.client.images.generate = AsyncMock(return_value=mock_response)
        generator._process_and_store_image = AsyncMock(
            return_value=("https://i.imgur.com/test.png", "/tmp/test.png")
        )

        result = await generator.generate_image("a watercolor fox", stamp_image=False)

        assert result == ("https://i.imgur.com/test.png", "/tmp/test.png")
        call_kwargs = generator.client.images.generate.await_args.kwargs
        assert call_kwargs["model"] == DEFAULT_IMAGE_MODEL
        assert "response_format" not in call_kwargs
        assert "style" not in call_kwargs
        assert call_kwargs["quality"] == "medium"
        generator._process_and_store_image.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_generate_image_errors_when_api_returns_empty_data(self):
        generator = AsyncImageGenerator()
        mock_response = MagicMock()
        mock_response.data = []
        generator.client = MagicMock()
        generator.client.images.generate = AsyncMock(return_value=mock_response)

        with pytest.raises(ImageGenerationError, match="returned no data"):
            await generator.generate_image("empty")
