import pytest


def test_donation_tiers_endpoint(client):
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


def test_create_support_donation(client, test_data):
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

    resp = client.post("/api/donations/create-payment-intent", json=donation_data)
    assert resp.status_code == 200

    # Check response structure
    data = resp.json()
    assert "client_secret" in data
    assert "payment_intent_id" in data


def test_create_commission_donation(client, test_data):
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

    resp = client.post("/api/donations/create-payment-intent", json=donation_data)
    assert resp.status_code == 200

    # Check response structure
    data = resp.json()
    assert "client_secret" in data
    assert "payment_intent_id" in data


def test_create_random_random_commission_donation(client, test_data):
    """Test creating a random_random commission donation with normalized interface."""
    subreddit, pipeline_run, reddit_post = test_data

    donation_data = {
        "amount_usd": 1.00,
        "customer_email": "random_commissioner@example.com",
        "customer_name": "Random Commissioner",
        "donation_type": "commission",
        "commission_type": "random_random",
        "subreddit": subreddit.subreddit_name,  # Now allowed in normalized interface
        "post_id": reddit_post.post_id,  # Now allowed in normalized interface
        "commission_message": "Surprise me!",
        "is_anonymous": False,
    }

    resp = client.post("/api/donations/create-payment-intent", json=donation_data)
    assert resp.status_code == 200

    # Check response structure
    data = resp.json()
    assert "client_secret" in data
    assert "payment_intent_id" in data


def test_random_random_commission_validation_accepts_subreddit(client, test_data):
    """Test that random_random commission type accepts subreddit parameter in normalized interface."""
    subreddit, pipeline_run, reddit_post = test_data

    donation_data = {
        "amount_usd": 1.00,
        "customer_email": "test@example.com",
        "customer_name": "Test User",
        "donation_type": "commission",
        "commission_type": "random_random",
        "subreddit": "golf",  # Now accepted in normalized interface
        "commission_message": "Test message",
        "is_anonymous": False,
    }

    resp = client.post("/api/donations/create-payment-intent", json=donation_data)
    assert resp.status_code == 200  # Should succeed with normalized interface


def test_random_random_commission_validation_accepts_post_id(client, test_data):
    """Test that random_random commission type accepts post_id parameter in normalized interface."""
    subreddit, pipeline_run, reddit_post = test_data

    donation_data = {
        "amount_usd": 1.00,
        "customer_email": "test@example.com",
        "customer_name": "Test User",
        "donation_type": "commission",
        "commission_type": "random_random",
        "post_id": "abc123",  # Now accepted in normalized interface
        "commission_message": "Test message",
        "is_anonymous": False,
    }

    resp = client.post("/api/donations/create-payment-intent", json=donation_data)
    assert resp.status_code == 200  # Should succeed with normalized interface


def test_donations_endpoint(client, test_data):
    """Test retrieving all donations."""
    resp = client.get("/api/donations")
    assert resp.status_code == 200
    donations = resp.json()
    assert isinstance(donations, list)


def test_post_donations_endpoint(client, test_data):
    """Test retrieving donations for a specific post."""
    subreddit, pipeline_run, reddit_post = test_data

    resp = client.get(f"/api/posts/{reddit_post.post_id}/donations")
    assert resp.status_code == 200
    donations = resp.json()
    assert isinstance(donations, list)


def test_donations_by_subreddit_endpoint(client, test_data):
    """Test retrieving donations grouped by subreddit."""
    resp = client.get("/api/donations/by-subreddit")
    assert resp.status_code == 200
    donations_by_subreddit = resp.json()
    assert isinstance(donations_by_subreddit, dict)

    # Check that each subreddit has the expected structure
    for subreddit_name, donations in donations_by_subreddit.items():
        assert "commission" in donations
        assert "support" in donations
        assert isinstance(donations["support"], list)

        # Check support donations structure
        for donation in donations["support"]:
            assert "reddit_username" in donation
            assert "tier_name" in donation
            assert "tier_min_amount" in donation
            assert "donation_amount" in donation
            assert "is_anonymous" in donation
            assert "created_at" in donation
            assert "donation_id" in donation
            assert "post_id" in donation  # New field
            assert "post_title" in donation  # New field
        
        # Check commission donation structure if present
        if donations["commission"]:
            commission = donations["commission"]
            assert "reddit_username" in commission
            assert "tier_name" in commission
            assert "tier_min_amount" in commission
            assert "donation_amount" in commission
            assert "is_anonymous" in commission
            assert "created_at" in commission
            assert "donation_id" in commission
            assert "commission_message" in commission
            assert "commission_type" in commission
            assert "post_id" in commission  # New field
            assert "post_title" in commission  # New field
