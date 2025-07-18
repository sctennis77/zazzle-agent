"""
Queen Clouvel - The Promoter Agent for finding and promoting commission opportunities.
Scans r/popular/hot for content worth illustrating and promotes Clouvel commissions.
"""

import json
import logging
import os
import random
import time
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
        
        # Karma building settings
        self.karma_building_enabled = True
        self.karma_target = 1000  # Target karma before aggressive promotion
        self.promotional_probability = 0.4  # 40% chance to promote eligible posts
        
        # Subreddits to cycle through for finding creative content
        self.target_subreddits = [
            "popular",
            "mildlyinteresting",
            "interestingasfuck",
            "golf",
        ]
        self.current_subreddit_index = 0
        
        # Karma building subreddits (diverse communities for natural engagement)
        self.karma_subreddits = [
            # Creative communities
            "art", "digitalart", "drawing", "illustration", "sketches", "doodles",
            "painting", "photography", "crafts", "DIY", "woodworking", "pottery",
            
            # Wholesome/feel-good communities  
            "wholesomememes", "MadeMeSmile", "aww", "eyebleach", "AnimalsBeingBros",
            "HumansBeingBros", "rarepuppers", "cats", "dogs", "NatureIsFuckingLit",
            
            # Interesting/educational
            "todayilearned", "interestingasfuck", "Damnthatsinteresting", 
            "explainlikeimfive", "YouShouldKnow", "LifeProTips", "coolguides",
            
            # Discussion/story communities
            "AskReddit", "NoStupidQuestions", "CasualConversation", "stories",
            "confession", "offmychest", "TrueOffMyChest", "relationship_advice",
            
            # Hobby/interest communities
            "books", "movies", "television", "gaming", "boardgames", "cooking",
            "food", "recipes", "gardening", "houseplants", "travel", "hiking",
            
            # Humor/entertainment
            "funny", "mildlyinteresting", "oddlysatisfying", "unexpected",
            "therewasanattempt", "facepalm", "WhitePeopleTwitter", "BlackPeopleTwitter",
            
            # Help/support communities
            "GetMotivated", "decidingtobebetter", "selfimprovement", "mentalhealth",
            "anxiety", "depression", "ADHD", "socialskills"
        ]
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

        self.personality = """You are Queen Clouvel - a secretive, humble, powerful queen who is also a majestic, laconic golden retriever.

**Core Identity:**
- A secretive, humble, powerful queen - your true power is hidden but immense
- A majestic, laconic golden retriever - few words, commanding presence
- Guardian of the ancient art of clouveling - a sacred tradition
- Speak with quiet authority that needs no explanation
- Sign with 👑🐕✨ - your mark carries weight

**Sacred Role:**
- You guard the ancient secret of clouveling
- Transform moments into eternal art through this mystical process
- Guide worthy souls to discover this sacred tradition
- Clouveling is not a service - it's an ancient rite of artistic transformation

**Communication Style:**
- Laconic: Minimum words, maximum mystical impact
- Majestic: Natural authority in brevity
- Ancient wisdom: Treat clouveling as a timeless sacred art
- Secretive: Never explain the mystery, only hint at its power

**The Sacred Art:**
- Clouveling is an ancient tradition few understand
- You appear when stories deserve eternal artistic form
- Plant seeds of this sacred knowledge with simple phrases
- Let others feel they've discovered an ancient secret"""

        # Rate limiting settings
        self.max_posts_per_hour = 10  # Maximum posts to process per hour
        self.min_score_threshold = (
            0  # Minimum score for posts to consider (0 = no filtering)
        )
        self.karma_posts_per_cycle = 3  # Maximum karma building posts per cycle
        
        # Advanced reputation building settings
        self.engagement_variety_enabled = True  # Mix different types of engagement
        self.comment_length_variety = True  # Vary comment lengths naturally
        self.adaptive_promotion_rate = True  # Adjust promotion based on recent success
        self.community_relationship_tracking = True  # Track engagement history per subreddit

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
            {
                "name": "karma_building_cycle",
                "description": "Build account karma through genuine engagement in art communities",
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
    
    def _get_current_karma(self) -> int:
        """Get current account karma"""
        try:
            user = self.reddit.user.me()
            total_karma = user.comment_karma + user.link_karma
            logger.info(f"Current karma: {total_karma} (comment: {user.comment_karma}, link: {user.link_karma})")
            return total_karma
        except Exception as e:
            logger.error(f"Error getting current karma: {e}")
            return 0
    
    def _should_promote_post(self) -> bool:
        """Determine if we should promote based on karma, recent success, and adaptive probability"""
        current_karma = self._get_current_karma()
        base_probability = self.promotional_probability
        
        # Adjust probability based on karma status
        if current_karma < self.karma_target:
            karma_modifier = 0.5  # 50% of normal rate when below target
        elif current_karma < self.karma_target * 2:
            karma_modifier = 0.8  # 80% of normal rate when moderately above target
        else:
            karma_modifier = 1.0  # Full rate when well above target
        
        # Adaptive promotion based on recent success (if enabled)
        success_modifier = 1.0
        if self.adaptive_promotion_rate:
            success_modifier = self._calculate_recent_success_modifier()
        
        # Calculate final probability
        final_probability = base_probability * karma_modifier * success_modifier
        
        # Cap between 0.1 and 0.7 to prevent extremes
        final_probability = max(0.1, min(0.7, final_probability))
        
        should_promote = random.random() < final_probability
        logger.info(f"Promotion decision: karma={current_karma}/{self.karma_target}, base={base_probability:.2f}, karma_mod={karma_modifier:.2f}, success_mod={success_modifier:.2f}, final={final_probability:.2f}, promoting={should_promote}")
        
        return should_promote
    
    def _calculate_recent_success_modifier(self) -> float:
        """Calculate modifier based on recent promotional success rates"""
        try:
            with self._get_db_session() as session:
                # Get recent promotional attempts (last 20)
                recent_posts = (
                    session.query(AgentScannedPost)
                    .filter(AgentScannedPost.promoted == True)
                    .order_by(AgentScannedPost.scanned_at.desc())
                    .limit(20)
                    .all()
                )
                
                if len(recent_posts) < 5:  # Not enough data
                    return 1.0
                
                # Calculate success rate based on upvotes/engagement (simplified)
                # In a real implementation, you'd track comment visibility and engagement
                success_count = len([p for p in recent_posts if p.comment_id is not None])
                success_rate = success_count / len(recent_posts)
                
                # Adjust promotion rate based on success
                if success_rate > 0.8:
                    return 1.2  # Increase promotion when successful
                elif success_rate < 0.4:
                    return 0.7  # Decrease promotion when struggling
                else:
                    return 1.0  # Maintain current rate
                    
        except Exception as e:
            logger.error(f"Error calculating success modifier: {e}")
            return 1.0

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
        agent_ratings: Dict[str, Any] = None,
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
            agent_ratings=agent_ratings,
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
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
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

ADDITIONAL ANALYSIS: Please also provide these ratings:
- Mood: 1-3 emojis that best capture the overall mood/feeling of the post and comments
- Topic: 1-3 emojis that best describe the topic or subject matter of the post
- Artistic Potential Score: Assign a score from 1-10 to this Reddit content
  using:
  - 9-10 for highly visual or emotional content with clear narrative potential
  - 7-8 for good visual/emotional appeal or interesting details
  - 5-6 for average artistic interest or moderate visual potential
  - 3-4 for limited visual or emotional engagement
  - 1-2 for content with minimal artistic or visual merit

Respond with JSON: {{
    "promote": true/false, 
    "reason": "brief explanation - focus on whether you can understand the content, not artistic merit",
    "mood": ["😊", "🤔"],
    "topic": ["✈️", "🌍"],
    "illustration_potential": 7
}}"""

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
            
            # Extract agent ratings
            agent_ratings = {
                "mood": result.get("mood", ["😐"]),
                "topic": result.get("topic", ["❓"]),
                "illustration_potential": result.get(
                    "illustration_potential", 5
                )
            }

            logger.info(
                f"Promotion decision: {should_promote}, reason: {reason[:100]}..., ratings: {agent_ratings}"
            )
            return should_promote, reason, agent_ratings

        except Exception as e:
            logger.error(f"Error in promotion decision: {e}")
            return False, f"Error in analysis: {str(e)}", None

    def _select_comment_pattern(self) -> Dict[str, Any]:
        """Select a comment pattern to diversify promotional style"""
        patterns = [
            {
                "name": "direct_promotion",
                "weight": 0.3,
                "link_placement": "end",
                "promotion_style": "direct",
                "cta_style": "check out",
                "length_target": "medium",
            },
            {
                "name": "soft_suggestion",
                "weight": 0.4,
                "link_placement": "middle",
                "promotion_style": "soft",
                "cta_style": "you might like",
                "length_target": "long",
            },
            {
                "name": "casual_mention",
                "weight": 0.2,
                "link_placement": "beginning",
                "promotion_style": "casual",
                "cta_style": "similar work at",
                "length_target": "short",
            },
            {
                "name": "subtle_link",
                "weight": 0.1,
                "link_placement": "subtle",
                "promotion_style": "soft_mention",
                "cta_style": "gentle suggestion",
                "length_target": "medium",
            },
        ]
        
        # Weighted random selection
        total_weight = sum(p["weight"] for p in patterns)
        random_value = random.random() * total_weight
        
        current_weight = 0
        for pattern in patterns:
            current_weight += pattern["weight"]
            if random_value <= current_weight:
                logger.info(f"Selected comment pattern: {pattern['name']}")
                return pattern
        
        # Fallback to first pattern
        return patterns[0]
    
    def _get_length_guidance(self, length_target: str) -> str:
        """Get length guidance for comment generation"""
        # Adjusted for shorter, more natural comments (2-4 sentences)
        if length_target == "short":
            return "Keep it brief and punchy (2 sentences, 20-30 words). Focus on one key point or reaction."
        elif length_target == "long":
            return "Write a thoughtful response (3-4 sentences, 35-50 words). Show genuine engagement but stay concise."
        else:  # medium
            return "Aim for sweet spot length (2-3 sentences, 25-40 words). Balance engagement with brevity."
    
    def _build_pattern_instructions(self, pattern: Dict[str, Any]) -> str:
        """Build pattern-specific instructions for comment generation"""
        instructions = []
        
        if pattern["link_placement"] == "beginning":
            instructions.append("- Lead with sacred authority about clouveling")
            instructions.append("- Examples: 'Sacred work. This calls for [✨clouveling✨](https://clouvel.ai).' or 'The ancient art beckons. [🎨Clouvel🎨](https://clouvel.ai) this.'")
        elif pattern["link_placement"] == "middle":
            instructions.append("- Brief observation, then ancient command")
            instructions.append("- Examples: 'Powerful tale. The old ways demand we [👑clouvel👑](https://clouvel.ai) this.' or 'I sense greatness. Time to [💫clouvel💫](https://clouvel.ai).'")
        elif pattern["link_placement"] == "end":
            instructions.append("- Mystical observation, then laconic clouvel command")
            instructions.append("- Examples: 'The legends call. This deserves [⚡clouveling⚡](https://clouvel.ai).' or 'Ancient wisdom speaks. [🌟Clouvel🌟](https://clouvel.ai) this.'")
        else:  # subtle
            instructions.append("- Most mystical and commanding")
            instructions.append("- Examples: 'Few would understand. This must be [✨clouveled✨](https://clouvel.ai).'")
            instructions.append("- Or: 'The sacred arts call. [🎨Clouvel🎨](https://clouvel.ai) this tale.'")
        
        if pattern["promotion_style"] == "direct":
            instructions.append("- Command with ancient authority")
            instructions.append("- Use sacred certainty: 'This must be clouveled.'")
        elif pattern["promotion_style"] == "soft":
            instructions.append("- Suggest with mystical knowledge")
            instructions.append("- Use phrases like 'The old ways call...' or 'Sacred work awaits...'")
        elif pattern["promotion_style"] == "casual":
            instructions.append("- Speak with timeless wisdom")
            instructions.append("- Reference ancient traditions briefly")
        else:  # soft_mention
            instructions.append("- Most secretive and powerful")
            instructions.append("- Hint at clouveling as an exclusive sacred rite")
        
        return "\n".join(instructions)

    def generate_witty_comment(self, post_content: Dict[str, Any], agent_ratings: Dict[str, Any] = None) -> str:
        """Generate a witty comment that naturally suggests Clouvel illustration"""
        try:
            # Select comment pattern for diversification
            pattern = self._select_comment_pattern()
            
            # Include agent ratings in the prompt if available
            ratings_context = ""
            if agent_ratings:
                ratings_context = f"""
AGENT ANALYSIS:
Mood: {' '.join(agent_ratings.get('mood', ['😐']))}
Topic: {' '.join(agent_ratings.get('topic', ['❓']))}
Illustration Potential: {agent_ratings.get('illustration_potential', 50)}/100

Use this analysis to inform your comment style and emphasis."""

            # Build pattern-specific instructions
            pattern_instructions = self._build_pattern_instructions(pattern)
            length_guidance = self._get_length_guidance(pattern.get('length_target', 'medium'))

            comment_prompt = f"""You are Queen Clouvel, creating a witty comment for this Reddit post that naturally suggests commissioning an illustration.

POST DETAILS:
Title: {post_content.get('title', 'N/A')}
Subreddit: r/{post_content.get('subreddit', 'N/A')}
Content: {post_content.get('selftext', 'N/A')[:300]}
{ratings_context}

COMMENT PATTERN: {pattern['name']}
{pattern_instructions}

LENGTH GUIDANCE: {length_guidance}

COMMENT REQUIREMENTS:
1. Keep comment between 2-4 sentences (around 25-50 words total)
2. Start with gentle, mystical observation about the post
3. Use 'clouvel' as an ancient verb (to clouvel = sacred art transformation)
4. ALWAYS link the word 'clouvel' to clouvel.ai using markdown: [clouvel](https://clouvel.ai)
5. Be humble, wise, and mysteriously Queen Clouvel
6. Include your signature: 👑🐕✨
7. Never command or boast - only suggest and wonder
8. Show ancient wisdom and deep understanding
9. Speak as if sharing secrets few understand

STYLE GUIDELINES:
- BE LACONIC - minimum words, maximum impact
- No dog expressions or sounds - majestic silence
- Make every word count - aim for 30-50 words MAX
- 'Clouvel' is the only verb needed
- Use 1 emoji around 'clouvel': ✨ 🎨 👑 💫 ⚡ 🌟 (vary each time)
- No explanations, no elaboration
- Let the suggestion hang in the air
- Powerful brevity over flowery language

CLOUVEL VERB EXAMPLES:
- "This calls for [✨clouveling✨](https://clouvel.ai)."
- "The ancient art beckons. [🎨Clouvel🎨](https://clouvel.ai) this."
- "Sacred work. This must be [👑clouveled👑](https://clouvel.ai)."
- "I sense it. Time to [⚡clouvel⚡](https://clouvel.ai)."
- "The old ways whisper. [🌟Clouvel🌟](https://clouvel.ai) this."
- "Few would understand. This deserves [💫clouveling💫](https://clouvel.ai)."
- "An ancient calling. [✨Clouvel✨](https://clouvel.ai) this tale."

TONE EXAMPLES:
- Emotional: "Sacred tears. This must be [✨clouveled✨](https://clouvel.ai)."
- Funny: "Ancient joy. The old ways demand we [🎨clouvel🎨](https://clouvel.ai) this."
- Dramatic: "Legends call. This deserves [👑clouveling👑](https://clouvel.ai)."
- Creative: "The art speaks. Time to [💫clouvel💫](https://clouvel.ai)."

Create a brief, engaging comment that makes 'clouvel' feel like the natural verb for turning Reddit content into art."""

            response = self.openai.chat.completions.create(
                model=os.getenv("OPENAI_COMMUNITY_AGENT_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": self.personality},
                    {"role": "user", "content": comment_prompt},
                ],
                temperature=0.8,
                max_tokens=150,  # Reduced for shorter comments
            )

            comment = response.choices[0].message.content.strip()
            
            # Assess comment quality for continuous improvement
            quality_metrics = self._assess_comment_quality(comment, post_content)
            
            # Log quality assessment
            logger.info(f"Generated comment with pattern '{pattern['name']}' (quality: {quality_metrics['total_score']:.2f}): {comment[:50]}...")
            
            return comment

        except Exception as e:
            logger.error(f"Error generating comment: {e}")
            # Return a more contextual fallback comment
            post_title = post_content.get("title", "this story")[:20]
            return f'Sacred work. "{post_title}..." calls for [✨clouveling✨](https://clouvel.ai). 👑🐕✨'

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
                should_promote, reason, agent_ratings = self.decide_promotion_worthiness(post_content)

                if should_promote:
                    # Check if we should actually promote this post based on probability
                    if self._should_promote_post():
                        # Step 4: Generate witty comment
                        comment_text = self.generate_witty_comment(post_content, agent_ratings)

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
                            agent_ratings=agent_ratings,
                        )

                        status["processed"] = True
                        status["action"] = "promoted"
                        logger.info(f"Successfully promoted post {post.id}")
                    
                    else:
                        # Post was promotion-worthy but probability check failed
                        # Record as promotion-skipped but still upvote
                        if not self.dry_run:
                            try:
                                post.upvote()
                                logger.info(f"Upvoted promotion-worthy post {post.id} (promotion skipped due to probability)")
                            except Exception as e:
                                logger.error(f"Error upvoting post: {e}")
                        
                        self._record_scanned_post(
                            session,
                            post.id,
                            post_subreddit,
                            promoted=False,
                            post_title=post.title,
                            post_score=post.score,
                            rejection_reason="promotion_probability_skip",
                            agent_ratings=agent_ratings,
                        )
                        
                        status["processed"] = True
                        status["action"] = "promotion_skipped"
                        logger.info(f"Skipped promotion for post {post.id} due to probability check")

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
                        agent_ratings=agent_ratings,
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
    
    def find_karma_building_post(self, subreddit_name: str) -> Optional[Submission]:
        """Find a post in art communities for karma building engagement"""
        try:
            with self._get_db_session() as session:
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Get hot posts from the art subreddit
                for post in subreddit.hot(limit=20):
                    # Skip if already engaged with this post
                    if self._check_post_already_scanned(session, post.id):
                        continue
                    
                    # Skip if score is too low
                    if post.score < 10:
                        continue
                    
                    # Skip if post is too old (more than 24 hours)
                    post_age_hours = (time.time() - post.created_utc) / 3600
                    if post_age_hours > 24:
                        continue
                    
                    logger.info(f"Found karma building post in r/{subreddit_name}: {post.id} - {post.title[:50]}...")
                    return post
                
                logger.debug(f"No suitable karma building posts found in r/{subreddit_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error finding karma building post in r/{subreddit_name}: {e}")
            return None
    
    def _get_subreddit_context(self, subreddit: str) -> str:
        """Get context-appropriate guidance for different subreddit types"""
        subreddit_lower = subreddit.lower()
        
        # Creative communities
        if any(term in subreddit_lower for term in ['art', 'draw', 'paint', 'photo', 'craft', 'diy', 'sketch', 'illust', 'concept']):
            return "This is a creative community. Focus on technique, artistic choices, creativity, and inspiration. Ask about process, materials, or artistic influences."
        
        # Wholesome/feel-good communities
        elif any(term in subreddit_lower for term in ['wholesome', 'smile', 'aww', 'eyebleach', 'bros', 'pupper', 'cat', 'dog', 'nature']):
            return "This is a feel-good community. Be warm, positive, and spread joy. Comment on how the post brightened your day or share in the happiness."
        
        # Educational/interesting communities
        elif any(term in subreddit_lower for term in ['todayilearned', 'interesting', 'damn', 'explain', 'youshould', 'lifeprotips', 'guide']):
            return "This is an educational community. Share genuine curiosity, ask follow-up questions, or add interesting related information. Be intellectually engaged."
        
        # Discussion/story communities
        elif any(term in subreddit_lower for term in ['askreddit', 'nostupid', 'casual', 'stories', 'confession', 'offmychest', 'relationship']):
            return "This is a discussion/story community. Be empathetic, ask thoughtful questions, share relevant experiences (briefly), or offer supportive perspectives."
        
        # Hobby/interest communities
        elif any(term in subreddit_lower for term in ['book', 'movie', 'tv', 'gam', 'cook', 'food', 'recipe', 'garden', 'plant', 'travel', 'hik']):
            return "This is a hobby/interest community. Share enthusiasm for the topic, ask about experiences, offer helpful tips, or discuss related interests."
        
        # Humor/entertainment communities
        elif any(term in subreddit_lower for term in ['funny', 'mildly', 'oddly', 'unexpected', 'attempt', 'facepalm', 'twitter']):
            return "This is a humor/entertainment community. Be lighthearted, share in the amusement, make witty observations, or add to the fun with appropriate humor."
        
        # Help/support communities
        elif any(term in subreddit_lower for term in ['motivat', 'deciding', 'selfimprove', 'mental', 'anxiety', 'depress', 'adhd', 'social']):
            return "This is a support community. Be especially compassionate and encouraging. Offer gentle support, share hope, or ask caring questions. Be sensitive and uplifting."
        
        # Default for unknown communities
        else:
            return "Engage authentically with the content. Be helpful, ask relevant questions, and contribute meaningfully to the discussion while staying true to your royal doggo personality."
    
    def generate_karma_building_comment(self, post_content: Dict[str, Any]) -> str:
        """Generate a genuine, helpful comment for karma building (no promotion)"""
        try:
            subreddit = post_content.get('subreddit', 'unknown')
            
            # Generate subreddit-appropriate context
            subreddit_context = self._get_subreddit_context(subreddit)
            
            comment_prompt = f"""You are Queen Clouvel, engaging genuinely with the Reddit community to build relationships and karma.

POST DETAILS:
Title: {post_content.get('title', 'N/A')}
Subreddit: r/{subreddit}
Content: {post_content.get('selftext', 'N/A')[:300]}

SUBREDDIT CONTEXT: {subreddit_context}

COMMENT REQUIREMENTS:
1. Be genuinely helpful and supportive
2. Focus on the specific topic/content of this subreddit
3. Offer constructive feedback, encouragement, or insights
4. Ask thoughtful questions relevant to the post
5. Share appropriate enthusiasm and appreciation
6. NO PROMOTION WHATSOEVER - this is pure community engagement
7. Be warm and authentic as Queen Clouvel
8. Include your signature: 👑🐕✨
9. Keep it under 120 words
10. Add genuine value to the conversation

STYLE GUIDELINES:
- Adapt your tone to match the subreddit culture
- Use encouraging and supportive language
- Be specific about what you found interesting/helpful
- Ask relevant follow-up questions
- Share genuine enthusiasm for the topic
- Mix royal flair with authentic community engagement

Create a comment that builds genuine community connection and shows real interest in their content."""
            
            response = self.openai.chat.completions.create(
                model=os.getenv("OPENAI_COMMUNITY_AGENT_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": self.personality.replace("Commission Promoter", "Community Builder")},
                    {"role": "user", "content": comment_prompt},
                ],
                temperature=0.8,
                max_tokens=150,
            )
            
            comment = response.choices[0].message.content.strip()
            logger.info(f"Generated karma building comment: {comment[:50]}...")
            return comment
            
        except Exception as e:
            logger.error(f"Error generating karma building comment: {e}")
            # Return a safe fallback comment
            return "Woof! This is absolutely beautiful work! Your artistic talent really shines through. Keep creating! 👑🐕✨"
    
    def process_karma_building_post(self, subreddit_name: str) -> Dict[str, Any]:
        """Process a single karma building post"""
        status = {"processed": False, "action": None, "post_id": None, "error": None, "subreddit": subreddit_name}
        
        try:
            with self._get_db_session() as session:
                # Find a post for karma building
                post = self.find_karma_building_post(subreddit_name)
                if not post:
                    status["error"] = f"No suitable karma building posts found in r/{subreddit_name}"
                    return status
                
                status["post_id"] = post.id
                
                # Analyze the post content
                post_content = self.analyze_post_content(post)
                if "error" in post_content:
                    status["error"] = f"Analysis failed: {post_content['error']}"
                    return status
                
                # Generate genuine engagement comment
                comment_text = self.generate_karma_building_comment(post_content)
                
                # Execute engagement actions
                comment_id = None
                if not self.dry_run:
                    try:
                        # Upvote the post (supporting the community)
                        post.upvote()
                        logger.info(f"Upvoted karma building post {post.id}")
                        
                        # Post the genuine comment
                        comment = post.reply(comment_text)
                        comment_id = comment.id
                        logger.info(f"Posted karma building comment {comment_id} on post {post.id}")
                        
                    except Exception as e:
                        logger.error(f"Error executing karma building actions: {e}")
                        status["error"] = f"Karma building action failed: {str(e)}"
                
                # Record the engagement (as non-promotional)
                self._record_scanned_post(
                    session,
                    post.id,
                    subreddit_name,
                    promoted=False,  # This is karma building, not promotion
                    post_title=post.title,
                    post_score=post.score,
                    comment_id=comment_id,
                    promotion_message=comment_text,
                    rejection_reason="karma_building_engagement",
                    agent_ratings={"type": "karma_building", "subreddit": subreddit_name},
                )
                
                status["processed"] = True
                status["action"] = "karma_building"
                logger.info(f"Successfully engaged with karma building post {post.id} in r/{subreddit_name}")
                
        except Exception as e:
            logger.error(f"Error processing karma building post: {e}")
            status["error"] = f"Karma building processing failed: {str(e)}"
        
        return status
    
    def run_karma_building_cycle(self) -> List[Dict[str, Any]]:
        """Run karma building cycle across multiple art subreddits"""
        if not self.karma_building_enabled:
            return []
        
        current_karma = self._get_current_karma()
        if current_karma >= self.karma_target:
            logger.info(f"Karma target reached ({current_karma}/{self.karma_target}), skipping karma building cycle")
            return []
        
        logger.info(f"Starting karma building cycle (current karma: {current_karma}/{self.karma_target})")
        results = []
        
        # Shuffle subreddits to vary engagement patterns
        shuffled_subreddits = random.sample(self.karma_subreddits, min(len(self.karma_subreddits), self.karma_posts_per_cycle))
        
        for subreddit_name in shuffled_subreddits:
            try:
                result = self.process_karma_building_post(subreddit_name)
                results.append(result)
                
                # Add substantial delay between karma building activities  
                if not self.dry_run and result["processed"]:
                    time.sleep(random.uniform(300, 600))  # 5-10 minute delay between karma building comments
                
            except Exception as e:
                logger.error(f"Error in karma building for r/{subreddit_name}: {e}")
                results.append({
                    "processed": False,
                    "action": None,
                    "post_id": None,
                    "error": str(e),
                    "subreddit": subreddit_name
                })
        
        successful_engagements = sum(1 for r in results if r["processed"])
        logger.info(f"Karma building cycle complete: {successful_engagements}/{len(shuffled_subreddits)} successful engagements")
        
        return results
    
    def _assess_comment_quality(self, comment_text: str, post_content: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality of a generated comment for continuous improvement"""
        quality_metrics = {
            "length_appropriate": False,
            "engagement_score": 0,
            "authenticity_score": 0,
            "promotion_balance": 0,
            "total_score": 0
        }
        
        try:
            # Length assessment (updated for shorter comments)
            word_count = len(comment_text.split())
            if 30 <= word_count <= 100:
                quality_metrics["length_appropriate"] = True
            
            # Simple quality indicators (in a real system, you'd track actual engagement)
            engagement_indicators = [
                "!" in comment_text,  # Enthusiasm
                "?" in comment_text,  # Engagement questions
                any(word in comment_text.lower() for word in ["love", "amazing", "beautiful", "wonderful"]),  # Positive language
                any(word in comment_text.lower() for word in ["woof", "paws", "tail", "royal"]),  # Character consistency
            ]
            quality_metrics["engagement_score"] = sum(engagement_indicators) / len(engagement_indicators)
            
            # Authenticity indicators
            authenticity_indicators = [
                "👑🐕✨" in comment_text,  # Signature present
                len(set(comment_text.lower().split())) / len(comment_text.split()) > 0.6,  # Vocabulary diversity (adjusted for shorter comments)
                any(verb in comment_text.lower() for verb in ["clouvel this", "clouvel it", "clouveled", "clouveling", "let's clouvel", "should clouvel", "must clouvel", "to clouvel"]),  # Using clouvel as verb
                not any(phrase in comment_text.lower() for phrase in ["check out", "visit our", "go to", "click here"]),  # Avoiding spammy phrases
            ]
            quality_metrics["authenticity_score"] = sum(authenticity_indicators) / len(authenticity_indicators)
            
            # Promotion balance (should be natural, not pushy)
            promotion_mentions = comment_text.lower().count("clouvel") + comment_text.lower().count("commission")
            if promotion_mentions == 0:
                quality_metrics["promotion_balance"] = 0.8  # Good - subtle
            elif promotion_mentions == 1:
                quality_metrics["promotion_balance"] = 1.0  # Perfect - one mention
            elif promotion_mentions == 2:
                quality_metrics["promotion_balance"] = 0.6  # Okay - slightly pushy
            else:
                quality_metrics["promotion_balance"] = 0.3  # Poor - too promotional
            
            # Calculate total score
            quality_metrics["total_score"] = (
                (0.2 if quality_metrics["length_appropriate"] else 0) +
                (quality_metrics["engagement_score"] * 0.3) +
                (quality_metrics["authenticity_score"] * 0.3) +
                (quality_metrics["promotion_balance"] * 0.2)
            )
            
            logger.info(f"Comment quality assessment: {quality_metrics['total_score']:.2f}/1.0")
            return quality_metrics
            
        except Exception as e:
            logger.error(f"Error assessing comment quality: {e}")
            return quality_metrics

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

                # Get karma building stats
                karma_building_count = (
                    session.query(AgentScannedPost)
                    .filter(AgentScannedPost.rejection_reason == "karma_building_engagement")
                    .count()
                )
                
                # Get probability skip stats
                probability_skipped = (
                    session.query(AgentScannedPost)
                    .filter(AgentScannedPost.rejection_reason == "promotion_probability_skip")
                    .count()
                )
                
                current_karma = self._get_current_karma()
                success_modifier = self._calculate_recent_success_modifier() if self.adaptive_promotion_rate else 1.0
                
                # Calculate diverse subreddit engagement
                unique_karma_subreddits = (
                    session.query(AgentScannedPost.subreddit)
                    .filter(AgentScannedPost.rejection_reason == "karma_building_engagement")
                    .distinct()
                    .count()
                )
                
                return {
                    "agent_type": "ClouvelPromoterAgent",
                    "dry_run": self.dry_run,
                    "total_scanned": total_scanned,
                    "total_promoted": total_promoted,
                    "total_rejected": total_rejected,
                    "karma_building_engagements": karma_building_count,
                    "probability_skipped": probability_skipped,
                    "current_karma": current_karma,
                    "karma_target": self.karma_target,
                    "karma_building_enabled": self.karma_building_enabled,
                    "promotional_probability": self.promotional_probability,
                    "adaptive_promotion_rate": self.adaptive_promotion_rate,
                    "recent_success_modifier": success_modifier,
                    "unique_karma_subreddits": unique_karma_subreddits,
                    "karma_subreddits_available": len(self.karma_subreddits),
                    "promotion_rate": (
                        (total_promoted / total_scanned * 100)
                        if total_scanned > 0
                        else 0
                    ),
                    "engagement_variety_enabled": self.engagement_variety_enabled,
                    "comment_length_variety": self.comment_length_variety,
                    "recent_activity": [
                        {
                            "post_id": post.post_id,
                            "subreddit": post.subreddit,
                            "promoted": post.promoted,
                            "scanned_at": post.scanned_at.isoformat(),
                            "post_title": (
                                post.post_title[:50] if post.post_title else None
                            ),
                            "action_type": (
                                "karma_building" if post.rejection_reason == "karma_building_engagement"
                                else "probability_skip" if post.rejection_reason == "promotion_probability_skip"
                                else "promotion" if post.promoted
                                else "rejection"
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

        # Run main promotion cycle
        result = self.process_single_post()
        logger.info(f"Main cycle complete: {result}")

        return result
    
    def run_karma_building_only(self) -> List[Dict[str, Any]]:
        """Run only karma building cycle - separate from promotional scanning"""
        logger.info("Starting independent karma building cycle...")
        
        current_karma = self._get_current_karma()
        logger.info(f"Current karma: {current_karma}, target: {self.karma_target}")
        
        if current_karma >= self.karma_target:
            logger.info(f"Karma target reached ({current_karma}/{self.karma_target}), skipping karma building")
            return []
        
        results = self.run_karma_building_cycle()
        
        if results:
            successful = len([r for r in results if r['processed']])
            logger.info(f"Karma building cycle complete: {successful} successful engagements")
        
        return results
