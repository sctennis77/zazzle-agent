from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, Donation, SourceType
from app.api import app, get_db

import os
import uuid

ADMIN_SECRET = "testsecret123"
os.environ["ADMIN_SECRET"] = ADMIN_SECRET
os.environ["TESTING"] = "true"

# Create a single in-memory engine and session for this test file
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    # Dependency override
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


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


def test_manual_create_commission_requires_secret():
    """Test that manual commission endpoint requires admin secret"""
    client = TestClient(app)
    payload = {
        "amount_usd": 10.0,
        "customer_email": "admin@example.com",
        "customer_name": "Admin User",
        "subreddit": "testsubreddit",
        "reddit_username": "adminuser",
        "is_anonymous": False,
        "post_id": "testpostid",
        "commission_message": "Test commission!"
    }
    # No secret header
    resp = client.post("/api/commissions/manual-create", json=payload)
    assert resp.status_code == 403
    # Wrong secret
    resp = client.post("/api/commissions/manual-create", json=payload, headers={"x-admin-secret": "wrong"})
    assert resp.status_code == 403


def test_manual_create_commission_success(client, db_session):
    """Test successful manual commission creation"""
    payload = {
        "amount_usd": 10.0,
        "customer_email": "admin@example.com",
        "customer_name": "Admin User",
        "subreddit": "testsubreddit",
        "reddit_username": "adminuser",
        "is_anonymous": False,
        "post_id": "testpostid",
        "commission_message": "Test commission!"
    }
    resp = client.post("/api/commissions/manual-create", json=payload, headers={"x-admin-secret": ADMIN_SECRET})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "manual commission created"
    donation_id = data["donation_id"]
    # Check DB for donation using the same session as the API
    donation = db_session.query(Donation).filter_by(id=donation_id).first()
    assert donation is not None
    assert donation.source == SourceType.MANUAL
    assert donation.donation_type == "commission"
    assert donation.status == "succeeded"
    # Note: commission_type will be None since it's not in CommissionRequest


def test_manual_create_commission_invalid_payload():
    """Test validation of commission request payload"""
    client = TestClient(app)
    # Missing required fields
    payload = {
        "amount_usd": 10.0,
        # Missing customer_email, customer_name, etc.
    }
    resp = client.post("/api/commissions/manual-create", json=payload, headers={"x-admin-secret": ADMIN_SECRET})
    assert resp.status_code == 422  # Validation error


def test_manual_create_commission_missing_secret():
    """Test 403 when no secret header provided"""
    client = TestClient(app)
    payload = {
        "amount_usd": 10.0,
        "customer_email": "admin@example.com",
        "customer_name": "Admin User",
        "subreddit": "testsubreddit",
        "reddit_username": "adminuser",
        "is_anonymous": False,
        "post_id": "testpostid",
        "commission_message": "Test commission!"
    }
    resp = client.post("/api/commissions/manual-create", json=payload)
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["detail"]


def test_manual_create_commission_wrong_secret():
    """Test 403 when wrong secret provided"""
    client = TestClient(app)
    payload = {
        "amount_usd": 10.0,
        "customer_email": "admin@example.com",
        "customer_name": "Admin User",
        "subreddit": "testsubreddit",
        "reddit_username": "adminuser",
        "is_anonymous": False,
        "post_id": "testpostid",
        "commission_message": "Test commission!"
    }
    resp = client.post("/api/commissions/manual-create", json=payload, headers={"x-admin-secret": "wrongsecret"})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["detail"]
