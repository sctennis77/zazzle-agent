import pytest
from httpx import AsyncClient
from app.api import app, fetch_successful_pipeline_runs
from unittest.mock import MagicMock
from app.db.models import PipelineRun, ProductInfo, RedditPost
from datetime import datetime

@pytest.mark.asyncio
async def test_get_generated_products_successful(monkeypatch):
    # Mock the fetch_successful_pipeline_runs function
    def mock_fetch_successful_pipeline_runs(db):
        return [{
            "product_info": {
                "id": 1,
                "pipeline_run_id": 1,
                "reddit_post_id": 1,
                "theme": "Test Theme",
                "image_url": "https://example.com/image.jpg",
                "product_url": "https://zazzle.com/product",
                "template_id": "template123",
                "model": "dall-e-3",
                "prompt_version": "1.0.0",
                "product_type": "sticker",
                "design_description": "Test design"
            },
            "pipeline_run": {
                "id": 1,
                "start_time": datetime.utcnow(),
                "status": 'completed',
                "retry_count": 0
            },
            "reddit_post": {
                "id": 1,
                "pipeline_run_id": 1,
                "post_id": "test123",
                "title": "Test Post",
                "content": "Test Content",
                "subreddit": "test",
                "url": "https://reddit.com/test",
                "permalink": "/r/test/test123"
            }
        }]

    monkeypatch.setattr("app.api.fetch_successful_pipeline_runs", mock_fetch_successful_pipeline_runs)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/generated_products")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["product_info"]["theme"] == "Test Theme"
        assert data[0]["pipeline_run"]["status"] == "completed"
        assert data[0]["reddit_post"]["post_id"] == "test123"

@pytest.mark.asyncio
async def test_get_generated_products_empty(monkeypatch):
    # Mock the fetch_successful_pipeline_runs function to return an empty list
    def mock_fetch_successful_pipeline_runs(db):
        return []

    monkeypatch.setattr("app.api.fetch_successful_pipeline_runs", mock_fetch_successful_pipeline_runs)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/generated_products")
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.asyncio
async def test_get_generated_products_error_handling(monkeypatch):
    # Mock the fetch_successful_pipeline_runs function to raise an exception
    def mock_fetch_successful_pipeline_runs(db):
        raise Exception("Database error")

    monkeypatch.setattr("app.api.fetch_successful_pipeline_runs", mock_fetch_successful_pipeline_runs)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/generated_products")
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Database error" in data["detail"] 