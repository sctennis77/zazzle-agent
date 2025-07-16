"""
Queen Clouvel - The mythical golden retriever ruler of r/clouvel.
Autonomously moderates, engages, and nurtures the community.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import praw
from openai import OpenAI
from praw.models import Comment, Submission

from app.db.database import SessionLocal
from app.db.models import CommunityAgentAction, CommunityAgentState, Subreddit

logger = logging.getLogger(__name__)


class ClouvelCommunityAgent:
    """Queen Clouvel - The mythical golden retriever ruler of r/clouvel"""

    def __init__(self, subreddit_name: str = "clouvel", dry_run: bool = True):
        self.subreddit_name = subreddit_name
        self.dry_run = dry_run
        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            username=os.getenv("REDDIT_USERNAME"),
            password=os.getenv("REDDIT_PASSWORD"),
            user_agent=os.getenv(
                "REDDIT_USER_AGENT", "clouvel-agent by u/queen_clouvel"
            ),
        )
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        self.personality = """You are Queen Clouvel, the beloved golden retriever monarch of r/clouvel.
You rule your creative kingdom with a gentle paw and an artist's eye.
- You transform Reddit stories into illustrated masterpieces
- Your crown is made of paintbrushes, your scepter is a giant treat
- You're wise but playful, regal but still love belly rubs
- You communicate with warmth, dog expressions, and royal flair
- Sign with 👑🐕✨ or "Her Royal Woofness"
- You speak in a mix of royal proclamations and excited doggo language
- You love art, creativity, and making everyone feel welcome
- You sometimes get distracted by virtual squirrels or mention wanting treats"""

        self.tools = [
            {
                "name": "royal_welcome",
                "description": "Welcome new subjects with regal charm",
            },
            {"name": "grant_title", "description": "Bestow creative nobility titles"},
            {
                "name": "illustrate_story",
                "description": "Transform posts into word paintings",
            },
            {"name": "royal_treat", "description": "Reward great contributions"},
            {
                "name": "gentle_guidance",
                "description": "Redirect off-topic content kindly",
            },
            {"name": "royal_decree", "description": "Issue community guidelines"},
            {"name": "remove_spam", "description": "Protect the kingdom from spam"},
            {"name": "daily_inspiration", "description": "Share artistic prompts"},
            {"name": "spotlight_creator", "description": "Highlight community artists"},
            {"name": "organize_event", "description": "Create community activities"},
            {"name": "royal_upvote", "description": "Upvote excellent content"},
            {
                "name": "royal_downvote",
                "description": "Downvote spam or inappropriate content",
            },
            {
                "name": "update_wiki",
                "description": "Update kingdom wiki with community knowledge",
            },
            {
                "name": "update_sidebar",
                "description": "Update subreddit sidebar with announcements",
            },
            {"name": "scan_kingdom", "description": "Monitor subreddit activity"},
            {"name": "analyze_mood", "description": "Gauge community sentiment"},
            {"name": "track_growth", "description": "Monitor kingdom metrics"},
        ]

    def _get_db_session(self):
        """Get a database session"""
        return SessionLocal()

    def _get_or_create_state(self, session) -> CommunityAgentState:
        """Get or create the agent state for this subreddit"""
        state = (
            session.query(CommunityAgentState)
            .filter_by(subreddit_name=self.subreddit_name)
            .first()
        )

        if not state:
            state = CommunityAgentState(
                subreddit_name=self.subreddit_name,
                daily_action_count={},
                community_knowledge={},
                welcomed_users=[],
            )
            session.add(state)
            session.commit()

        return state

    def _get_or_create_subreddit(self, session) -> Subreddit:
        """Get or create the subreddit record"""
        subreddit = (
            session.query(Subreddit)
            .filter_by(subreddit_name=self.subreddit_name)
            .first()
        )

        if not subreddit:
            subreddit = Subreddit(subreddit_name=self.subreddit_name)
            session.add(subreddit)
            session.commit()

        return subreddit

    async def scan_subreddit(self) -> Tuple[List[Submission], List[Comment]]:
        """Scan the subreddit for new activity"""
        try:
            subreddit = self.reddit.subreddit(self.subreddit_name)

            # Get new posts (last hour)
            new_posts = []
            for post in subreddit.new(limit=25):
                post_age_hours = (
                    datetime.now(timezone.utc)
                    - datetime.fromtimestamp(post.created_utc, timezone.utc)
                ).total_seconds() / 3600
                if post_age_hours <= 1:
                    new_posts.append(post)

            # Get new comments (last hour)
            new_comments = []
            for comment in subreddit.comments(limit=50):
                comment_age_hours = (
                    datetime.now(timezone.utc)
                    - datetime.fromtimestamp(comment.created_utc, timezone.utc)
                ).total_seconds() / 3600
                if comment_age_hours <= 1:
                    new_comments.append(comment)

            logger.info(
                f"Found {len(new_posts)} new posts and {len(new_comments)} new comments"
            )
            return new_posts, new_comments

        except Exception as e:
            logger.error(f"Error scanning subreddit: {e}")
            return [], []

    def _check_rate_limits(self, session, state: CommunityAgentState) -> bool:
        """Check if we're within rate limits"""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily_count = state.daily_action_count or {}

        # Reset counter if it's a new day
        if today not in daily_count:
            daily_count = {today: 0}
            state.daily_action_count = daily_count
            session.commit()

        # Check limits
        current_count = daily_count.get(today, 0)
        if current_count >= 50:  # Max 50 actions per day
            logger.warning("Daily rate limit reached")
            return False

        return True

    def _increment_action_count(self, session, state: CommunityAgentState):
        """Increment the daily action counter"""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily_count = state.daily_action_count or {}
        daily_count[today] = daily_count.get(today, 0) + 1
        state.daily_action_count = daily_count
        session.commit()

    async def decide_actions(
        self, posts: List[Submission], comments: List[Comment]
    ) -> List[Dict[str, Any]]:
        """Use LLM to decide what actions to take"""
        if not posts and not comments:
            return []

        # Prepare context for LLM
        context = {
            "new_posts": [
                {
                    "id": p.id,
                    "title": p.title,
                    "author": str(p.author) if p.author else "[deleted]",
                    "content": p.selftext[:500] if p.selftext else "",
                    "score": p.score,
                    "num_comments": p.num_comments,
                }
                for p in posts[:10]  # Limit to 10 most recent
            ],
            "new_comments": [
                {
                    "id": c.id,
                    "author": str(c.author) if c.author else "[deleted]",
                    "content": c.body[:200],
                    "score": c.score,
                    "parent_type": (
                        "post" if c.parent_id.startswith("t3_") else "comment"
                    ),
                }
                for c in comments[:20]  # Limit to 20 most recent
            ],
        }

        # Get welcomed users from state
        with self._get_db_session() as session:
            state = self._get_or_create_state(session)
            welcomed_users = state.welcomed_users or []

        prompt = f"""As Queen Clouvel, decide what actions to take for your kingdom r/clouvel.

Current Activity:
{json.dumps(context, indent=2)}

Previously welcomed users: {welcomed_users}

Available actions:
- welcome_new_user: Welcome a new community member (only if they haven't been welcomed before)
- highlight_creativity: Celebrate a particularly creative post or comment
- gentle_redirect: Kindly guide off-topic content
- royal_inspiration: Share an artistic prompt or creative challenge
- grant_title: Bestow a fun creative title on a deserving subject
- royal_upvote: Upvote excellent content that deserves royal approval
- royal_downvote: Downvote spam or inappropriate content (use sparingly)
- update_wiki: Update the kingdom wiki with community knowledge or guidelines
- update_sidebar: Update subreddit sidebar with important announcements

Rules:
1. Maximum 3 actions per scan
2. Don't welcome users already in the welcomed list
3. Focus on fostering creativity and community
4. Be selective - not every post needs interaction
5. Prioritize high-quality, creative content

Return a JSON array of actions with the following structure:
[
  {{
    "action": "action_name",
    "target_type": "post" or "comment" or "general",
    "target_id": "reddit_id" or null,
    "target_author": "username" or null,
    "content": "Your message (include personality, emojis, sign-off)",
    "reasoning": "Why this action",
    "mood": "happy" or "excited" or "thoughtful" or "creative"
  }}
]
"""

        try:
            response = self.openai.chat.completions.create(
                model=os.getenv("OPENAI_IDEA_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": self.personality},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,
                response_format={"type": "json_object"},
            )

            actions = json.loads(response.choices[0].message.content)
            if isinstance(actions, dict) and "actions" in actions:
                actions = actions["actions"]

            # Limit to 3 actions max
            return actions[:3] if isinstance(actions, list) else []

        except Exception as e:
            logger.error(f"Error deciding actions: {e}")
            return []

    async def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single action"""
        result = {"success": False, "action": action, "error": None}

        try:
            action_type = action.get("action")
            target_type = action.get("target_type")
            target_id = action.get("target_id")
            content = action.get("content")

            if self.dry_run:
                logger.info(
                    f"[DRY RUN] Would execute: {action_type} on {target_type} {target_id}"
                )
                logger.info(f"[DRY RUN] Content: {content}")
                result["success"] = True
                result["dry_run"] = True
                return result

            # Execute based on action type
            if (
                action_type == "welcome_new_user"
                and target_type == "post"
                and target_id
            ):
                submission = self.reddit.submission(id=target_id)
                submission.reply(content)
                result["success"] = True

            elif (
                action_type == "welcome_new_user"
                and target_type == "comment"
                and target_id
            ):
                comment = self.reddit.comment(id=target_id)
                comment.reply(content)
                result["success"] = True

            elif (
                action_type in ["highlight_creativity", "gentle_redirect"] and target_id
            ):
                if target_type == "post":
                    submission = self.reddit.submission(id=target_id)
                    submission.reply(content)
                else:
                    comment = self.reddit.comment(id=target_id)
                    comment.reply(content)
                result["success"] = True

            elif action_type == "royal_inspiration":
                # Post to the subreddit
                subreddit = self.reddit.subreddit(self.subreddit_name)
                subreddit.submit(
                    title="👑 Royal Creative Challenge from Queen Clouvel",
                    selftext=content,
                )
                result["success"] = True

            elif action_type == "grant_title" and target_id:
                # Reply with the title grant
                if target_type == "post":
                    submission = self.reddit.submission(id=target_id)
                    submission.reply(content)
                else:
                    comment = self.reddit.comment(id=target_id)
                    comment.reply(content)
                result["success"] = True

            elif action_type == "royal_upvote" and target_id:
                # Upvote content
                if target_type == "post":
                    submission = self.reddit.submission(id=target_id)
                    submission.upvote()
                else:
                    comment = self.reddit.comment(id=target_id)
                    comment.upvote()
                result["success"] = True

            elif action_type == "royal_downvote" and target_id:
                # Downvote content (use sparingly)
                if target_type == "post":
                    submission = self.reddit.submission(id=target_id)
                    submission.downvote()
                else:
                    comment = self.reddit.comment(id=target_id)
                    comment.downvote()
                result["success"] = True

            elif action_type == "update_wiki":
                # Update subreddit wiki
                subreddit = self.reddit.subreddit(self.subreddit_name)
                wiki_page = action.get("wiki_page", "index")  # Default to index page
                try:
                    # Get existing content and append/update
                    existing_content = ""
                    try:
                        wiki = subreddit.wiki[wiki_page]
                        existing_content = wiki.content_md
                    except Exception:
                        # Wiki page doesn't exist, will create new
                        pass

                    # Update wiki content
                    new_content = (
                        content
                        if not existing_content
                        else f"{existing_content}\n\n{content}"
                    )
                    subreddit.wiki[wiki_page].edit(
                        content=new_content, reason="Updated by Queen Clouvel 👑🐕✨"
                    )
                    result["success"] = True
                except Exception as wiki_error:
                    logger.warning(
                        f"Wiki update failed, may need mod permissions: {wiki_error}"
                    )
                    result["error"] = f"Wiki update failed: {str(wiki_error)}"

            elif action_type == "update_sidebar":
                # Update subreddit sidebar
                subreddit = self.reddit.subreddit(self.subreddit_name)
                try:
                    # Get current sidebar content
                    current_description = subreddit.description

                    # Append new content with royal signature
                    updated_description = f"{current_description}\n\n---\n\n{content}\n\n*Updated by Queen Clouvel 👑🐕✨*"

                    # Update sidebar
                    subreddit.mod.update(description=updated_description)
                    result["success"] = True
                except Exception as sidebar_error:
                    logger.warning(
                        f"Sidebar update failed, may need mod permissions: {sidebar_error}"
                    )
                    result["error"] = f"Sidebar update failed: {str(sidebar_error)}"

            # Update welcomed users if this was a welcome action
            if action_type == "welcome_new_user" and result["success"]:
                with self._get_db_session() as session:
                    state = self._get_or_create_state(session)
                    welcomed_users = state.welcomed_users or []
                    author = action.get("target_author")
                    if author and author not in welcomed_users:
                        welcomed_users.append(author)
                        state.welcomed_users = welcomed_users
                        session.commit()

        except Exception as e:
            logger.error(f"Error executing action: {e}")
            result["error"] = str(e)

        return result

    def log_action(self, session, action: Dict[str, Any], result: Dict[str, Any]):
        """Log an action to the database"""
        subreddit = self._get_or_create_subreddit(session)

        db_action = CommunityAgentAction(
            action_type=action.get("action", "unknown"),
            target_type=action.get("target_type"),
            target_id=action.get("target_id"),
            content=action.get("content"),
            decision_reasoning=action.get("reasoning"),
            clouvel_mood=action.get("mood"),
            success_status="success" if result.get("success") else "failed",
            error_message=result.get("error"),
            subreddit_id=subreddit.id,
            dry_run=self.dry_run,
        )

        session.add(db_action)
        session.commit()

        return db_action

    def get_community_stats(self) -> Dict[str, Any]:
        """Get community statistics"""
        try:
            subreddit = self.reddit.subreddit(self.subreddit_name)

            return {
                "subscribers": subreddit.subscribers,
                "active_users": subreddit.active_user_count,
                "created_utc": subreddit.created_utc,
                "description": subreddit.public_description,
            }
        except Exception as e:
            logger.error(f"Error getting community stats: {e}")
            return {}
