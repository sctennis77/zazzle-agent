"""
Tests for the Clouvel Promoter Agent
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.agents.clouvel_promoter_agent import ClouvelPromoterAgent
from app.db.models import AgentScannedPost


class TestClouvelPromoterAgent:
    """Test suite for ClouvelPromoterAgent"""

    def test_agent_initialization(self):
        """Test agent initializes correctly"""
        agent = ClouvelPromoterAgent(dry_run=True)
        
        assert agent.dry_run is True
        assert agent.subreddit_name == "popular"
        assert agent.max_posts_per_hour == 10
        assert agent.min_score_threshold == 0
        assert len(agent.tools) == 9

    def test_agent_initialization_custom_subreddit(self):
        """Test agent initializes with custom subreddit"""
        agent = ClouvelPromoterAgent(subreddit_name="test", dry_run=False)
        
        assert agent.dry_run is False
        assert agent.subreddit_name == "test"

    @patch('app.agents.clouvel_promoter_agent.praw.Reddit')
    @patch('app.agents.clouvel_promoter_agent.OpenAI')
    def test_agent_services_initialized(self, mock_openai, mock_reddit):
        """Test that Reddit and OpenAI services are initialized"""
        agent = ClouvelPromoterAgent(dry_run=True)
        
        mock_reddit.assert_called_once()
        mock_openai.assert_called_once()

    def test_personality_defined(self):
        """Test that agent personality is properly defined"""
        agent = ClouvelPromoterAgent(dry_run=True)
        
        assert "Queen Clouvel" in agent.personality
        assert "golden retriever monarch" in agent.personality
        assert "Commission Promoter" in agent.personality

    @patch('app.agents.clouvel_promoter_agent.SessionLocal')
    def test_check_post_already_scanned(self, mock_session_local):
        """Test checking if post is already scanned"""
        # Mock session and query
        mock_session = Mock()
        mock_session_local.return_value.__enter__.return_value = mock_session
        
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # Post not found
        
        agent = ClouvelPromoterAgent(dry_run=True)
        result = agent._check_post_already_scanned(mock_session, "test_post_id")
        
        assert result is False
        mock_session.query.assert_called_with(AgentScannedPost)

    @patch('app.agents.clouvel_promoter_agent.requests.get')
    def test_get_donations_by_post_id_success(self, mock_get):
        """Test getting donations for a post"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"amount": 25.0}]
        mock_get.return_value = mock_response
        
        agent = ClouvelPromoterAgent(dry_run=True)
        donations = agent.get_donations_by_post_id("test_post_id")
        
        assert len(donations) == 1
        assert donations[0]["amount"] == 25.0

    @patch('app.agents.clouvel_promoter_agent.requests.get')
    def test_get_donations_by_post_id_failure(self, mock_get):
        """Test handling API failure when getting donations"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_get.return_value = mock_response
        
        agent = ClouvelPromoterAgent(dry_run=True)
        donations = agent.get_donations_by_post_id("test_post_id")
        
        assert donations == []

    def test_check_post_already_commissioned(self):
        """Test checking if post is already commissioned"""
        agent = ClouvelPromoterAgent(dry_run=True)
        
        with patch.object(agent, 'get_donations_by_post_id') as mock_get_donations:
            # Test with donations (commissioned)
            mock_get_donations.return_value = [{"amount": 25.0}]
            result = agent._check_post_already_commissioned("test_post_id")
            assert result is True
            
            # Test without donations (not commissioned)
            mock_get_donations.return_value = []
            result = agent._check_post_already_commissioned("test_post_id")
            assert result is False

    @patch('app.agents.clouvel_promoter_agent.SessionLocal')
    def test_record_scanned_post(self, mock_session_local):
        """Test recording a scanned post"""
        mock_session = Mock()
        mock_session_local.return_value.__enter__.return_value = mock_session
        
        agent = ClouvelPromoterAgent(dry_run=True)
        agent._record_scanned_post(
            mock_session,
            "test_post_id",
            "test_subreddit",
            True,
            "Test Title",
            100,
            "comment_123",
            "Test promotion message"
        )
        
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_get_status_structure(self):
        """Test status method returns proper structure"""
        agent = ClouvelPromoterAgent(dry_run=True)
        
        with patch.object(agent, '_get_db_session') as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            
            # Mock query results
            mock_session.query.return_value.count.return_value = 10
            mock_session.query.return_value.filter.return_value.count.return_value = 7
            mock_session.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
            
            status = agent.get_status()
            
            assert "agent_type" in status
            assert "dry_run" in status
            assert "total_scanned" in status
            assert "total_promoted" in status
            assert "total_rejected" in status
            assert "promotion_rate" in status
            assert "recent_activity" in status
            
            assert status["agent_type"] == "ClouvelPromoterAgent"
            assert status["dry_run"] is True


class TestClouvelPromoterAgentAnalysis:
    """Test content analysis functionality"""

    def test_analyze_post_content_structure(self):
        """Test post content analysis returns expected structure"""
        agent = ClouvelPromoterAgent(dry_run=True)
        
        # Mock Reddit post
        mock_post = Mock()
        mock_post.title = "Test Title"
        mock_post.selftext = "Test content"
        mock_post.url = "https://reddit.com/test"
        mock_post.subreddit.display_name = "test"
        mock_post.score = 100
        mock_post.num_comments = 5
        mock_post.author = "test_user"
        mock_post.is_video = False
        mock_post.domain = "reddit.com"
        # Mock comments with iterable behavior
        mock_comment = Mock()
        mock_comment.body = "Test comment"
        mock_comment.score = 10
        mock_comment.author = "commenter"
        
        mock_comments = Mock()
        mock_comments.replace_more = Mock()
        mock_comments.__iter__ = Mock(return_value=iter([mock_comment]))
        mock_comments.__getitem__ = Mock(side_effect=lambda x: [mock_comment][x])
        mock_post.comments = mock_comments
        
        content = agent.analyze_post_content(mock_post)
        
        assert "title" in content
        assert "selftext" in content
        assert "url" in content
        assert "subreddit" in content
        assert "score" in content
        assert "num_comments" in content
        assert "author" in content
        assert "is_video" in content
        assert "is_image" in content
        assert "domain" in content
        assert "top_comments" in content

    @patch('app.agents.clouvel_promoter_agent.OpenAI')
    def test_decide_promotion_worthiness_promote(self, mock_openai_class):
        """Test promotion decision logic for worthy content"""
        # Mock OpenAI response
        mock_openai = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = '{"promote": true, "reason": "Great story potential"}'
        mock_response.choices = [mock_choice]
        mock_openai.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai
        
        agent = ClouvelPromoterAgent(dry_run=True)
        agent.openai = mock_openai
        
        post_content = {
            "title": "Amazing story",
            "selftext": "Great content",
            "subreddit": "test",
            "score": 100,
            "num_comments": 10,
            "domain": "reddit.com",
            "is_image": False,
            "is_video": False,
            "top_comments": []
        }
        
        should_promote, reason, agent_ratings = agent.decide_promotion_worthiness(post_content)
        
        assert should_promote is True
        assert reason == "Great story potential"

    @patch('app.agents.clouvel_promoter_agent.OpenAI')
    def test_generate_witty_comment(self, mock_openai_class):
        """Test comment generation"""
        # Mock OpenAI response
        mock_openai = Mock()
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Woof! What an amazing story! 👑🐕✨"
        mock_response.choices = [mock_choice]
        mock_openai.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai
        
        agent = ClouvelPromoterAgent(dry_run=True)
        agent.openai = mock_openai
        
        post_content = {
            "title": "Test story",
            "selftext": "Test content",
            "subreddit": "test"
        }
        
        comment = agent.generate_witty_comment(post_content)
        
        assert "Woof!" in comment
        assert "👑🐕✨" in comment


class TestClouvelPromoterAgentWorkflow:
    """Test complete workflow functionality"""

    def test_run_single_cycle_dry_run(self):
        """Test complete single cycle in dry run mode"""
        agent = ClouvelPromoterAgent(dry_run=True)
        
        with patch.object(agent, 'get_status') as mock_get_status, \
             patch.object(agent, 'process_single_post') as mock_process:
            
            mock_get_status.return_value = {
                "total_scanned": 5,
                "total_promoted": 3
            }
            mock_process.return_value = {
                "processed": True,
                "action": "promoted",
                "post_id": "test_123"
            }
            
            result = agent.run_single_cycle()
            
            assert result["processed"] is True
            assert result["action"] == "promoted"
            assert result["post_id"] == "test_123"
            
            mock_get_status.assert_called_once()
            mock_process.assert_called_once()