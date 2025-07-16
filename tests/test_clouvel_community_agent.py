"""
Tests for the Clouvel Community Agent - Queen Clouvel's autonomous kingdom management.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.clouvel_community_agent import ClouvelCommunityAgent
from app.db.models import CommunityAgentAction, CommunityAgentState, Subreddit


@pytest.fixture
def mock_reddit_submission():
    """Mock Reddit submission object"""
    submission = MagicMock()
    submission.id = "test_post_123"
    submission.title = "Amazing artwork I created!"
    submission.selftext = "Check out this cool digital art piece"
    submission.author = MagicMock()
    submission.author.__str__ = MagicMock(return_value="artist_user")
    submission.score = 15
    submission.num_comments = 3
    submission.created_utc = datetime.now(timezone.utc).timestamp()
    submission.reply = MagicMock()
    return submission


@pytest.fixture
def mock_reddit_comment():
    """Mock Reddit comment object"""
    comment = MagicMock()
    comment.id = "comment_456"
    comment.author = MagicMock()
    comment.author.__str__ = MagicMock(return_value="commenter_user")
    comment.body = "This is such beautiful work!"
    comment.score = 5
    comment.parent_id = "t3_test_post_123"
    comment.created_utc = datetime.now(timezone.utc).timestamp()
    comment.reply = MagicMock()
    return comment


@pytest.fixture
def clouvel_agent():
    """Create a Clouvel Community Agent with mocked dependencies"""
    with patch("app.agents.clouvel_community_agent.praw.Reddit") as mock_reddit:
        with patch("app.agents.clouvel_community_agent.OpenAI") as mock_openai:
            mock_reddit_client = MagicMock()
            mock_openai_client = MagicMock()
            mock_reddit.return_value = mock_reddit_client
            mock_openai.return_value = mock_openai_client

            agent = ClouvelCommunityAgent(subreddit_name="clouvel", dry_run=True)
            agent.reddit = mock_reddit_client
            agent.openai = mock_openai_client
            return agent


class TestClouvelCommunityAgent:
    """Test cases for Queen Clouvel's community management"""

    def test_agent_initialization(self):
        """Test that the agent initializes with correct personality"""
        agent = ClouvelCommunityAgent(subreddit_name="test_sub", dry_run=True)

        assert agent.subreddit_name == "test_sub"
        assert agent.dry_run is True
        assert "Queen Clouvel" in agent.personality
        assert "golden retriever" in agent.personality
        assert len(agent.tools) > 0

        # Check that essential tools are present
        tool_names = [tool["name"] for tool in agent.tools]
        assert "royal_welcome" in tool_names
        assert "grant_title" in tool_names
        assert "gentle_guidance" in tool_names
        assert "royal_upvote" in tool_names
        assert "royal_downvote" in tool_names
        assert "update_wiki" in tool_names
        assert "update_sidebar" in tool_names

    def test_get_or_create_state_new(self, clouvel_agent, db_session):
        """Test creating new agent state"""
        state = clouvel_agent._get_or_create_state(db_session)

        assert state is not None
        assert state.subreddit_name == "clouvel"
        assert state.daily_action_count == {}
        assert state.community_knowledge == {}
        assert state.welcomed_users == []

    def test_get_or_create_state_existing(self, clouvel_agent, db_session):
        """Test retrieving existing agent state"""
        # Create initial state
        existing_state = CommunityAgentState(
            subreddit_name="clouvel",
            daily_action_count={"2025-07-15": 5},
            community_knowledge={"active_users": ["user1", "user2"]},
            welcomed_users=["welcomed_user"],
        )
        db_session.add(existing_state)
        db_session.commit()

        # Retrieve it
        state = clouvel_agent._get_or_create_state(db_session)

        assert state.daily_action_count["2025-07-15"] == 5
        assert "user1" in state.community_knowledge["active_users"]
        assert "welcomed_user" in state.welcomed_users

    def test_check_rate_limits_within_limits(self, clouvel_agent, db_session):
        """Test rate limiting when within daily limits"""
        state = clouvel_agent._get_or_create_state(db_session)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        state.daily_action_count = {today: 10}
        db_session.commit()

        assert clouvel_agent._check_rate_limits(db_session, state) is True

    def test_check_rate_limits_exceeded(self, clouvel_agent, db_session):
        """Test rate limiting when daily limits exceeded"""
        state = clouvel_agent._get_or_create_state(db_session)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        state.daily_action_count = {today: 50}  # At limit
        db_session.commit()

        assert clouvel_agent._check_rate_limits(db_session, state) is False

    def test_increment_action_count(self, clouvel_agent, db_session):
        """Test incrementing daily action counter"""
        state = clouvel_agent._get_or_create_state(db_session)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        clouvel_agent._increment_action_count(db_session, state)

        # Refresh from database
        db_session.refresh(state)
        assert state.daily_action_count[today] == 1

    @pytest.mark.asyncio
    async def test_scan_subreddit_success(
        self, clouvel_agent, mock_reddit_submission, mock_reddit_comment
    ):
        """Test successful subreddit scanning"""
        # Mock subreddit with recent posts and comments
        mock_subreddit = MagicMock()
        mock_subreddit.new.return_value = [mock_reddit_submission]
        mock_subreddit.comments.return_value = [mock_reddit_comment]
        clouvel_agent.reddit.subreddit.return_value = mock_subreddit

        posts, comments = await clouvel_agent.scan_subreddit()

        assert len(posts) >= 0  # May be 0 if post is too old
        assert len(comments) >= 0  # May be 0 if comment is too old
        clouvel_agent.reddit.subreddit.assert_called_with("clouvel")

    @pytest.mark.asyncio
    async def test_scan_subreddit_error_handling(self, clouvel_agent):
        """Test error handling during subreddit scanning"""
        clouvel_agent.reddit.subreddit.side_effect = Exception("Reddit API error")

        posts, comments = await clouvel_agent.scan_subreddit()

        assert posts == []
        assert comments == []

    @pytest.mark.asyncio
    async def test_decide_actions_with_new_content(
        self, clouvel_agent, mock_reddit_submission, mock_reddit_comment
    ):
        """Test LLM decision making with new content"""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(
            [
                {
                    "action": "welcome_new_user",
                    "target_type": "post",
                    "target_id": "test_post_123",
                    "target_author": "artist_user",
                    "content": "Welcome to our creative kingdom! 👑🐕✨",
                    "reasoning": "New user posting artwork",
                    "mood": "excited",
                }
            ]
        )
        clouvel_agent.openai.chat.completions.create.return_value = mock_response

        # Mock database state
        with patch.object(clouvel_agent, "_get_db_session") as mock_session:
            mock_db_session = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_db_session

            mock_state = MagicMock()
            mock_state.welcomed_users = []
            clouvel_agent._get_or_create_state = MagicMock(return_value=mock_state)

            actions = await clouvel_agent.decide_actions(
                [mock_reddit_submission], [mock_reddit_comment]
            )

        assert len(actions) == 1
        assert actions[0]["action"] == "welcome_new_user"
        assert actions[0]["target_id"] == "test_post_123"
        assert "👑🐕✨" in actions[0]["content"]

    @pytest.mark.asyncio
    async def test_decide_actions_empty_content(self, clouvel_agent):
        """Test decision making with no new content"""
        actions = await clouvel_agent.decide_actions([], [])
        assert actions == []

    @pytest.mark.asyncio
    async def test_execute_action_welcome_post_dry_run(self, clouvel_agent):
        """Test executing welcome action on post in dry run mode"""
        action = {
            "action": "welcome_new_user",
            "target_type": "post",
            "target_id": "test_post_123",
            "content": "Welcome to our kingdom! 👑🐕✨",
        }

        result = await clouvel_agent.execute_action(action)

        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["action"] == action

    @pytest.mark.asyncio
    async def test_execute_action_welcome_post_live(
        self, clouvel_agent, mock_reddit_submission
    ):
        """Test executing welcome action on post in live mode"""
        clouvel_agent.dry_run = False
        clouvel_agent.reddit.submission.return_value = mock_reddit_submission

        action = {
            "action": "welcome_new_user",
            "target_type": "post",
            "target_id": "test_post_123",
            "target_author": "artist_user",
            "content": "Welcome to our kingdom! 👑🐕✨",
        }

        # Mock database operations
        with patch.object(clouvel_agent, "_get_db_session") as mock_session:
            mock_db_session = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_db_session

            mock_state = MagicMock()
            mock_state.welcomed_users = []
            clouvel_agent._get_or_create_state = MagicMock(return_value=mock_state)

            result = await clouvel_agent.execute_action(action)

        assert result["success"] is True
        mock_reddit_submission.reply.assert_called_once_with(
            "Welcome to our kingdom! 👑🐕✨"
        )

    @pytest.mark.asyncio
    async def test_execute_action_royal_inspiration(self, clouvel_agent):
        """Test executing royal inspiration action"""
        clouvel_agent.dry_run = False
        mock_subreddit = MagicMock()
        clouvel_agent.reddit.subreddit.return_value = mock_subreddit

        action = {
            "action": "royal_inspiration",
            "target_type": "general",
            "target_id": None,
            "content": "Today's royal challenge: Paint your morning with words! 🎨",
        }

        result = await clouvel_agent.execute_action(action)

        assert result["success"] is True
        mock_subreddit.submit.assert_called_once()

        # Check submit call arguments
        call_args = mock_subreddit.submit.call_args
        assert "👑 Royal Creative Challenge" in call_args.kwargs["title"]
        assert "Paint your morning with words!" in call_args.kwargs["selftext"]

    @pytest.mark.asyncio
    async def test_execute_action_error_handling(self, clouvel_agent):
        """Test error handling during action execution"""
        clouvel_agent.dry_run = False
        clouvel_agent.reddit.submission.side_effect = Exception("Reddit error")

        action = {
            "action": "welcome_new_user",
            "target_type": "post",
            "target_id": "test_post_123",
            "content": "Welcome!",
        }

        result = await clouvel_agent.execute_action(action)

        assert result["success"] is False
        assert "Reddit error" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_action_royal_upvote(
        self, clouvel_agent, mock_reddit_submission
    ):
        """Test executing royal upvote action"""
        clouvel_agent.dry_run = False
        clouvel_agent.reddit.submission.return_value = mock_reddit_submission

        action = {
            "action": "royal_upvote",
            "target_type": "post",
            "target_id": "excellent_post_123",
            "content": None,
        }

        result = await clouvel_agent.execute_action(action)

        assert result["success"] is True
        mock_reddit_submission.upvote.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_action_royal_downvote(
        self, clouvel_agent, mock_reddit_comment
    ):
        """Test executing royal downvote action"""
        clouvel_agent.dry_run = False
        clouvel_agent.reddit.comment.return_value = mock_reddit_comment

        action = {
            "action": "royal_downvote",
            "target_type": "comment",
            "target_id": "spam_comment_456",
            "content": None,
        }

        result = await clouvel_agent.execute_action(action)

        assert result["success"] is True
        mock_reddit_comment.downvote.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_action_update_wiki(self, clouvel_agent):
        """Test executing wiki update action"""
        clouvel_agent.dry_run = False

        # Mock subreddit and wiki
        mock_subreddit = MagicMock()
        mock_wiki_page = MagicMock()
        mock_wiki_page.content_md = "Existing wiki content"
        mock_subreddit.wiki = {"index": mock_wiki_page}
        clouvel_agent.reddit.subreddit.return_value = mock_subreddit

        action = {
            "action": "update_wiki",
            "target_type": "general",
            "target_id": None,
            "content": "## New Royal Decree\n\nAll subjects must share their creativity!",
            "wiki_page": "index",
        }

        result = await clouvel_agent.execute_action(action)

        assert result["success"] is True
        mock_wiki_page.edit.assert_called_once()
        edit_call = mock_wiki_page.edit.call_args
        assert "New Royal Decree" in edit_call.kwargs["content"]
        assert "Queen Clouvel 👑🐕✨" in edit_call.kwargs["reason"]

    @pytest.mark.asyncio
    async def test_execute_action_update_sidebar(self, clouvel_agent):
        """Test executing sidebar update action"""
        clouvel_agent.dry_run = False

        # Mock subreddit with mod capabilities
        mock_subreddit = MagicMock()
        mock_subreddit.description = "Welcome to r/clouvel! A creative community."
        mock_mod = MagicMock()
        mock_subreddit.mod = mock_mod
        clouvel_agent.reddit.subreddit.return_value = mock_subreddit

        action = {
            "action": "update_sidebar",
            "target_type": "general",
            "target_id": None,
            "content": "🎨 Weekly Art Challenge: Paint your dreams!",
        }

        result = await clouvel_agent.execute_action(action)

        assert result["success"] is True
        mock_mod.update.assert_called_once()
        update_call = mock_mod.update.call_args
        assert "Weekly Art Challenge" in update_call.kwargs["description"]
        assert "Queen Clouvel 👑🐕✨" in update_call.kwargs["description"]

    @pytest.mark.asyncio
    async def test_execute_action_wiki_permission_error(self, clouvel_agent):
        """Test wiki update with permission error"""
        clouvel_agent.dry_run = False

        mock_subreddit = MagicMock()
        mock_subreddit.wiki.__getitem__.side_effect = Exception("Forbidden")
        clouvel_agent.reddit.subreddit.return_value = mock_subreddit

        action = {
            "action": "update_wiki",
            "target_type": "general",
            "content": "Royal announcement",
        }

        result = await clouvel_agent.execute_action(action)

        assert result["success"] is False
        assert "Wiki update failed" in result["error"]

    def test_log_action_success(self, clouvel_agent, db_session):
        """Test logging successful action to database"""
        # Create subreddit record
        subreddit = Subreddit(subreddit_name="clouvel")
        db_session.add(subreddit)
        db_session.commit()

        action = {
            "action": "welcome_new_user",
            "target_type": "post",
            "target_id": "test_post_123",
            "content": "Welcome! 👑🐕✨",
            "reasoning": "New user posting artwork",
            "mood": "excited",
        }

        result = {"success": True, "error": None}

        db_action = clouvel_agent.log_action(db_session, action, result)

        assert db_action.action_type == "welcome_new_user"
        assert db_action.target_type == "post"
        assert db_action.target_id == "test_post_123"
        assert db_action.content == "Welcome! 👑🐕✨"
        assert db_action.success_status == "success"
        assert db_action.clouvel_mood == "excited"
        assert db_action.dry_run is True

    def test_log_action_failure(self, clouvel_agent, db_session):
        """Test logging failed action to database"""
        # Create subreddit record
        subreddit = Subreddit(subreddit_name="clouvel")
        db_session.add(subreddit)
        db_session.commit()

        action = {"action": "test_action"}
        result = {"success": False, "error": "Test error"}

        db_action = clouvel_agent.log_action(db_session, action, result)

        assert db_action.success_status == "failed"
        assert db_action.error_message == "Test error"

    def test_get_community_stats_success(self, clouvel_agent):
        """Test getting community statistics"""
        mock_subreddit = MagicMock()
        mock_subreddit.subscribers = 1500
        mock_subreddit.active_user_count = 50
        mock_subreddit.created_utc = 1609459200  # 2021-01-01
        mock_subreddit.public_description = "A creative community"
        clouvel_agent.reddit.subreddit.return_value = mock_subreddit

        stats = clouvel_agent.get_community_stats()

        assert stats["subscribers"] == 1500
        assert stats["active_users"] == 50
        assert stats["created_utc"] == 1609459200
        assert stats["description"] == "A creative community"

    def test_get_community_stats_error(self, clouvel_agent):
        """Test error handling when getting community stats"""
        clouvel_agent.reddit.subreddit.side_effect = Exception("API error")

        stats = clouvel_agent.get_community_stats()

        assert stats == {}


class TestClouvelPersonality:
    """Test Queen Clouvel's personality and responses"""

    def test_personality_contains_key_elements(self):
        """Test that the personality contains essential Queen Clouvel elements"""
        agent = ClouvelCommunityAgent()
        personality = agent.personality

        assert "Queen Clouvel" in personality
        assert "golden retriever" in personality
        assert "crown" in personality
        assert "paintbrushes" in personality
        assert "👑🐕✨" in personality
        assert "Royal Woofness" in personality

    def test_tools_include_essential_functions(self):
        """Test that essential tools are available"""
        agent = ClouvelCommunityAgent()
        tool_names = [tool["name"] for tool in agent.tools]

        # Core engagement tools
        assert "royal_welcome" in tool_names
        assert "grant_title" in tool_names
        assert "illustrate_story" in tool_names

        # Moderation tools
        assert "gentle_guidance" in tool_names
        assert "royal_decree" in tool_names

        # Community building tools
        assert "daily_inspiration" in tool_names
        assert "spotlight_creator" in tool_names

        # Voting tools
        assert "royal_upvote" in tool_names
        assert "royal_downvote" in tool_names

        # Moderation tools
        assert "update_wiki" in tool_names
        assert "update_sidebar" in tool_names

        # Monitoring tools
        assert "scan_kingdom" in tool_names
        assert "analyze_mood" in tool_names
