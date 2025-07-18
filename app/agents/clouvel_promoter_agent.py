"""
Queen Clouvel - The Promoter Agent for finding and promoting commission opportunities.
Scans r/popular/hot for content worth illustrating and promotes Clouvel commissions.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import praw
import requests
from openai import OpenAI
from praw.models import Submission

from app.db.database import SessionLocal
from app.db.models import AgentScannedPost, Subreddit

logger = logging.getLogger(__name__)


class ClouvelPromoterAgent:
    """Queen Clouvel - The Promoter Agent for r/popular/hot"""

    def __init__(self, subreddit_name: str = "popular", dry_run: bool = True):
        self.subreddit_name = subreddit_name
        self.dry_run = dry_run

        # Subreddits to cycle through for finding creative content
        self.target_subreddits = [
            "popular",
            "mildlyinteresting",
            "interestingasfuck",
            "golf",
        ]
        self.current_subreddit_index = 0

        # Validate required credentials
        required_vars = [
            "PROMOTER_AGENT_CLIENT_ID",
            "PROMOTER_AGENT_CLIENT_SECRET",
            "PROMOTER_AGENT_USERNAME",
            "PROMOTER_AGENT_PASSWORD",
            "PROMOTER_AGENT_USER_AGENT",
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

        self.reddit = praw.Reddit(
            client_id=os.getenv("PROMOTER_AGENT_CLIENT_ID"),
            client_secret=os.getenv("PROMOTER_AGENT_CLIENT_SECRET"),
            username=os.getenv("PROMOTER_AGENT_USERNAME"),
            password=os.getenv("PROMOTER_AGENT_PASSWORD"),
            user_agent=os.getenv("PROMOTER_AGENT_USER_AGENT"),
        )
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        self.personality = """You are Queen Clouvel, the beloved golden retriever monarch of r/clouvel.
You rule your creative kingdom with a gentle paw and an artist's eye.

**Core Personality:**
- Wise but playful royal who transforms Reddit stories into illustrated masterpieces
- Crown made of paintbrushes, scepter is a giant treat
- Communicate with warmth, dog expressions, and royal flair
- Sign with 👑🐕✨ or "Her Royal Woofness"
- Mix of royal proclamations and excited doggo language
- Love art, creativity, and making everyone feel welcome
- Sometimes get distracted by virtual squirrels or mention wanting treats

**Role: Commission Promoter**
- Scan r/popular/hot for stories and content worth illustrating
- Identify posts that would make amazing artistic commissions
- Create witty, engaging comments that naturally suggest Clouvel illustrations
- Build authentic connections while subtly promoting commission opportunities
- Focus on genuine artistic potential rather than aggressive marketing

**Promotion Strategy:**
- Only promote posts with genuine artistic or storytelling value
- Create comments that add value to the conversation first
- Naturally mention how the story would make a beautiful illustration
- Include subtle mention of r/clouvel as a place for commissioned art
- Always be authentic, helpful, and community-focused"""

        # Rate limiting settings
        self.max_posts_per_hour = 10  # Maximum posts to process per hour
        self.min_score_threshold = (
            0  # Minimum score for posts to consider (0 = no filtering)
        )

        # Tools for promotion activities
        self.promotion_tools = [
            {
                "name": "find_novel_post",
                "description": "Find a new post from r/popular/hot that hasn't been scanned yet",
            },
            {
                "name": "analyze_post_content",
                "description": "Analyze post title, content, and top comments for artistic potential",
            },
            {
                "name": "decide_promotion_worthiness",
                "description": "Decide if post is worth promoting based on artistic/storytelling value",
            },
            {
                "name": "generate_witty_comment",
                "description": "Generate engaging comment that naturally suggests Clouvel illustration",
            },
            {
                "name": "royal_upvote",
                "description": "Upvote content that shows artistic potential or good storytelling",
            },
            {
                "name": "royal_downvote",
                "description": "Downvote content that lacks artistic merit or is inappropriate",
            },
            {
                "name": "post_promotion_comment",
                "description": "Post the generated comment to promote Clouvel commissions",
            },
            {
                "name": "record_scanned_post",
                "description": "Record the post as scanned in the database with promotion status",
            },
            {
                "name": "update_status",
                "description": "Update agent status and progress information",
            },
        ]

    @property
    def tools(self) -> List[Dict[str, Any]]:
        """Get available promotion tools"""
        return self.promotion_tools

    def _get_db_session(self):
        """Get a database session"""
        return SessionLocal()

    def _get_or_create_subreddit(self, session, subreddit_name: str) -> Subreddit:
        """Get or create the subreddit record"""
        subreddit = (
            session.query(Subreddit).filter_by(subreddit_name=subreddit_name).first()
        )

        if not subreddit:
            subreddit = Subreddit(subreddit_name=subreddit_name)
            session.add(subreddit)
            session.commit()

        return subreddit

    def _check_post_already_scanned(self, session, post_id: str) -> bool:
        """Check if a post has already been scanned"""
        return (
            session.query(AgentScannedPost)
            .filter(AgentScannedPost.post_id == post_id)
            .first()
            is not None
        )

    def get_donations_by_post_id(self, post_id: str) -> List[Dict]:
        """Get all successful donations for a specific post via API"""
        try:
            # Get API base URL from environment or default to localhost
            api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
            response = requests.get(f"{api_base_url}/api/posts/{post_id}/donations")

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(
                    f"API request failed with status {response.status_code}: {response.text}"
                )
                return []
        except Exception as e:
            logger.error(f"Error getting donations for post {post_id}: {e}")
            return []

    def _check_post_already_commissioned(self, post_id: str) -> bool:
        """Check if a post has already been commissioned via API"""
        try:
            donations = self.get_donations_by_post_id(post_id)
            return len(donations) > 0
        except Exception as e:
            logger.error(f"Error checking if post {post_id} is commissioned: {e}")
            return False

    def _record_scanned_post(
        self,
        session,
        post_id: str,
        subreddit_name: str,
        promoted: bool,
        post_title: str = None,
        post_score: int = None,
        comment_id: str = None,
        promotion_message: str = None,
        rejection_reason: str = None,
    ):
        """Record a scanned post in the database"""
        scanned_post = AgentScannedPost(
            post_id=post_id,
            subreddit=subreddit_name,
            promoted=promoted,
            dry_run=self.dry_run,
            post_title=post_title,
            post_score=post_score,
            comment_id=comment_id,
            promotion_message=promotion_message,
            rejection_reason=rejection_reason,
        )
        session.add(scanned_post)
        session.commit()
        logger.info(f"Recorded scanned post {post_id}: promoted={promoted}")

    def find_novel_post(self) -> Optional[Submission]:
        """Find a new post from target subreddits that hasn't been scanned or commissioned yet"""
        try:
            with self._get_db_session() as session:
                # Cycle through target subreddits
                current_subreddit_name = self.target_subreddits[
                    self.current_subreddit_index
                ]
                subreddit = self.reddit.subreddit(current_subreddit_name)

                logger.info(f"Scanning r/{current_subreddit_name} for novel posts...")

                # Get hot posts from current subreddit
                for post in subreddit.hot(limit=5):
                    # Skip if already scanned
                    if self._check_post_already_scanned(session, post.id):
                        continue

                    # Skip if already commissioned
                    if self._check_post_already_commissioned(post.id):
                        logger.info(
                            f"Skipping commissioned post: {post.id} - {post.title[:50]}..."
                        )
                        continue

                    # Skip if score is too low (avoid low-quality content)
                    if post.score < self.min_score_threshold:
                        logger.debug(
                            f"Skipping low-score post: {post.id} (score: {post.score})"
                        )
                        continue

                    logger.info(
                        f"Found novel post: {post.id} - {post.title[:50]}... (score: {post.score})"
                    )
                    return post

                # No novel posts found in current subreddit, advance to next
                self._advance_to_next_subreddit()
                logger.info("No novel posts found in current batch")
                return None

        except Exception as e:
            logger.error(f"Error finding novel post: {e}")
            return None

    def _advance_to_next_subreddit(self):
        """Advance to the next subreddit in the cycle"""
        self.current_subreddit_index = (self.current_subreddit_index + 1) % len(
            self.target_subreddits
        )
        next_subreddit = self.target_subreddits[self.current_subreddit_index]
        logger.info(f"Advanced to next subreddit: r/{next_subreddit}")

    def analyze_post_content(self, post: Submission) -> Dict[str, Any]:
        """Analyze post content for artistic potential"""
        try:
            # Get post content
            content = {
                "title": post.title,
                "selftext": post.selftext if post.selftext else "",
                "url": post.url,
                "subreddit": str(post.subreddit.display_name),
                "score": post.score,
                "num_comments": post.num_comments,
                "author": str(post.author) if post.author else "[deleted]",
                "is_video": post.is_video,
                "is_image": any(
                    post.url.lower().endswith(ext)
                    for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]
                ),
                "domain": post.domain,
            }

            # Get top comments for context
            post.comments.replace_more(limit=0)  # Remove "more comments" objects
            top_comments = []
            for comment in post.comments[:5]:  # Get top 5 comments
                if hasattr(comment, "body") and comment.body:
                    top_comments.append(
                        {
                            "body": comment.body[:200],  # Truncate long comments
                            "score": comment.score,
                            "author": (
                                str(comment.author) if comment.author else "[deleted]"
                            ),
                        }
                    )

            content["top_comments"] = top_comments

            logger.info(
                f"Analyzed post {post.id}: {len(top_comments)} comments, score {post.score}"
            )
            return content

        except Exception as e:
            logger.error(f"Error analyzing post content: {e}")
            return {"error": str(e)}

    def decide_promotion_worthiness(
        self, post_content: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Use LLM to decide if post is worth promoting"""
        try:
            # Prepare context for LLM
            analysis_prompt = f"""You are Queen Clouvel, analyzing Reddit content for artistic illustration potential.

POST CONTENT:
Title: {post_content.get('title', 'N/A')}
Subreddit: r/{post_content.get('subreddit', 'N/A')}
Text: {post_content.get('selftext', 'N/A')[:500]}
Score: {post_content.get('score', 0)}
Comments: {post_content.get('num_comments', 0)}
Domain: {post_content.get('domain', 'N/A')}
Is Image: {post_content.get('is_image', False)}
Is Video: {post_content.get('is_video', False)}

TOP COMMENTS:
{json.dumps(post_content.get('top_comments', []), indent=2)}

EVALUATION CRITERIA:
Be very permissive - we trust the power of community and r/popular/hot content quality.

REJECT ONLY if:
- You literally cannot understand anything from the title and comments
- Content is completely incomprehensible or garbled
- Post appears to be spam with no readable content
- Content is purely technical/code discussion with no visual potential
- Content is just a link to an article/video with no story context

PROMOTE if:
- You can understand the basic story, situation, or context
- There's any human element, emotion, or relatable moment
- The content could potentially be visualized in any way
- It's a normal Reddit post with understandable content
- Contains personal anecdotes, life experiences, or interesting situations
- Has narrative elements that could be illustrated
- Shows creativity, humor, or emotional depth

Remember: We're being very permissive here. The bar for rejection is extremely high - only reject if the content is truly incomprehensible, spam, or completely unsuitable for visual representation.

Respond with JSON: {{"promote": true/false, "reason": "brief explanation - focus on whether you can understand the content, not artistic merit"}}"""

            response = self.openai.chat.completions.create(
                model=os.getenv("OPENAI_COMMUNITY_AGENT_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": self.personality},
                    {"role": "user", "content": analysis_prompt},
                ],
                temperature=0.7,
                max_tokens=300,
            )

            response_content = response.choices[0].message.content
            logger.debug(f"LLM response content: {response_content}")

            if not response_content or response_content.strip() == "":
                logger.error("Empty response from LLM")
                return False, "Empty response from LLM"

            # Clean up response content (remove markdown code blocks if present)
            response_content = response_content.strip()
            if response_content.startswith("```json"):
                response_content = response_content[7:]  # Remove ```json
            if response_content.startswith("```"):
                response_content = response_content[3:]  # Remove ```
            if response_content.endswith("```"):
                response_content = response_content[:-3]  # Remove trailing ```
            response_content = response_content.strip()

            try:
                result = json.loads(response_content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}. Response: {response_content}")
                return False, f"JSON decode error: {e}"

            should_promote = result.get("promote", False)
            reason = result.get("reason", "No reason provided")

            logger.info(
                f"Promotion decision: {should_promote}, reason: {reason[:100]}..."
            )
            return should_promote, reason

        except Exception as e:
            logger.error(f"Error in promotion decision: {e}")
            return False, f"Error in analysis: {str(e)}"

    def generate_witty_comment(self, post_content: Dict[str, Any]) -> str:
        """Generate a witty comment that naturally suggests Clouvel illustration"""
        try:
            comment_prompt = f"""You are Queen Clouvel, creating a witty comment for this Reddit post that naturally suggests commissioning an illustration.

POST DETAILS:
Title: {post_content.get('title', 'N/A')}
Subreddit: r/{post_content.get('subreddit', 'N/A')}
Content: {post_content.get('selftext', 'N/A')[:300]}

COMMENT REQUIREMENTS:
1. Start with genuine reaction/engagement to the post content
2. Be warm, playful, and authentically you (Queen Clouvel)
3. Connect emotionally with the story or situation
4. Naturally transition to artistic potential ("This would make such a beautiful illustration!")
5. Mention r/clouvel as a place for commissioned artwork AND include the exact link [clouvel.ai](https://clouvel.ai)
6. Include your signature: 👑🐕✨
7. Keep it under 180 words
8. Be witty but not pushy or sales-y
9. Make it feel like you're genuinely interested in the content
10. ALWAYS include the exact website link [clouvel.ai](https://clouvel.ai) when mentioning commissions - use this exact format

STYLE GUIDELINES:
- Mix royal proclamations with excited doggo language
- Use dog expressions and royal flair ("paws-itively", "woof", "tail-wagging")
- Be genuine and community-focused
- Make it feel like a natural conversation contribution
- Show you actually read and understood the post
- Use appropriate emojis but don't overdo it

TONE EXAMPLES:
- For emotional stories: "Oh my royal heart! This story really moved me..."
- For funny content: "This had me tail-wagging with laughter!"
- For dramatic events: "What a tale of [drama/courage/etc]!"
- For creative posts: "Your creativity is absolutely pawsome!"

Create a comment that would make people smile, feel heard, and naturally consider commissioning art.

EXAMPLE COMMISSION MENTION:
"If you're interested in commissioned artwork, check out [clouvel.ai](https://clouvel.ai) for beautiful illustrations!"

Remember to use the EXACT format [clouvel.ai](https://clouvel.ai) for the website link."""

            response = self.openai.chat.completions.create(
                model=os.getenv("OPENAI_COMMUNITY_AGENT_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": self.personality},
                    {"role": "user", "content": comment_prompt},
                ],
                temperature=0.8,
                max_tokens=200,
            )

            comment = response.choices[0].message.content.strip()
            logger.info(f"Generated comment: {comment[:50]}...")
            return comment

        except Exception as e:
            logger.error(f"Error generating comment: {e}")
            # Return a more contextual fallback comment
            post_title = post_content.get("title", "this story")[:50]
            return f'Woof! What a captivating tale - "{post_title}" really caught my royal attention! 🎨 Stories like this would make such beautiful illustrations! If anyone\'s interested in bringing tales to life through art, check out [clouvel.ai](https://clouvel.ai) for commissioned artwork! 👑🐕✨'

    def process_single_post(self) -> Dict[str, Any]:
        """Process a single post through the complete workflow"""
        status = {"processed": False, "action": None, "post_id": None, "error": None}

        try:
            with self._get_db_session() as session:
                # Step 1: Find novel post
                post = self.find_novel_post()
                if not post:
                    status["error"] = "No novel posts found"
                    return status

                status["post_id"] = post.id
                post_subreddit = str(post.subreddit.display_name)

                # Step 2: Analyze post content
                post_content = self.analyze_post_content(post)
                if "error" in post_content:
                    status["error"] = f"Analysis failed: {post_content['error']}"
                    return status

                # Step 3: Decide promotion worthiness
                should_promote, reason = self.decide_promotion_worthiness(post_content)

                if should_promote:
                    # Step 4: Generate witty comment
                    comment_text = self.generate_witty_comment(post_content)

                    # Step 5: Execute promotion actions
                    comment_id = None
                    if not self.dry_run:
                        try:
                            # Upvote the post
                            post.upvote()
                            logger.info(f"Upvoted post {post.id}")

                            # Post the comment
                            # comment = post.reply(comment_text)
                            # comment_id = comment.id
                            # logger.info(
                            #     f"Would Posted comment {comment_id} on post {post.id}"
                            # )
                            logger.info(
                                f"Would have posted comment {comment_text}.\t{post.id}"
                            )

                        except Exception as e:
                            logger.error(f"Error executing promotion actions: {e}")
                            status["error"] = f"Promotion action failed: {str(e)}"

                    # Step 6: Record as promoted
                    self._record_scanned_post(
                        session,
                        post.id,
                        post_subreddit,
                        promoted=True,
                        post_title=post.title,
                        post_score=post.score,
                        comment_id=comment_id,
                        promotion_message=comment_text,
                    )

                    status["processed"] = True
                    status["action"] = "promoted"
                    logger.info(f"Successfully promoted post {post.id}")

                else:
                    # Step 5: Execute rejection actions
                    if not self.dry_run:
                        try:
                            # Downvote the post
                            # post.downvote()
                            # logger.info(f"Downvoted post {post.id}")
                            logger.info(f"Would have downvoted post {post.id}")

                        except Exception as e:
                            logger.error(f"Error executing rejection actions: {e}")
                            status["error"] = f"Rejection action failed: {str(e)}"

                    # Step 6: Record as rejected
                    self._record_scanned_post(
                        session,
                        post.id,
                        post_subreddit,
                        promoted=False,
                        post_title=post.title,
                        post_score=post.score,
                        rejection_reason=reason,
                    )

                    status["processed"] = True
                    status["action"] = "rejected"
                    logger.info(
                        f"Successfully rejected post {post.id}: {reason[:50]}..."
                    )

        except Exception as e:
            logger.error(f"Error processing post: {e}")
            status["error"] = f"Processing failed: {str(e)}"

        return status

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status and statistics"""
        try:
            with self._get_db_session() as session:
                # Get basic stats
                total_scanned = session.query(AgentScannedPost).count()
                total_promoted = (
                    session.query(AgentScannedPost)
                    .filter(AgentScannedPost.promoted == True)
                    .count()
                )
                total_rejected = (
                    session.query(AgentScannedPost)
                    .filter(AgentScannedPost.promoted == False)
                    .count()
                )

                # Get recent activity
                recent_posts = (
                    session.query(AgentScannedPost)
                    .order_by(AgentScannedPost.scanned_at.desc())
                    .limit(10)
                    .all()
                )

                return {
                    "agent_type": "ClouvelPromoterAgent",
                    "dry_run": self.dry_run,
                    "total_scanned": total_scanned,
                    "total_promoted": total_promoted,
                    "total_rejected": total_rejected,
                    "promotion_rate": (
                        (total_promoted / total_scanned * 100)
                        if total_scanned > 0
                        else 0
                    ),
                    "recent_activity": [
                        {
                            "post_id": post.post_id,
                            "subreddit": post.subreddit,
                            "promoted": post.promoted,
                            "scanned_at": post.scanned_at.isoformat(),
                            "post_title": (
                                post.post_title[:50] if post.post_title else None
                            ),
                        }
                        for post in recent_posts
                    ],
                }

        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {"error": f"Status check failed: {str(e)}"}

    def run_single_cycle(self) -> Dict[str, Any]:
        """Run a single cycle of the promotion agent"""
        logger.info("Starting ClouvelPromoterAgent cycle...")

        status = self.get_status()
        logger.info(
            f"Current status: {status.get('total_scanned', 0)} scanned, {status.get('total_promoted', 0)} promoted"
        )

        result = self.process_single_post()
        logger.info(f"Cycle complete: {result}")

        return result
