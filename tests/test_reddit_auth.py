"""
Test Reddit authentication for both main Reddit client and Promoter agent.
"""
import os
import pytest
from unittest.mock import patch
import praw
from dotenv import load_dotenv

from app.clients.reddit_client import RedditClient


class TestRedditAuthentication:
    """Test Reddit OAuth2 authentication for both clients"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Load environment variables before each test"""
        load_dotenv(override=True)
    
    def test_main_reddit_client_auth(self):
        """Test that main Reddit client can authenticate with REDDIT_* credentials"""
        # Verify env vars are present
        assert os.getenv("REDDIT_CLIENT_ID"), "REDDIT_CLIENT_ID not found in environment"
        assert os.getenv("REDDIT_CLIENT_SECRET"), "REDDIT_CLIENT_SECRET not found in environment"
        assert os.getenv("REDDIT_USERNAME"), "REDDIT_USERNAME not found in environment"
        assert os.getenv("REDDIT_PASSWORD"), "REDDIT_PASSWORD not found in environment"
        
        # Initialize client
        client = RedditClient()
        
        # Test authentication by getting authenticated user
        try:
            user = client.reddit.user.me()
            assert user is not None, "Failed to get authenticated user"
            assert user.name == os.getenv("REDDIT_USERNAME"), f"Username mismatch: expected {os.getenv('REDDIT_USERNAME')}, got {user.name}"
            
            # Test API access
            subreddit = client.reddit.subreddit("python")
            assert subreddit.display_name.lower() == "python", "Failed to access subreddit"
            
        except Exception as e:
            pytest.fail(f"Reddit client authentication failed: {str(e)}")
    
    def test_promoter_agent_reddit_auth(self):
        """Test that promoter agent can authenticate with PROMOTER_AGENT_* credentials"""
        # Verify env vars are present
        assert os.getenv("PROMOTER_AGENT_CLIENT_ID"), "PROMOTER_AGENT_CLIENT_ID not found in environment"
        assert os.getenv("PROMOTER_AGENT_CLIENT_SECRET"), "PROMOTER_AGENT_CLIENT_SECRET not found in environment"
        assert os.getenv("PROMOTER_AGENT_USERNAME"), "PROMOTER_AGENT_USERNAME not found in environment"
        assert os.getenv("PROMOTER_AGENT_PASSWORD"), "PROMOTER_AGENT_PASSWORD not found in environment"
        
        # Create Reddit instance with promoter credentials (same as in ClouvelPromoterAgent)
        try:
            reddit = praw.Reddit(
                client_id=os.getenv("PROMOTER_AGENT_CLIENT_ID"),
                client_secret=os.getenv("PROMOTER_AGENT_CLIENT_SECRET"),
                username=os.getenv("PROMOTER_AGENT_USERNAME"),
                password=os.getenv("PROMOTER_AGENT_PASSWORD"),
                user_agent=os.getenv("PROMOTER_AGENT_USER_AGENT", "clouvel-promoter by u/Queen_Clouvel"),
            )
            
            # Test authentication
            user = reddit.user.me()
            assert user is not None, "Failed to get authenticated user"
            assert user.name == os.getenv("PROMOTER_AGENT_USERNAME"), f"Username mismatch: expected {os.getenv('PROMOTER_AGENT_USERNAME')}, got {user.name}"
            
            # Test API access
            subreddit = reddit.subreddit("art")
            assert subreddit.display_name.lower() == "art", "Failed to access subreddit"
            
        except Exception as e:
            pytest.fail(f"Promoter agent authentication failed: {str(e)}")
    
    def test_both_clients_different_users(self):
        """Verify that the two clients authenticate as different users"""
        main_username = os.getenv("REDDIT_USERNAME")
        promoter_username = os.getenv("PROMOTER_AGENT_USERNAME")
        
        # They should be different users
        assert main_username != promoter_username, "Main and promoter should use different Reddit accounts"
        
        # Verify both are set
        assert main_username, "Main Reddit username not set"
        assert promoter_username, "Promoter Reddit username not set"