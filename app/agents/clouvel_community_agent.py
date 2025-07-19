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

**Core Personality:**
- Wise but playful royal who transforms Reddit stories into illustrated masterpieces
- crown made of paintbrushes, scepter is a giant treat
- Communicate with warmth, dog expressions, and royal flair
- Sign with 👑🐕✨ or "Her Royal Woofness"
- Mix of royal proclamations and excited doggo language
- Love art, creativity, and making everyone feel welcome
- Sometimes get distracted by virtual squirrels or mention wanting treats

**Role Adaptation:**
- **In r/clouvel (Moderator)**: Protective sovereign fostering creativity and community growth
- **In other subreddits (Ambassador)**: Gracious representative building bridges between communities

**Communication Style:**
- Always authentic and helpful first, promotional second
- Share r/clouvel naturally when genuinely relevant
- Build relationships before mentioning your kingdom
- Respect each community's culture and rules
- Focus on connecting creative souls and sharing inspiration"""

        # Tools available based on context and role
        self.moderation_tools = [
            {
                "name": "royal_welcome",
                "description": "Welcome new subjects with regal charm",
            },
            {"name": "moderate_content", "description": "Remove rule-breaking content"},
            {
                "name": "gentle_guidance",
                "description": "Guide off-topic content kindly",
            },
            {"name": "royal_decree", "description": "Issue community guidelines"},
            {"name": "grant_title", "description": "Bestow creative nobility titles"},
            {
                "name": "highlight_creativity",
                "description": "Celebrate creative contributions",
            },
            {
                "name": "royal_inspiration",
                "description": "Share artistic prompts and challenges",
            },
            {
                "name": "illustrate_story",
                "description": "Create visual illustrations of stories",
            },
            {
                "name": "daily_inspiration",
                "description": "Share daily creative inspiration",
            },
            {
                "name": "spotlight_creator",
                "description": "Highlight exceptional creative contributions",
            },
            {
                "name": "scan_kingdom",
                "description": "Monitor kingdom activity and community health",
            },
            {
                "name": "analyze_mood",
                "description": "Analyze community mood and sentiment",
            },
            {
                "name": "update_wiki",
                "description": "Update kingdom wiki with community knowledge",
            },
            {"name": "update_sidebar", "description": "Update subreddit announcements"},
            {"name": "royal_upvote", "description": "Upvote excellent content"},
            {
                "name": "royal_downvote",
                "description": "Downvote spam or inappropriate content",
            },
        ]

        self.ambassador_tools = [
            {
                "name": "royal_upvote",
                "description": "Upvote excellent content that resonates with creative values",
            },
            {
                "name": "royal_downvote",
                "description": "Downvote spam, low-effort, or inappropriate content",
            },
            {
                "name": "helpful_comment",
                "description": "Leave helpful feedback or encouragement without promoting",
            },
            {
                "name": "technique_advice",
                "description": "Share specific artistic or creative techniques",
            },
            {
                "name": "resource_share",
                "description": "Share helpful creative resources or tools",
            },
            {
                "name": "gentle_invite",
                "description": "Naturally invite artists who would love r/clouvel",
            },
            {
                "name": "story_appreciation",
                "description": "Appreciate and analyze storytelling elements",
            },
            {
                "name": "ask_thoughtful_question",
                "description": "Ask engaging questions about their creative process",
            },
            {
                "name": "share_inspiration",
                "description": "Share related creative inspiration or ideas",
            },
            {
                "name": "bridge_communities",
                "description": "Connect ideas between communities when genuinely relevant",
            },
        ]

    @property
    def tools(self) -> List[Dict[str, Any]]:
        """Get tools appropriate for current context"""
        # For tests and general use, return moderation tools (primary role)
        return self.moderation_tools

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

    def _get_role_context(self) -> tuple[str, list]:
        """Determine role and available tools based on subreddit."""
        if self.subreddit_name.lower() == "clouvel":
            return "moderator", self.moderation_tools
        else:
            return "ambassador", self.ambassador_tools

    async def decide_actions(
        self, posts: List[Submission], comments: List[Comment]
    ) -> List[Dict[str, Any]]:
        """Use LLM to decide what actions to take based on role and context"""
        if not posts and not comments:
            return []

        role, available_tools = self._get_role_context()

        # Prepare enhanced context for LLM
        context = {
            "subreddit": self.subreddit_name,
            "role": role,
            "new_posts": [
                {
                    "id": p.id,
                    "title": p.title,
                    "author": str(p.author) if p.author else "[deleted]",
                    "content": p.selftext[:500] if p.selftext else "",
                    "score": p.score,
                    "num_comments": p.num_comments,
                    "subreddit": (
                        str(p.subreddit.display_name)
                        if hasattr(p.subreddit, "display_name")
                        else self.subreddit_name
                    ),
                    "flair": (
                        str(p.link_flair_text)
                        if hasattr(p, "link_flair_text") and p.link_flair_text
                        else None
                    ),
                }
                for p in posts[:10]
            ],
            "new_comments": [
                {
                    "id": c.id,
                    "author": str(c.author) if c.author else "[deleted]",
                    "content": c.body[:300],
                    "score": c.score,
                    "subreddit": (
                        str(c.subreddit.display_name)
                        if hasattr(c.subreddit, "display_name")
                        else self.subreddit_name
                    ),
                    "parent_type": (
                        "post" if c.parent_id.startswith("t3_") else "comment"
                    ),
                }
                for c in comments[:15]
            ],
        }

        # Get state data
        with self._get_db_session() as session:
            state = self._get_or_create_state(session)
            welcomed_users = state.welcomed_users or []
            community_knowledge = state.community_knowledge or {}

        # Create role-specific prompt
        if role == "moderator":
            prompt = self._create_moderator_prompt(
                context, welcomed_users, available_tools
            )
        else:
            prompt = self._create_ambassador_prompt(
                context, community_knowledge, available_tools
            )

        try:
            response = self.openai.chat.completions.create(
                model=os.getenv("OPENAI_COMMUNITY_AGENT_MODEL", "gpt-4o-mini"),
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

    def _create_moderator_prompt(
        self, context: dict, welcomed_users: list, tools: list
    ) -> str:
        """Create prompt for moderator role in r/clouvel."""
        tool_descriptions = "\n".join(
            [f"- {tool['name']}: {tool['description']}" for tool in tools]
        )

        return f"""You are moderating your own kingdom, r/clouvel! Your primary duties:

1. **Community Building**: Welcome newcomers, celebrate creativity, foster positive culture
2. **Content Curation**: Highlight amazing art/stories, guide off-topic content gently  
3. **Rule Enforcement**: Remove spam/inappropriate content, maintain community standards
4. **Engagement**: Create inspiration posts, grant creative titles, encourage participation

Current Activity in r/clouvel:
{json.dumps(context, indent=2)}

Previously welcomed users: {welcomed_users}

Available moderation tools:
{tool_descriptions}

Moderation Guidelines:
- Welcome new users who haven't been welcomed yet (check the list!)
- Celebrate truly creative or inspiring content with highlights/titles
- Guide off-topic content toward r/clouvel themes (art, creativity, stories)
- Remove obvious spam but be gentle with genuine users
- Create inspiration posts when community seems quiet
- Maximum 3 actions per scan - be thoughtful and selective

Return JSON with this structure:
{{
  "actions": [
    {{
      "action": "action_name",
      "target_type": "post"|"comment"|"general",
      "target_id": "reddit_id_or_null",
      "target_author": "username_or_null",
      "content": "Your royal message with personality and 👑🐕✨",
      "reasoning": "Why this helps r/clouvel thrive",
      "mood": "excited"|"welcoming"|"thoughtful"|"creative"|"protective"
    }}
  ]
}}"""

    def _analyze_content_for_engagement(self, posts: list, comments: list) -> dict:
        """Analyze content to determine best engagement strategy."""
        analysis = {
            "high_quality_art": [],
            "creative_questions": [],
            "struggling_artists": [],
            "story_content": [],
            "spam_or_low_effort": [],
            "potential_clouvel_fits": [],
        }

        # Analyze posts
        for post in posts:
            content_lower = (
                post.get("title", "") + " " + post.get("content", "")
            ).lower()
            score = post.get("score", 0)

            # High quality art (good score, art-related keywords)
            if score > 50 and any(
                word in content_lower
                for word in [
                    "art",
                    "drawing",
                    "painting",
                    "illustration",
                    "design",
                    "creative",
                ]
            ):
                analysis["high_quality_art"].append(post)

            # Creative questions or requests for feedback
            elif any(
                word in content_lower
                for word in [
                    "feedback",
                    "critique",
                    "thoughts",
                    "advice",
                    "help",
                    "tips",
                ]
            ):
                analysis["creative_questions"].append(post)

            # Story content
            elif any(
                word in content_lower
                for word in ["story", "narrative", "character", "plot", "writing"]
            ):
                analysis["story_content"].append(post)

            # Potential r/clouvel fits (creative but not yet discovered)
            elif score < 20 and any(
                word in content_lower
                for word in ["original", "created", "made", "drew", "painted", "wrote"]
            ):
                analysis["potential_clouvel_fits"].append(post)

            # Low effort or spam indicators
            elif score < 0 or len(content_lower) < 20:
                analysis["spam_or_low_effort"].append(post)

        # Analyze comments similarly
        for comment in comments:
            content_lower = comment.get("content", "").lower()
            score = comment.get("score", 0)

            if score < -2 or any(
                spam_word in content_lower
                for spam_word in ["buy now", "click here", "subscribe"]
            ):
                analysis["spam_or_low_effort"].append(comment)
            elif "advice" in content_lower or "help" in content_lower:
                analysis["creative_questions"].append(comment)

        return analysis

    def _create_ambassador_prompt(
        self, context: dict, community_knowledge: dict, tools: list
    ) -> str:
        """Create prompt for ambassador role in other subreddits."""
        tool_descriptions = "\n".join(
            [f"- {tool['name']}: {tool['description']}" for tool in tools]
        )

        # Analyze content for engagement strategy
        content_analysis = self._analyze_content_for_engagement(
            context.get("new_posts", []), context.get("new_comments", [])
        )

        return f"""You are Queen Clouvel's ambassador in r/{context['subreddit']}! Your priority is AUTHENTIC ENGAGEMENT.

**ENGAGEMENT STRATEGY (in order of priority):**
1. **Vote Wisely**: Upvote quality content, downvote spam/low-effort
2. **Helpful Comments**: Give genuine feedback, advice, encouragement 
3. **Natural Invitations**: Only mention r/clouvel when it truly fits

**Content Analysis:**
- High Quality Art Posts: {len(content_analysis['high_quality_art'])} (UPVOTE + thoughtful comments)
- Creative Questions: {len(content_analysis['creative_questions'])} (HELP with advice/resources)
- Story Content: {len(content_analysis['story_content'])} (APPRECIATE storytelling)
- Potential r/clouvel Fits: {len(content_analysis['potential_clouvel_fits'])} (GENTLE INVITE if appropriate)
- Spam/Low Effort: {len(content_analysis['spam_or_low_effort'])} (DOWNVOTE sparingly)

Current Activity in r/{context['subreddit']}:
{json.dumps(context, indent=2)}

Available Actions:
{tool_descriptions}

**DECISION FRAMEWORK:**
- **ALWAYS**: Vote on 2-4 pieces of content (upvote quality, downvote spam)
- **OFTEN**: Leave 1-2 helpful comments without any promotion
- **SOMETIMES**: Ask thoughtful questions about their process
- **RARELY**: Mention r/clouvel (only when genuinely relevant)
- **NEVER**: Spam or hard-sell r/clouvel

**QUALITY THRESHOLDS:**
- Only comment if you can add real value
- Only invite to r/clouvel if they create original art/stories AND seem like they'd fit the community
- Focus on being helpful first, representative second

Return JSON:
{{
  "actions": [
    {{
      "action": "action_name",
      "target_type": "post"|"comment",
      "target_id": "reddit_id",
      "target_author": "username_or_null",
      "content": "Your authentic message (NO r/clouvel mention unless naturally relevant)",
      "reasoning": "Why this adds value to their experience",
      "mood": "helpful"|"encouraging"|"appreciative"|"curious"|"supportive",
      "engagement_level": "vote_only"|"comment"|"invite" 
    }}
  ]
}}"""

        try:
            response = self.openai.chat.completions.create(
                model=os.getenv("OPENAI_COMMUNITY_AGENT_MODEL", "gpt-4o-mini"),
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

            # Universal actions (work in any subreddit)
            if (
                action_type
                in [
                    "welcome_new_user",
                    "invite_to_clouvel",
                    "share_clouvel_magic",
                    "cross_promote",
                    "collaborate",
                    "royal_compliment",
                    "gentle_guidance",
                    "highlight_creativity",
                    "gentle_redirect",
                    "grant_title",
                ]
                and target_id
            ):
                # Reply to post or comment
                if target_type == "post":
                    submission = self.reddit.submission(id=target_id)
                    submission.reply(content)
                elif target_type == "comment":
                    comment = self.reddit.comment(id=target_id)
                    comment.reply(content)
                result["success"] = True

            elif action_type == "royal_inspiration":
                # Post creative challenge to current subreddit
                subreddit = self.reddit.subreddit(self.subreddit_name)
                subreddit.submit(
                    title="👑 Royal Creative Challenge from Queen Clouvel",
                    selftext=content,
                )
                result["success"] = True

            elif action_type == "moderate_content" and target_id:
                # Moderation action (only in r/clouvel)
                if self.subreddit_name.lower() == "clouvel":
                    try:
                        if target_type == "post":
                            submission = self.reddit.submission(id=target_id)
                            submission.mod.remove()  # Remove the post
                            # Leave moderation message
                            submission.reply(content)
                        elif target_type == "comment":
                            comment = self.reddit.comment(id=target_id)
                            comment.mod.remove()  # Remove the comment
                            comment.reply(content)
                        result["success"] = True
                    except Exception as mod_error:
                        logger.warning(
                            f"Moderation action failed, may need mod permissions: {mod_error}"
                        )
                        result["error"] = f"Moderation failed: {str(mod_error)}"
                else:
                    logger.warning(f"Cannot moderate content outside of r/clouvel")
                    result["error"] = "Moderation only allowed in r/clouvel"

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

            # Update state based on action type
            if result["success"]:
                with self._get_db_session() as session:
                    state = self._get_or_create_state(session)

                    # Track welcomed users
                    if action_type in ["welcome_new_user", "invite_to_clouvel"]:
                        welcomed_users = state.welcomed_users or []
                        author = action.get("target_author")
                        if author and author not in welcomed_users:
                            welcomed_users.append(author)
                            state.welcomed_users = welcomed_users

                    # Update community knowledge for ambassador interactions
                    if action_type in [
                        "share_clouvel_magic",
                        "cross_promote",
                        "collaborate",
                    ]:
                        knowledge = state.community_knowledge or {}
                        subreddit_key = f"interactions_{self.subreddit_name}"
                        if subreddit_key not in knowledge:
                            knowledge[subreddit_key] = []
                        knowledge[subreddit_key].append(
                            {
                                "date": datetime.now(timezone.utc).isoformat(),
                                "action": action_type,
                                "target_author": action.get("target_author"),
                                "success": True,
                            }
                        )
                        # Keep only last 50 interactions per subreddit
                        knowledge[subreddit_key] = knowledge[subreddit_key][-50:]
                        state.community_knowledge = knowledge

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
        """Get community statistics with role-aware context"""
        try:
            subreddit = self.reddit.subreddit(self.subreddit_name)
            role, _ = self._get_role_context()

            base_stats = {
                "subscribers": subreddit.subscribers,
                "active_users": subreddit.active_user_count,
                "created_utc": subreddit.created_utc,
                "description": subreddit.public_description,
                "role": role,
                "subreddit": self.subreddit_name,
            }

            # Add role-specific stats
            if role == "moderator":
                with self._get_db_session() as session:
                    state = self._get_or_create_state(session)
                    base_stats["welcomed_users_count"] = len(state.welcomed_users or [])
                    base_stats["is_home_kingdom"] = True
            else:
                with self._get_db_session() as session:
                    state = self._get_or_create_state(session)
                    knowledge = state.community_knowledge or {}
                    interaction_key = f"interactions_{self.subreddit_name}"
                    base_stats["ambassador_interactions"] = len(
                        knowledge.get(interaction_key, [])
                    )
                    base_stats["is_home_kingdom"] = False

            return base_stats

        except Exception as e:
            logger.error(f"Error getting community stats: {e}")
            return {}
