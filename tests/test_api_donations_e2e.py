import pytest
from fastapi.testclient import TestClient
from app.api import app

client = TestClient(app)


def test_donation_tiers_endpoint():
    """Test that donation tiers endpoint returns valid tier data."""
    resp = client.get("/api/donation-tiers")
    assert resp.status_code == 200
    tiers = resp.json()
    assert len(tiers) > 0
    # Check that tiers have required fields
    for tier in tiers:
        assert "name" in tier
        assert "min_amount" in tier
        assert "display_name" in tier


def test_create_support_donation(test_data):
    """Test creating a basic support donation."""
    subreddit, pipeline_run, reddit_post = test_data
    
    donation_data = {
        "amount_usd": 5.00,
        "customer_email": "supporter@example.com",
        "customer_name": "Supporter",
        "donation_type": "support",
        "subreddit": subreddit.subreddit_name,
        "post_id": reddit_post.post_id,
        "message": "Keep up the great work!",
        "is_anonymous": False,
    }
    
    resp = client.post("/api/donations/create-checkout-session", json=donation_data)
    assert resp.status_code == 200
    
    # Check response structure
    data = resp.json()
    assert "url" in data
    assert "session_id" in data


def test_create_commission_donation(test_data):
    """Test creating a basic commission donation."""
    subreddit, pipeline_run, reddit_post = test_data
    
    donation_data = {
        "amount_usd": 10.00,
        "customer_email": "commissioner@example.com",
        "customer_name": "Commissioner",
        "donation_type": "commission",
        "commission_type": "specific_post",
        "subreddit": subreddit.subreddit_name,
        "post_id": reddit_post.post_id,
        "commission_message": "Please make this special!",
        "is_anonymous": False,
    }
    
    resp = client.post("/api/donations/create-checkout-session", json=donation_data)
    assert resp.status_code == 200
    
    # Check response structure
    data = resp.json()
    assert "url" in data
    assert "session_id" in data


def test_create_random_random_commission_donation(test_data):
    """Test creating a random_random commission donation."""
    subreddit, pipeline_run, reddit_post = test_data
    
    donation_data = {
        "amount_usd": 1.00,
        "customer_email": "random_commissioner@example.com",
        "customer_name": "Random Commissioner",
        "donation_type": "commission",
        "commission_type": "random_random",
        "subreddit": "",  # Should be empty for random_random
        "commission_message": "Surprise me!",
        "is_anonymous": False,
    }
    
    resp = client.post("/api/donations/create-checkout-session", json=donation_data)
    assert resp.status_code == 200
    
    # Check response structure
    data = resp.json()
    assert "url" in data
    assert "session_id" in data


def test_random_random_commission_validation_rejects_subreddit(test_data):
    """Test that random_random commission type rejects subreddit parameter."""
    subreddit, pipeline_run, reddit_post = test_data
    
    donation_data = {
        "amount_usd": 1.00,
        "customer_email": "test@example.com",
        "customer_name": "Test User",
        "donation_type": "commission",
        "commission_type": "random_random",
        "subreddit": "golf",  # Should be rejected
        "commission_message": "Test message",
        "is_anonymous": False,
    }
    
    resp = client.post("/api/donations/create-checkout-session", json=donation_data)
    assert resp.status_code == 422  # Validation error


def test_random_random_commission_validation_rejects_post_id(test_data):
    """Test that random_random commission type rejects post_id parameter."""
    subreddit, pipeline_run, reddit_post = test_data
    
    donation_data = {
        "amount_usd": 1.00,
        "customer_email": "test@example.com",
        "customer_name": "Test User",
        "donation_type": "commission",
        "commission_type": "random_random",
        "post_id": "abc123",  # Should be rejected
        "commission_message": "Test message",
        "is_anonymous": False,
    }
    
    resp = client.post("/api/donations/create-checkout-session", json=donation_data)
    assert resp.status_code == 422  # Validation error


def test_donations_endpoint(test_data):
    """Test retrieving all donations."""
    resp = client.get("/api/donations")
    assert resp.status_code == 200
    donations = resp.json()
    assert isinstance(donations, list)


def test_post_donations_endpoint(test_data):
    """Test retrieving donations for a specific post."""
    subreddit, pipeline_run, reddit_post = test_data
    
    resp = client.get(f"/api/posts/{reddit_post.post_id}/donations")
    assert resp.status_code == 200
    donations = resp.json()
    assert isinstance(donations, list) 