"""
Tests for agent-related API endpoints.

Tests the agent_scanned_posts CRUD endpoints and get_donations_by_post_id functionality.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from app.db.models import AgentScannedPost, Donation, Subreddit, SourceType
from app.models import AgentScannedPostCreateRequest


class TestAgentScannedPostsAPI:
    """Test suite for agent_scanned_posts API endpoints."""

    def test_create_agent_scanned_post_success(self, client, db_session):
        """Test successful creation of agent scanned post."""
        post_data = {
            "post_id": "test_post_123",
            "subreddit": "popular",
            "promoted": True,
            "post_title": "Test Post Title",
            "post_score": 150,
            "comment_id": "comment_456",
            "promotion_message": "Great post! Check out r/clouvel for artwork! 👑🐕✨",
            "rejection_reason": None,
        }

        response = client.post("/api/agent-scanned-posts", json=post_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["post_id"] == "test_post_123"
        assert data["subreddit"] == "popular"
        assert data["promoted"] is True
        assert data["post_title"] == "Test Post Title"
        assert data["post_score"] == 150
        assert data["comment_id"] == "comment_456"
        assert data["promotion_message"] == "Great post! Check out r/clouvel for artwork! 👑🐕✨"
        assert data["rejection_reason"] is None
        assert "id" in data
        assert "scanned_at" in data

    def test_create_agent_scanned_post_rejected(self, client, db_session):
        """Test creation of rejected agent scanned post."""
        post_data = {
            "post_id": "test_post_456",
            "subreddit": "popular",
            "promoted": False,
            "post_title": "Incomprehensible Post",
            "post_score": 5,
            "comment_id": None,
            "promotion_message": None,
            "rejection_reason": "Content is incomprehensible or garbled",
        }

        response = client.post("/api/agent-scanned-posts", json=post_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["post_id"] == "test_post_456"
        assert data["promoted"] is False
        assert data["rejection_reason"] == "Content is incomprehensible or garbled"
        assert data["promotion_message"] is None
        assert data["comment_id"] is None

    def test_create_agent_scanned_post_duplicate(self, client, db_session):
        """Test creation fails for duplicate post_id."""
        # Create first post
        post_data = {
            "post_id": "duplicate_post",
            "subreddit": "popular",
            "promoted": True,
            "post_title": "Original Post",
            "post_score": 100,
        }
        
        response = client.post("/api/agent-scanned-posts", json=post_data)
        assert response.status_code == 200

        # Try to create duplicate
        response = client.post("/api/agent-scanned-posts", json=post_data)
        assert response.status_code == 409
        assert "already scanned" in response.json()["detail"]

    def test_get_agent_scanned_posts_all(self, client, db_session):
        """Test getting all agent scanned posts."""
        # Create test posts
        posts = [
            AgentScannedPost(
                post_id="post_1",
                subreddit="popular",
                promoted=True,
                post_title="Post 1",
                post_score=100,
            ),
            AgentScannedPost(
                post_id="post_2",
                subreddit="gaming",
                promoted=False,
                post_title="Post 2",
                post_score=50,
                rejection_reason="Low quality content",
            ),
            AgentScannedPost(
                post_id="post_3",
                subreddit="popular",
                promoted=True,
                post_title="Post 3",
                post_score=200,
            ),
        ]
        
        for post in posts:
            db_session.add(post)
        db_session.commit()

        response = client.get("/api/agent-scanned-posts")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 3
        
        # Check posts are returned in correct order (most recent first)
        assert data[0]["post_id"] == "post_3"
        assert data[1]["post_id"] == "post_2"
        assert data[2]["post_id"] == "post_1"

    def test_get_agent_scanned_posts_filtered_by_promoted(self, client, db_session):
        """Test filtering agent scanned posts by promoted status."""
        # Create test posts
        posts = [
            AgentScannedPost(
                post_id="promoted_post",
                subreddit="popular",
                promoted=True,
                post_title="Promoted Post",
                post_score=100,
            ),
            AgentScannedPost(
                post_id="rejected_post",
                subreddit="popular",
                promoted=False,
                post_title="Rejected Post",
                post_score=50,
                rejection_reason="Low quality",
            ),
        ]
        
        for post in posts:
            db_session.add(post)
        db_session.commit()

        # Test promoted=true filter
        response = client.get("/api/agent-scanned-posts?promoted=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["post_id"] == "promoted_post"
        assert data[0]["promoted"] is True

        # Test promoted=false filter
        response = client.get("/api/agent-scanned-posts?promoted=false")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["post_id"] == "rejected_post"
        assert data[0]["promoted"] is False

    def test_get_agent_scanned_posts_filtered_by_subreddit(self, client, db_session):
        """Test filtering agent scanned posts by subreddit."""
        # Create test posts
        posts = [
            AgentScannedPost(
                post_id="popular_post",
                subreddit="popular",
                promoted=True,
                post_title="Popular Post",
                post_score=100,
            ),
            AgentScannedPost(
                post_id="gaming_post",
                subreddit="gaming",
                promoted=True,
                post_title="Gaming Post",
                post_score=75,
            ),
        ]
        
        for post in posts:
            db_session.add(post)
        db_session.commit()

        # Test subreddit filter
        response = client.get("/api/agent-scanned-posts?subreddit=gaming")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["post_id"] == "gaming_post"
        assert data[0]["subreddit"] == "gaming"

    def test_get_agent_scanned_posts_pagination(self, client, db_session):
        """Test pagination of agent scanned posts."""
        # Create 5 test posts
        posts = [
            AgentScannedPost(
                post_id=f"post_{i}",
                subreddit="popular",
                promoted=True,
                post_title=f"Post {i}",
                post_score=100 + i,
            )
            for i in range(5)
        ]
        
        for post in posts:
            db_session.add(post)
        db_session.commit()

        # Test limit
        response = client.get("/api/agent-scanned-posts?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

        # Test offset
        response = client.get("/api/agent-scanned-posts?limit=2&offset=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # Should skip the first 2 posts (most recent)
        assert data[0]["post_id"] == "post_2"
        assert data[1]["post_id"] == "post_1"

    def test_get_agent_scanned_post_by_id_success(self, client, db_session):
        """Test getting specific agent scanned post by ID."""
        # Create test post
        post = AgentScannedPost(
            post_id="specific_post",
            subreddit="popular",
            promoted=True,
            post_title="Specific Post",
            post_score=150,
            comment_id="comment_123",
            promotion_message="Great content! 👑🐕✨",
        )
        db_session.add(post)
        db_session.commit()

        response = client.get("/api/agent-scanned-posts/specific_post")
        assert response.status_code == 200
        
        data = response.json()
        assert data["post_id"] == "specific_post"
        assert data["subreddit"] == "popular"
        assert data["promoted"] is True
        assert data["post_title"] == "Specific Post"
        assert data["post_score"] == 150
        assert data["comment_id"] == "comment_123"
        assert data["promotion_message"] == "Great content! 👑🐕✨"

    def test_get_agent_scanned_post_by_id_not_found(self, client, db_session):
        """Test getting non-existent agent scanned post returns 404."""
        response = client.get("/api/agent-scanned-posts/nonexistent_post")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_check_post_scanned_exists(self, client, db_session):
        """Test checking if post has been scanned - exists."""
        # Create test post
        post = AgentScannedPost(
            post_id="scanned_post",
            subreddit="popular",
            promoted=True,
            post_title="Scanned Post",
            post_score=100,
        )
        db_session.add(post)
        db_session.commit()

        response = client.get("/api/agent-scanned-posts/check/scanned_post")
        assert response.status_code == 200
        
        data = response.json()
        assert data["post_id"] == "scanned_post"
        assert data["already_scanned"] is True

    def test_check_post_scanned_not_exists(self, client, db_session):
        """Test checking if post has been scanned - does not exist."""
        response = client.get("/api/agent-scanned-posts/check/unscanned_post")
        assert response.status_code == 200
        
        data = response.json()
        assert data["post_id"] == "unscanned_post"
        assert data["already_scanned"] is False

    def test_get_agent_scanned_posts_with_commission_status(self, client, db_session):
        """Test getting agent scanned posts with commission status information."""
        # Create test scanned post
        scanned_post = AgentScannedPost(
            post_id="commission_test_post",
            subreddit="popular",
            promoted=True,
            post_title="Commission Test Post",
            post_score=150,
            comment_id="comment_123",
            promotion_message="Great content! 👑🐕✨",
        )
        db_session.add(scanned_post)
        
        # Create test subreddit
        subreddit = Subreddit(
            subreddit_name="popular",
            display_name="Popular",
            subscribers=1000000,
            over18=False,
        )
        db_session.add(subreddit)
        db_session.commit()
        
        # Create test donation for commission
        donation = Donation(
            stripe_payment_intent_id="pi_test_commission",
            amount_cents=1000,
            amount_usd=Decimal("10.00"),
            tier="gold",
            status="succeeded",
            post_id="commission_test_post",
            reddit_username="test_user",
            donation_type="commission",
            commission_type="specific_post",
            subreddit_id=subreddit.id,
            source=SourceType.STRIPE,
        )
        db_session.add(donation)
        db_session.commit()
        
        # Test without commission status (original format)
        response = client.get("/api/agent-scanned-posts?limit=10")
        assert response.status_code == 200
        data = response.json()
        
        # Find our test post
        test_post = None
        for post in data:
            if post["post_id"] == "commission_test_post":
                test_post = post
                break
        
        assert test_post is not None
        assert "is_commissioned" not in test_post
        assert "donation_info" not in test_post
        
        # Test with commission status (enhanced format)
        response = client.get("/api/agent-scanned-posts?include_commission_status=true&limit=10")
        assert response.status_code == 200
        data = response.json()
        
        # Find our test post
        test_post = None
        for post in data:
            if post["post_id"] == "commission_test_post":
                test_post = post
                break
        
        assert test_post is not None
        assert test_post["is_commissioned"] is True
        assert test_post["donation_info"] is not None
        assert test_post["donation_info"]["donation_id"] == donation.id
        assert test_post["donation_info"]["amount_usd"] == 10.0
        assert test_post["donation_info"]["tier"] == "gold"
        assert test_post["donation_info"]["donor_username"] == "test_user"
        
        # Test non-commissioned post
        non_commissioned_post = AgentScannedPost(
            post_id="no_commission_post",
            subreddit="popular",
            promoted=True,
            post_title="No Commission Post",
            post_score=100,
        )
        db_session.add(non_commissioned_post)
        db_session.commit()
        
        response = client.get("/api/agent-scanned-posts?include_commission_status=true&limit=10")
        assert response.status_code == 200
        data = response.json()
        
        # Find the non-commissioned post
        non_commissioned = None
        for post in data:
            if post["post_id"] == "no_commission_post":
                non_commissioned = post
                break
        
        assert non_commissioned is not None
        assert non_commissioned["is_commissioned"] is False
        assert non_commissioned["donation_info"] is None


class TestGetDonationsByPostIdAPI:
    """Test suite for get_donations_by_post_id API endpoint."""

    def test_get_donations_by_post_id_success(self, client, db_session):
        """Test successful retrieval of donations for a specific post."""
        # Create test subreddit
        subreddit = Subreddit(subreddit_name="test_sub")
        db_session.add(subreddit)
        db_session.commit()

        # Create test donations
        donations = [
            Donation(
                stripe_payment_intent_id="pi_test_1",
                amount_cents=2500,
                amount_usd=25.00,
                status="succeeded",
                tier="gold",
                customer_email="test1@example.com",
                customer_name="Test User 1",
                subreddit_id=subreddit.id,
                donation_type="commission",
                commission_type="specific_post",
                post_id="test_post_123",
                commission_message="Amazing story!",
                source=SourceType.STRIPE,
            ),
            Donation(
                stripe_payment_intent_id="pi_test_2",
                amount_cents=1000,
                amount_usd=10.00,
                status="succeeded",
                tier="silver",
                customer_email="test2@example.com",
                customer_name="Test User 2",
                subreddit_id=subreddit.id,
                donation_type="commission",
                commission_type="specific_post",
                post_id="test_post_123",
                commission_message="Love this content!",
                source=SourceType.STRIPE,
            ),
            Donation(
                stripe_payment_intent_id="pi_test_3",
                amount_cents=500,
                amount_usd=5.00,
                status="succeeded",
                tier="bronze",
                customer_email="test3@example.com",
                customer_name="Test User 3",
                subreddit_id=subreddit.id,
                donation_type="commission",
                commission_type="specific_post",
                post_id="different_post_456",  # Different post
                commission_message="Cool stuff!",
                source=SourceType.STRIPE,
            ),
        ]
        
        for donation in donations:
            db_session.add(donation)
        db_session.commit()

        response = client.get("/api/posts/test_post_123/donations")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 2  # Only donations for test_post_123
        
        # Check first donation
        assert data[0]["post_id"] == "test_post_123"
        assert data[0]["amount_usd"] == 25.00
        assert data[0]["tier"] == "gold"
        assert data[0]["customer_name"] == "Test User 1"
        assert data[0]["commission_message"] == "Amazing story!"
        assert data[0]["status"] == "succeeded"
        
        # Check second donation
        assert data[1]["post_id"] == "test_post_123"
        assert data[1]["amount_usd"] == 10.00
        assert data[1]["tier"] == "silver"
        assert data[1]["customer_name"] == "Test User 2"
        assert data[1]["commission_message"] == "Love this content!"

    def test_get_donations_by_post_id_no_donations(self, client, db_session):
        """Test retrieving donations for post with no donations."""
        response = client.get("/api/posts/no_donations_post/donations")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 0

    def test_get_donations_by_post_id_only_succeeded(self, client, db_session):
        """Test that only successful donations are returned."""
        # Create test subreddit
        subreddit = Subreddit(subreddit_name="test_sub")
        db_session.add(subreddit)
        db_session.commit()

        # Create donations with different statuses
        donations = [
            Donation(
                stripe_payment_intent_id="pi_succeeded",
                amount_cents=2500,
                amount_usd=25.00,
                status="succeeded",
                tier="gold",
                customer_email="success@example.com",
                subreddit_id=subreddit.id,
                donation_type="commission",
                commission_type="specific_post",
                post_id="status_test_post",
                source=SourceType.STRIPE,
            ),
            Donation(
                stripe_payment_intent_id="pi_failed",
                amount_cents=1000,
                amount_usd=10.00,
                status="failed",
                tier="silver",
                customer_email="failed@example.com",
                subreddit_id=subreddit.id,
                donation_type="commission",
                commission_type="specific_post",
                post_id="status_test_post",
                source=SourceType.STRIPE,
            ),
            Donation(
                stripe_payment_intent_id="pi_pending",
                amount_cents=500,
                amount_usd=5.00,
                status="pending",
                tier="bronze",
                customer_email="pending@example.com",
                subreddit_id=subreddit.id,
                donation_type="commission",
                commission_type="specific_post",
                post_id="status_test_post",
                source=SourceType.STRIPE,
            ),
        ]
        
        for donation in donations:
            db_session.add(donation)
        db_session.commit()

        response = client.get("/api/posts/status_test_post/donations")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 1  # Only the succeeded donation
        assert data[0]["status"] == "succeeded"
        assert data[0]["customer_email"] == "success@example.com"

    def test_get_donations_by_post_id_with_subreddit_info(self, client, db_session):
        """Test that donations include subreddit information."""
        # Create test subreddit
        subreddit = Subreddit(
            subreddit_name="test_community",
            display_name="Test Community",
            description="A test community",
        )
        db_session.add(subreddit)
        db_session.commit()

        # Create test donation
        donation = Donation(
            stripe_payment_intent_id="pi_subreddit_test",
            amount_cents=1500,
            amount_usd=15.00,
            status="succeeded",
            tier="silver",
            customer_email="user@example.com",
            customer_name="Test User",
            subreddit_id=subreddit.id,
            donation_type="commission",
            commission_type="specific_post",
            post_id="subreddit_test_post",
            source=SourceType.STRIPE,
        )
        db_session.add(donation)
        db_session.commit()

        response = client.get("/api/posts/subreddit_test_post/donations")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 1
        assert data[0]["subreddit"]["subreddit_name"] == "test_community"
        assert data[0]["subreddit"]["display_name"] == "Test Community"
        assert data[0]["subreddit"]["description"] == "A test community"