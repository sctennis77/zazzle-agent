import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import praw

from app.utils.logging_config import get_logger, log_operation

logger = get_logger(__name__)


class RedditClient:
    """Client for interacting with Reddit API."""

    def __init__(self):
        """Initialize Reddit client with credentials from environment variables."""
        try:
            log_operation(
                logger, "init", "started", {"mode": os.getenv("REDDIT_MODE", "dryrun")}
            )

            self.reddit = praw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID"),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                username=os.getenv("REDDIT_USERNAME"),
                password=os.getenv("REDDIT_PASSWORD"),
                user_agent=os.getenv(
                    "REDDIT_USER_AGENT", "zazzle-agent by u/yourusername"
                ),
            )

            # Determine operation mode (live or dry run)
            self.mode = os.getenv("REDDIT_MODE", "dryrun").lower()
            if self.mode not in ["dryrun", "live"]:
                log_operation(
                    logger,
                    "init",
                    "warning",
                    {
                        "message": f"Invalid REDDIT_MODE '{self.mode}'. Defaulting to 'dryrun'.",
                        "mode": self.mode,
                    },
                )
                self.mode = "dryrun"

            if self.mode == "dryrun":
                log_operation(
                    logger,
                    "init",
                    "info",
                    {
                        "message": "Operating in DRY RUN mode. No actual Reddit actions will be performed.",
                        "mode": self.mode,
                    },
                )
            else:
                log_operation(
                    logger,
                    "init",
                    "info",
                    {
                        "message": "Operating in LIVE mode. Actions will be performed on Reddit.",
                        "mode": self.mode,
                    },
                )

            # Verify credentials
            if not all(
                [
                    os.getenv("REDDIT_CLIENT_ID"),
                    os.getenv("REDDIT_CLIENT_SECRET"),
                    os.getenv("REDDIT_USERNAME"),
                    os.getenv("REDDIT_PASSWORD"),
                ]
            ):
                log_operation(
                    logger,
                    "init",
                    "warning",
                    {
                        "message": "Reddit API credentials are missing. Some functionality may be limited."
                    },
                )

            log_operation(logger, "init", "success", {"mode": self.mode})

        except Exception as e:
            log_operation(
                logger,
                "init",
                "failure",
                {"mode": os.getenv("REDDIT_MODE", "dryrun")},
                error=e,
            )
            raise

    def get_subreddit(self, subreddit_name: str) -> praw.models.Subreddit:
        """Get a subreddit instance."""
        try:
            log_operation(
                logger, "get_subreddit", "started", {"subreddit": subreddit_name}
            )

            subreddit = self.reddit.subreddit(subreddit_name)

            log_operation(
                logger, "get_subreddit", "success", {"subreddit": subreddit_name}
            )

            return subreddit

        except Exception as e:
            log_operation(
                logger,
                "get_subreddit",
                "failure",
                {"subreddit": subreddit_name},
                error=e,
            )
            raise

    def get_post(self, post_id: str) -> praw.models.Submission:
        """Get a post by ID."""
        try:
            log_operation(logger, "get_post", "started", {"post_id": post_id})

            post = self.reddit.submission(post_id)

            log_operation(logger, "get_post", "success", {"post_id": post_id})

            return post

        except Exception as e:
            log_operation(logger, "get_post", "failure", {"post_id": post_id}, error=e)
            raise

    def get_comment(self, comment_id: str) -> praw.models.Comment:
        """Get a comment by ID."""
        return self.reddit.comment(comment_id)

    def upvote_post(self, post_id: str) -> dict:
        post = self.get_post(post_id)
        if self.mode == "dryrun":
            log_operation(
                logger,
                "upvote_post",
                "dryrun",
                {
                    "post_id": post_id,
                    "post_title": post.title,
                    "subreddit": post.subreddit.display_name,
                    "mode": self.mode,
                },
            )
            return {
                "type": "post_vote",
                "action": "would upvote",
                "post_id": post_id,
                "post_title": post.title,
                "subreddit": post.subreddit.display_name,
            }
        post.upvote()
        log_operation(
            logger,
            "upvote_post",
            "success",
            {
                "post_id": post_id,
                "post_title": post.title,
                "subreddit": post.subreddit.display_name,
                "mode": self.mode,
            },
        )
        return {
            "type": "post_vote",
            "action": "upvoted",
            "post_id": post_id,
            "post_title": post.title,
            "subreddit": post.subreddit.display_name,
        }

    def downvote_post(self, post_id: str) -> dict:
        post = self.get_post(post_id)
        if self.mode == "dryrun":
            log_operation(
                logger,
                "downvote_post",
                "dryrun",
                {
                    "post_id": post_id,
                    "post_title": post.title,
                    "subreddit": post.subreddit.display_name,
                    "mode": self.mode,
                },
            )
            return {
                "type": "post_vote",
                "action": "would downvote",
                "post_id": post_id,
                "post_title": post.title,
                "subreddit": post.subreddit.display_name,
            }
        post.downvote()
        log_operation(
            logger,
            "downvote_post",
            "success",
            {
                "post_id": post_id,
                "post_title": post.title,
                "subreddit": post.subreddit.display_name,
                "mode": self.mode,
            },
        )
        return {
            "type": "post_vote",
            "action": "downvoted",
            "post_id": post_id,
            "post_title": post.title,
            "subreddit": post.subreddit.display_name,
        }

    def upvote_comment(self, comment_id: str) -> dict:
        comment = self.get_comment(comment_id)
        if self.mode == "dryrun":
            log_operation(
                logger,
                "upvote_comment",
                "dryrun",
                {
                    "comment_id": comment_id,
                    "post_id": comment.submission.id,
                    "post_title": comment.submission.title,
                    "subreddit": comment.subreddit.display_name,
                    "mode": self.mode,
                },
            )
            return {
                "type": "comment_vote",
                "action": "would upvote",
                "comment_id": comment_id,
                "post_id": comment.submission.id,
                "post_title": comment.submission.title,
                "subreddit": comment.subreddit.display_name,
            }
        comment.upvote()
        log_operation(
            logger,
            "upvote_comment",
            "success",
            {
                "comment_id": comment_id,
                "post_id": comment.submission.id,
                "post_title": comment.submission.title,
                "subreddit": comment.subreddit.display_name,
                "mode": self.mode,
            },
        )
        return {
            "type": "comment_vote",
            "action": "upvoted",
            "comment_id": comment_id,
            "post_id": comment.submission.id,
            "post_title": comment.submission.title,
            "subreddit": comment.subreddit.display_name,
        }

    def downvote_comment(self, comment_id: str) -> dict:
        comment = self.get_comment(comment_id)
        if self.mode == "dryrun":
            log_operation(
                logger,
                "downvote_comment",
                "dryrun",
                {
                    "comment_id": comment_id,
                    "post_id": comment.submission.id,
                    "post_title": comment.submission.title,
                    "subreddit": comment.subreddit.display_name,
                    "mode": self.mode,
                },
            )
            return {
                "type": "comment_vote",
                "action": "would downvote",
                "comment_id": comment_id,
                "post_id": comment.submission.id,
                "post_title": comment.submission.title,
                "subreddit": comment.subreddit.display_name,
            }
        comment.downvote()
        log_operation(
            logger,
            "downvote_comment",
            "success",
            {
                "comment_id": comment_id,
                "post_id": comment.submission.id,
                "post_title": comment.submission.title,
                "subreddit": comment.subreddit.display_name,
                "mode": self.mode,
            },
        )
        return {
            "type": "comment_vote",
            "action": "downvoted",
            "comment_id": comment_id,
            "post_id": comment.submission.id,
            "post_title": comment.submission.title,
            "subreddit": comment.subreddit.display_name,
        }

    def comment_on_post(self, post_id: str, comment_text: str) -> dict:
        log_operation(
            logger,
            "comment_on_post",
            "started",
            {
                "post_id": post_id,
                "comment_length": len(comment_text),
                "mode": self.mode,
            },
        )
        post = self.get_post(post_id)
        if self.mode == "dryrun":
            log_operation(
                logger,
                "comment_on_post",
                "dryrun",
                {
                    "type": "post_comment",
                    "action": "would comment on post",
                    "post_id": post_id,
                    "post_title": post.title,
                    "post_link": post.url,
                    "comment_text": comment_text,
                    "subreddit": post.subreddit.display_name,
                    "mode": self.mode,
                },
            )
            return {
                "type": "post_comment",
                "action": "would comment on post",
                "post_id": post_id,
                "post_title": post.title,
                "post_link": post.url,
                "comment_text": comment_text,
                "subreddit": post.subreddit.display_name,
            }
        new_comment = post.reply(comment_text)
        log_operation(
            logger,
            "comment_on_post",
            "success",
            {
                "type": "post_comment",
                "action": "commented on post",
                "post_id": post_id,
                "post_title": post.title,
                "post_link": post.url,
                "comment_text": comment_text,
                "subreddit": post.subreddit.display_name,
                "comment_id": new_comment.id,
                "mode": self.mode,
            },
        )
        return {
            "type": "post_comment",
            "action": "commented on post",
            "post_id": post_id,
            "post_title": post.title,
            "post_link": post.url,
            "comment_text": comment_text,
            "subreddit": post.subreddit.display_name,
            "comment_id": new_comment.id,
        }

    def reply_to_comment(self, comment_id: str, reply_text: str) -> dict:
        comment = self.get_comment(comment_id)
        if self.mode == "dryrun":
            log_operation(
                logger,
                "reply_to_comment",
                "dryrun",
                {
                    "action": "would reply to comment",
                    "comment_id": comment_id,
                    "reply_text": reply_text,
                    "post_id": comment.submission.id,
                    "post_title": comment.submission.title,
                    "post_link": f"https://reddit.com/r/{comment.subreddit.display_name}/comments/{comment.submission.id}/_/{comment_id}",
                    "subreddit": comment.subreddit.display_name,
                    "mode": self.mode,
                },
            )
            return {
                "action": "would reply to comment",
                "comment_id": comment_id,
                "reply_text": reply_text,
                "post_id": comment.submission.id,
                "post_title": comment.submission.title,
                "post_link": f"https://reddit.com/r/{comment.subreddit.display_name}/comments/{comment.submission.id}/_/{comment_id}",
                "subreddit": comment.subreddit.display_name,
            }
        new_reply = comment.reply(reply_text)
        log_operation(
            logger,
            "reply_to_comment",
            "success",
            {
                "action": "replied to comment",
                "comment_id": comment_id,
                "reply_text": reply_text,
                "post_id": comment.submission.id,
                "post_title": comment.submission.title,
                "post_link": f"https://reddit.com/r/{comment.subreddit.display_name}/comments/{comment.submission.id}/_/{comment_id}",
                "subreddit": comment.subreddit.display_name,
                "reply_id": new_reply.id,
                "mode": self.mode,
            },
        )
        return {
            "action": "replied to comment",
            "comment_id": comment_id,
            "reply_text": reply_text,
            "post_id": comment.submission.id,
            "post_title": comment.submission.title,
            "post_link": f"https://reddit.com/r/{comment.subreddit.display_name}/comments/{comment.submission.id}/_/{comment_id}",
            "subreddit": comment.subreddit.display_name,
            "reply_id": new_reply.id,
        }

    def post_content(self, subreddit_name: str, title: str, content: str) -> dict:
        log_operation(
            logger,
            "post_content",
            "started",
            {
                "subreddit": subreddit_name,
                "title_length": len(title),
                "content_length": len(content),
                "mode": self.mode,
            },
        )
        subreddit = self.get_subreddit(subreddit_name)
        if self.mode == "dryrun":
            log_operation(
                logger,
                "post_content",
                "dryrun",
                {
                    "type": "post_content",
                    "action": "would post content",
                    "subreddit": subreddit_name,
                    "title": title,
                    "content": content,
                    "mode": self.mode,
                },
            )
            return {
                "type": "post_content",
                "action": "would post content",
                "subreddit": subreddit_name,
                "title": title,
                "content": content,
            }
        new_post = subreddit.submit(title=title, selftext=content)
        log_operation(
            logger,
            "post_content",
            "success",
            {
                "type": "post_content",
                "action": "posted content",
                "subreddit": subreddit_name,
                "title": title,
                "content": content,
                "post_id": new_post.id,
                "post_url": new_post.url,
                "mode": self.mode,
            },
        )
        return {
            "type": "post_content",
            "action": "posted content",
            "subreddit": subreddit_name,
            "title": title,
            "content": content,
            "post_id": new_post.id,
            "post_url": new_post.url,
        }

    def get_post_context(self, post_id: str) -> Dict[str, Any]:
        """Get detailed context for a given post ID, including top comments."""
        try:
            log_operation(
                logger,
                "get_post_context",
                "started",
                {"post_id": post_id, "mode": self.mode},
            )
            post = self.get_post(post_id)
            top_comments_data = []
            if self.mode == "dryrun":
                # Simulate top comments for dry run
                top_comments_data = [
                    {
                        "id": "dryrun_comment_id",
                        "body": "This is a simulated comment in dry run mode.",
                        "score": 10,
                        "author": "dryrun_user",
                        "created_utc": datetime.now(timezone.utc).timestamp(),
                    }
                ]
            else:
                # Fetch real top comments in live mode
                post.comments.replace_more(limit=0)  # Flatten MoreComments objects
                for comment in post.comments.list()[:5]:  # Get top 5 comments
                    top_comments_data.append(
                        {
                            "id": comment.id,
                            "body": comment.body,
                            "score": comment.score,
                            "author": str(comment.author),
                            "created_utc": comment.created_utc,
                        }
                    )

            post_context = {
                "post_id": post.id,
                "title": post.title,
                "content": post.selftext,
                "score": post.score,
                "num_comments": post.num_comments,
                "created_utc": post.created_utc,
                "subreddit": post.subreddit.display_name,
                "permalink": post.permalink,
                "url": post.url,
                "author": str(post.author) if post.author else None,
                "top_comments": top_comments_data,
            }
            log_operation(
                logger,
                "get_post_context",
                "success",
                {
                    "post_id": post_id,
                    "title": post.title,
                    "subreddit": post.subreddit.display_name,
                    "mode": self.mode,
                },
            )
            return post_context
        except Exception as e:
            log_operation(
                logger,
                "get_post_context",
                "failure",
                {"post_id": post_id, "mode": self.mode},
                error=e,
            )
            raise

    def get_comment_context(self, comment_id: str) -> Dict[str, Any]:
        """Get detailed context for a given comment ID."""
        try:
            log_operation(
                logger,
                "get_comment_context",
                "started",
                {"comment_id": comment_id, "mode": self.mode},
            )
            comment = self.get_comment(comment_id)
            comment_context = {
                "comment_id": comment.id,
                "body": comment.body,
                "score": comment.score,
                "author": str(comment.author),
                "created_utc": comment.created_utc,
                "post_id": comment.submission.id,
                "post_title": comment.submission.title,
                "subreddit": comment.subreddit.display_name,
            }
            log_operation(
                logger,
                "get_comment_context",
                "success",
                {
                    "comment_id": comment_id,
                    "post_id": comment.submission.id,
                    "mode": self.mode,
                },
            )
            return comment_context
        except Exception as e:
            log_operation(
                logger,
                "get_comment_context",
                "failure",
                {"comment_id": comment_id, "mode": self.mode},
                error=e,
            )
            raise

    def get_trending_posts(
        self, subreddit_name: str, limit: int = 1
    ) -> List[Dict[str, Any]]:
        """Get a list of trending posts from a specified subreddit."""
        try:
            log_operation(
                logger,
                "get_trending_posts",
                "started",
                {"subreddit": subreddit_name, "limit": limit, "mode": self.mode},
            )
            subreddit = self.get_subreddit(subreddit_name)
            trending_posts_data = []
            if self.mode == "dryrun":
                # Simulate trending posts for dry run
                for i in range(limit):
                    trending_posts_data.append(
                        {
                            "id": f"dryrun_post_{i}",
                            "title": f"Simulated Trending Post {i}",
                            "url": f"http://dryrun.reddit.com/r/{subreddit_name}/comments/dryrun_post_{i}",
                            "score": 100 + i,
                            "num_comments": 20 + i,
                            "created_utc": datetime.now(timezone.utc).timestamp()
                            - i * 3600,
                        }
                    )
            else:
                for submission in subreddit.hot(limit=limit):
                    trending_posts_data.append(
                        {
                            "id": submission.id,
                            "title": submission.title,
                            "url": submission.url,
                            "score": submission.score,
                            "num_comments": submission.num_comments,
                            "created_utc": submission.created_utc,
                        }
                    )
            log_operation(
                logger,
                "get_trending_posts",
                "success",
                {
                    "subreddit": subreddit_name,
                    "num_posts": len(trending_posts_data),
                    "mode": self.mode,
                },
            )
            return trending_posts_data
        except Exception as e:
            log_operation(
                logger,
                "get_trending_posts",
                "failure",
                {"subreddit": subreddit_name, "mode": self.mode},
                error=e,
            )
            raise

    def post_product(self, product_id: str, product_name: str, content: str) -> dict:
        """Posts a product to a hardcoded subreddit in dry run mode."""
        subreddit_name = "test_subreddit"  # Hardcoded for dry run testing
        if self.mode == "dryrun":
            log_operation(
                logger,
                "post_product",
                "dryrun",
                {
                    "product_id": product_id,
                    "product_name": product_name,
                    "subreddit": subreddit_name,
                    "action": "would post content",
                    "mode": self.mode,
                },
            )
            return {
                "type": "product_post",
                "action": "would post content",
                "product_id": product_id,
                "product_name": product_name,
                "subreddit": subreddit_name,
                "title": product_name,
                "content": content,
            }

        # In live mode, you would implement the actual posting logic here
        # For now, it's assumed to be part of dry run for testing purposes
        raise NotImplementedError(
            "Product posting is only implemented for dry run mode in this example."
        )
