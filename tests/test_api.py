"""
API endpoint tests.

Tests for the FastAPI application endpoints, including products, donations,
and admin functionality.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from app.db.models import Donation, SourceType


def test_get_generated_products_successful(client, monkeypatch):
    """Test successful retrieval of generated products."""
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

    response = client.get("/api/generated_products")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["product_info"]["theme"] == "Test Theme"
    assert data[0]["pipeline_run"]["status"] == "completed"
    assert data[0]["reddit_post"]["post_id"] == "test123"


def test_get_generated_products_empty(client, monkeypatch):
    """Test endpoint returns empty list when no products exist."""
    def mock_fetch_successful_pipeline_runs(db):
        return []

    monkeypatch.setattr(
        "app.api.fetch_successful_pipeline_runs", mock_fetch_successful_pipeline_runs
    )

    response = client.get("/api/generated_products")
    assert response.status_code == 200
    assert response.json() == []


def test_get_generated_products_error_handling(client, monkeypatch):
    """Test error handling when database operation fails."""
    def mock_fetch_successful_pipeline_runs(db):
        raise Exception("Database error")

    monkeypatch.setattr(
        "app.api.fetch_successful_pipeline_runs", mock_fetch_successful_pipeline_runs
    )

    response = client.get("/api/generated_products")
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "Internal server error" in data["detail"]


def test_cors_allows_allowed_origins(client):
    """Test CORS allows configured origins - prevents debugging nightmares."""
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
                "Access-Control-Request-Headers": "Content-Type",
            }
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin


def test_cors_blocks_disallowed_origins(client):
    """Test CORS blocks non-configured origins - security check."""
    disallowed_origin = "https://malicious-site.com"
    
    response = client.options(
        "/api/generated_products",
        headers={
            "Origin": disallowed_origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        }
    )
    # CORS should not include the origin in the response for disallowed origins
    assert response.headers.get("access-control-allow-origin") != disallowed_origin


def test_stripe_webhook_missing_signature(client):
    """Test Stripe webhook rejects requests without signature."""
    response = client.post(
        "/webhook",
        data="test payload",
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400


def test_stripe_webhook_invalid_signature(client):
    """Test Stripe webhook rejects requests with invalid signature."""
    response = client.post(
        "/webhook",
        data="test payload",
        headers={
            "Content-Type": "application/json",
            "Stripe-Signature": "invalid_signature"
        }
    )
    assert response.status_code == 400


def test_subreddits_endpoint(client, db_session, sample_subreddit_data):
    """Test subreddits endpoint returns configured subreddits."""
    from app.db.models import Subreddit
    
    # Create test subreddit
    subreddit = Subreddit(**sample_subreddit_data)
    db_session.add(subreddit)
    db_session.commit()
    
    response = client.get("/api/subreddits")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    
    # Check our test subreddit is included
    test_subreddit = next(
        (s for s in data if s["subreddit_name"] == "test"), None
    )
    assert test_subreddit is not None
    assert test_subreddit["display_name"] == "Test Subreddit"


def test_manual_create_commission_success(client, mock_stripe_service):
    """Test manual commission creation with admin secret."""
    commission_data = {
        "amount_usd": 25.00,
        "customer_email": "test@example.com",
        "customer_name": "Test Customer",
        "subreddit": "hiking",
        "commission_message": "Create something cool!",
        "reddit_username": "test_user",
        "is_anonymous": False,
    }
    
    # Mock successful Stripe PaymentIntent creation
    mock_payment_intent = {
        "id": "pi_test_123",
        "amount": 2500,
        "currency": "usd",
        "status": "succeeded",
        "receipt_email": "test@example.com",
        "metadata": commission_data
    }
    mock_stripe_service.create_payment_intent.return_value = mock_payment_intent
    
    response = client.post(
        "/api/admin/manual_commission",
        json=commission_data,
        headers={"X-Admin-Secret": "testsecret123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["payment_intent_id"] == "pi_test_123"
    assert data["amount_usd"] == 25.00


def test_manual_create_commission_unauthorized(client):
    """Test manual commission creation fails without admin secret."""
    commission_data = {
        "amount_usd": 25.00,
        "customer_email": "test@example.com",
        "customer_name": "Test Customer",
        "subreddit": "hiking",
        "commission_message": "Create something cool!",
        "reddit_username": "test_user",
        "is_anonymous": False,
    }
    
    response = client.post(
        "/api/admin/manual_commission",
        json=commission_data
    )
    
    assert response.status_code == 403


def test_manual_create_commission_wrong_secret(client):
    """Test manual commission creation fails with wrong admin secret."""
    commission_data = {
        "amount_usd": 25.00,
        "customer_email": "test@example.com",
        "customer_name": "Test Customer",
        "subreddit": "hiking",
        "commission_message": "Create something cool!",
        "reddit_username": "test_user",
        "is_anonymous": False,
    }
    
    response = client.post(
        "/api/admin/manual_commission",
        json=commission_data,
        headers={"X-Admin-Secret": "wrong_secret"}
    )
    
    assert response.status_code == 403


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data