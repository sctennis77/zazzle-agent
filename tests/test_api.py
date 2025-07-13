from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api import app, fetch_successful_pipeline_runs
from app.db.models import PipelineRun, ProductInfo, RedditPost


def test_get_generated_products_successful(monkeypatch):
    # Mock the fetch_successful_pipeline_runs function
    def mock_fetch_successful_pipeline_runs(db):
        return [
            {
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
                    "design_description": "Test design",
                },
                "pipeline_run": {
                    "id": 1,
                    "start_time": datetime.utcnow(),
                    "status": "completed",
                    "retry_count": 0,
                },
                "reddit_post": {
                    "id": 1,
                    "pipeline_run_id": 1,
                    "post_id": "test123",
                    "title": "Test Post",
                    "content": "Test Content",
                    "subreddit": "test",
                    "url": "https://reddit.com/test",
                    "permalink": "/r/test/test123",
                    "comment_summary": "Test comment summary",
                },
            }
        ]

    monkeypatch.setattr(
        "app.api.fetch_successful_pipeline_runs", mock_fetch_successful_pipeline_runs
    )

    client = TestClient(app)
    response = client.get("/api/generated_products")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["product_info"]["theme"] == "Test Theme"
    assert data[0]["pipeline_run"]["status"] == "completed"
    assert data[0]["reddit_post"]["post_id"] == "test123"


def test_get_generated_products_empty(monkeypatch):
    # Mock the fetch_successful_pipeline_runs function to return an empty list
    def mock_fetch_successful_pipeline_runs(db):
        return []

    monkeypatch.setattr(
        "app.api.fetch_successful_pipeline_runs", mock_fetch_successful_pipeline_runs
    )

    client = TestClient(app)
    response = client.get("/api/generated_products")
    assert response.status_code == 200
    assert response.json() == []


def test_get_generated_products_error_handling(monkeypatch):
    # Mock the fetch_successful_pipeline_runs function to raise an exception
    def mock_fetch_successful_pipeline_runs(db):
        raise Exception("Database error")

    monkeypatch.setattr(
        "app.api.fetch_successful_pipeline_runs", mock_fetch_successful_pipeline_runs
    )

    client = TestClient(app)
    response = client.get("/api/generated_products")
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "Internal server error" in data["detail"]


def test_cors_allows_allowed_origins():
    client = TestClient(app)
    allowed_origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "https://frontend-production-f4ae.up.railway.app",
        "https://clouvel.ai",
        "https://www.clouvel.ai",
    ]
    for origin in allowed_origins:
        response = client.options(
            "/api/generated_products",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin

def test_cors_blocks_disallowed_origin():
    client = TestClient(app)
    disallowed_origin = "https://notallowed.example.com"
    response = client.options(
        "/api/generated_products",
        headers={
            "Origin": disallowed_origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    # Should return 400 for disallowed origins (FastAPI/Starlette behavior)
    assert response.status_code == 400
    assert response.headers.get("access-control-allow-origin") is None
