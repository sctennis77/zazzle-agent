import pytest
from httpx import AsyncClient
from app.api import app, fetch_successful_pipeline_runs
from unittest.mock import MagicMock
from app.db.models import PipelineRun, ProductInfo, RedditPost

@pytest.mark.asyncio
async def test_get_generated_products_successful(monkeypatch):
    # Mock the fetch_successful_pipeline_runs function
    def mock_fetch_successful_pipeline_runs(db):
        return [{
            "product_info": {"id": 1},
            "pipeline_run": {"id": 1, "status": 'success'},
            "reddit_post": {"id": 1}
        }]

    monkeypatch.setattr("app.api.fetch_successful_pipeline_runs", mock_fetch_successful_pipeline_runs)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/generated_products")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert response.json() == [{
        "product_info": {"id": 1},
        "pipeline_run": {"id": 1, "status": 'success'},
        "reddit_post": {"id": 1}
    }]

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