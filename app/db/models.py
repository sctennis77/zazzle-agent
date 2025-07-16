import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import backref, declarative_base, relationship

from app.models import (
    DonationTier,
    InteractionActionStatus,
    InteractionActionType,
    InteractionTargetType,
)

Base = declarative_base()


class Subreddit(Base):
    """Core subreddit entity - single source of truth for subreddit metadata"""

    __tablename__ = "subreddits"
    id = Column(Integer, primary_key=True)
    subreddit_name = Column(
        String(100), nullable=False, unique=True, index=True
    )  # e.g., "golf", "all"
    reddit_id = Column(String(32), nullable=True, index=True)  # Reddit's internal ID
    reddit_fullname = Column(
        String(32), nullable=True, index=True
    )  # Reddit's fullname (t5_...)
    display_name = Column(
        String(100), nullable=True
    )  # Display name (usually same as subreddit_name)
    description = Column(Text, nullable=True)  # Subreddit description in Markdown
    description_html = Column(Text, nullable=True)  # Subreddit description in HTML
    public_description = Column(
        Text, nullable=True
    )  # Public description shown in searches
    created_utc = Column(
        DateTime, nullable=True, index=True
    )  # When subreddit was created
    subscribers = Column(Integer, nullable=True, index=True)  # Number of subscribers
    over18 = Column(Boolean, default=False, nullable=False)  # Whether NSFW
    spoilers_enabled = Column(
        Boolean, default=False, nullable=False
    )  # Whether spoilers enabled
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Relationships
    donations = relationship("Donation", back_populates="subreddit")
    fundraising_goals = relationship(
        "SubredditFundraisingGoal", back_populates="subreddit"
    )
    pipeline_tasks = relationship("PipelineTask", back_populates="subreddit")
    reddit_posts = relationship("RedditPost", back_populates="subreddit")
    interaction_actions = relationship(
        "InteractionAgentAction", back_populates="subreddit"
    )


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    id = Column(Integer, primary_key=True)
    start_time = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    end_time = Column(DateTime, nullable=True, index=True)
    status = Column(
        String(32), default="pending", index=True
    )  # pending, running, success, failed, cancelled
    summary = Column(Text, nullable=True)
    config = Column(JSON, nullable=True)  # Store pipeline configuration
    metrics = Column(JSON, nullable=True)  # Store runtime metrics
    duration = Column(Integer, nullable=True)  # Duration in seconds
    retry_count = Column(Integer, default=0)  # Number of retry attempts
    last_error = Column(Text, nullable=True)  # Last error message if failed
    version = Column(String(32), nullable=True)  # Pipeline version

    reddit_posts = relationship(
        "RedditPost", back_populates="pipeline_run", cascade="all, delete-orphan"
    )
    products = relationship(
        "ProductInfo", back_populates="pipeline_run", cascade="all, delete-orphan"
    )
    errors = relationship(
        "ErrorLog", back_populates="pipeline_run", cascade="all, delete-orphan"
    )


class PipelineRunUsage(Base):
    __tablename__ = "pipeline_run_usages"
    id = Column(Integer, primary_key=True)
    pipeline_run_id = Column(
        Integer,
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    idea_model = Column(String(64), nullable=False)
    image_model = Column(String(64), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    image_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Numeric(10, 4), nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )

    pipeline_run = relationship("PipelineRun", backref="usage", uselist=False)


class SourceType(enum.Enum):
    STRIPE = "stripe"
    MANUAL = "manual"


class Donation(Base):
    __tablename__ = "donations"
    id = Column(Integer, primary_key=True)
    stripe_payment_intent_id = Column(
        String(255), unique=True, nullable=False, index=True
    )
    amount_cents = Column(Integer, nullable=False)  # Amount in cents
    amount_usd = Column(Numeric(10, 2), nullable=False)  # Amount in USD
    currency = Column(String(3), default="usd", nullable=False)
    status = Column(
        String(32), default="pending", nullable=False, index=True
    )  # pending, succeeded, failed, canceled
    tier = Column(
        String(32), nullable=False, index=True
    )  # bronze, silver, gold, platinum, emerald, topaz, ruby, sapphire
    customer_email = Column(String(255), nullable=True, index=True)
    customer_name = Column(String(255), nullable=True)
    message = Column(Text, nullable=True)  # Optional message from donor
    subreddit_id = Column(
        Integer, ForeignKey("subreddits.id"), nullable=True, index=True
    )  # Subreddit associated with the donation
    reddit_username = Column(
        String(100), nullable=True, index=True
    )  # Reddit username of the donor
    stripe_metadata = Column(JSON, nullable=True)  # Additional Stripe metadata
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True,
    )
    is_anonymous = Column(Boolean, default=False, nullable=False)
    subreddit_fundraising_goal_id = Column(
        Integer, ForeignKey("subreddit_fundraising_goals.id"), nullable=True, index=True
    )  # Associated fundraising goal
    donation_type = Column(
        String(32), default="support", nullable=False, index=True
    )  # "commission" or "support"
    commission_type = Column(
        String(32), nullable=True, index=True
    )  # "specific_post" or "random_subreddit"
    post_id = Column(
        String(32), nullable=True, index=True
    )  # Reddit post ID for commissioning specific posts
    commission_message = Column(
        Text, nullable=True
    )  # Optional message to display with commission badge
    source = Column(
        Enum(SourceType, name="source_type"), nullable=True
    )  # 'stripe' or 'manual' or null
    stripe_refund_id = Column(
        String(255), nullable=True, index=True
    )  # Stripe refund ID if refunded

    # Relationships
    subreddit = relationship("Subreddit", back_populates="donations")
    subreddit_fundraising_goal = relationship(
        "SubredditFundraisingGoal", back_populates="donations"
    )


class SubredditFundraisingGoal(Base):
    """Community fundraising goals for subreddits"""

    __tablename__ = "subreddit_fundraising_goals"
    id = Column(Integer, primary_key=True)
    subreddit_id = Column(
        Integer, ForeignKey("subreddits.id"), nullable=False, index=True
    )
    goal_amount = Column(
        Numeric(10, 2), nullable=False, index=True
    )  # Total goal amount
    current_amount = Column(
        Numeric(10, 2), default=0, nullable=False, index=True
    )  # Current progress
    deadline = Column(DateTime, nullable=True, index=True)  # Optional deadline
    status = Column(
        String(32), default="active", nullable=False, index=True
    )  # active, completed, expired
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    completed_at = Column(DateTime, nullable=True, index=True)

    subreddit = relationship("Subreddit", back_populates="fundraising_goals")
    donations = relationship("Donation", back_populates="subreddit_fundraising_goal")


class PipelineTask(Base):
    """Task queue for pipeline execution"""

    __tablename__ = "pipeline_tasks"
    id = Column(Integer, primary_key=True)
    type = Column(String(32), nullable=False, index=True)  # SUBREDDIT_POST
    subreddit_id = Column(
        Integer, ForeignKey("subreddits.id"), nullable=False, index=True
    )  # Target subreddit
    donation_id = Column(
        Integer, ForeignKey("donations.id"), nullable=True, index=True
    )  # Associated donation
    status = Column(
        String(32), default="pending", nullable=False, index=True
    )  # pending, in_progress, completed, failed
    priority = Column(
        Integer, default=0, nullable=False, index=True
    )  # Higher number = higher priority
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    scheduled_for = Column(DateTime, nullable=True, index=True)  # When to execute
    completed_at = Column(DateTime, nullable=True, index=True)  # When completed
    error_message = Column(Text, nullable=True)  # Error message if failed
    context_data = Column(JSON, nullable=True)  # Additional context data
    pipeline_run_id = Column(
        Integer, ForeignKey("pipeline_runs.id"), nullable=True, index=True
    )  # Associated pipeline run
    started_at = Column(
        DateTime, nullable=True, index=True
    )  # When task started processing
    last_heartbeat = Column(
        DateTime, nullable=True, index=True
    )  # Last heartbeat timestamp
    retry_count = Column(Integer, default=0, nullable=False)  # Number of retry attempts
    max_retries = Column(Integer, default=2, nullable=False)  # Maximum retry attempts
    timeout_seconds = Column(
        Integer, default=300, nullable=False
    )  # Task timeout in seconds (5 minutes)

    subreddit = relationship("Subreddit", back_populates="pipeline_tasks")
    donation = relationship("Donation", backref="tasks")
    pipeline_run = relationship("PipelineRun", backref="tasks")


class RedditPost(Base):
    __tablename__ = "reddit_posts"
    id = Column(Integer, primary_key=True)
    pipeline_run_id = Column(
        Integer,
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    post_id = Column(String(32), unique=True, index=True)
    title = Column(Text)
    content = Column(Text)
    subreddit_id = Column(
        Integer, ForeignKey("subreddits.id"), nullable=True, index=True
    )
    url = Column(Text)
    permalink = Column(Text)
    comment_summary = Column(Text, nullable=True)
    author = Column(String(64), nullable=True, index=True)  # Reddit post author
    score = Column(
        Integer, nullable=True, index=True
    )  # Reddit post score (upvotes - downvotes)
    num_comments = Column(
        Integer, nullable=True, index=True
    )  # Number of comments on the post

    pipeline_run = relationship("PipelineRun", back_populates="reddit_posts")
    subreddit = relationship("Subreddit", back_populates="reddit_posts")
    products = relationship(
        "ProductInfo", back_populates="reddit_post", cascade="all, delete-orphan"
    )
    interaction_actions = relationship(
        "InteractionAgentAction",
        back_populates="reddit_post",
        cascade="all, delete-orphan",
    )


class ProductInfo(Base):
    __tablename__ = "product_infos"
    id = Column(Integer, primary_key=True)
    pipeline_run_id = Column(
        Integer,
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reddit_post_id = Column(
        Integer, ForeignKey("reddit_posts.id", ondelete="CASCADE"), index=True
    )
    theme = Column(String(256), index=True)
    image_title = Column(String(256), nullable=True, index=True)
    image_url = Column(Text, nullable=True)  # URL to the product image
    product_url = Column(Text)
    affiliate_link = Column(Text)
    template_id = Column(String(64), index=True)
    model = Column(String(64), index=True)
    prompt_version = Column(String(32))
    product_type = Column(String(64), index=True)
    design_description = Column(Text)
    image_quality = Column(
        String(16), default="standard", index=True
    )  # Image quality: standard, hd

    pipeline_run = relationship("PipelineRun", back_populates="products")
    reddit_post = relationship("RedditPost", back_populates="products")
    interaction_actions = relationship(
        "InteractionAgentAction",
        back_populates="product_info",
        cascade="all, delete-orphan",
    )
    subreddit_post = relationship(
        "ProductSubredditPost", back_populates="product_info", uselist=False
    )


class ErrorLog(Base):
    __tablename__ = "error_logs"
    id = Column(Integer, primary_key=True)
    pipeline_run_id = Column(
        Integer,
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    error_message = Column(Text)
    error_type = Column(
        String(64), index=True
    )  # Type of error (e.g., 'API_ERROR', 'VALIDATION_ERROR', 'SYSTEM_ERROR')
    component = Column(
        String(64), index=True
    )  # Component where error occurred (e.g., 'REDDIT_AGENT', 'IMAGE_GENERATOR')
    stack_trace = Column(Text, nullable=True)  # Full stack trace if available
    context_data = Column(JSON, nullable=True)  # Additional context data as JSON
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    severity = Column(String(16), default="ERROR", index=True)  # ERROR, WARNING, INFO

    pipeline_run = relationship("PipelineRun", back_populates="errors")


class InteractionAgentAction(Base):
    __tablename__ = "interaction_agent_actions"
    id = Column(Integer, primary_key=True)
    product_info_id = Column(
        Integer,
        ForeignKey("product_infos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reddit_post_id = Column(
        Integer,
        ForeignKey("reddit_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type = Column(String(32), index=True)  # upvote, downvote, reply
    target_type = Column(String(32), index=True)  # post, comment
    target_id = Column(String(32), index=True)  # Reddit post/comment ID
    content = Column(Text, nullable=True)  # For replies
    subreddit_id = Column(
        Integer, ForeignKey("subreddits.id"), nullable=True, index=True
    )
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    success = Column(
        String(8), default=InteractionActionStatus.PENDING.value, index=True
    )  # pending, success, failed
    error_message = Column(Text, nullable=True)
    context_data = Column(JSON, nullable=True)  # Additional context data

    product_info = relationship("ProductInfo", back_populates="interaction_actions")
    reddit_post = relationship("RedditPost", back_populates="interaction_actions")
    subreddit = relationship("Subreddit", back_populates="interaction_actions")

    @property
    def action_type_enum(self) -> InteractionActionType:
        return InteractionActionType(self.action_type)

    @action_type_enum.setter
    def action_type_enum(self, value: InteractionActionType):
        self.action_type = value.value

    @property
    def target_type_enum(self) -> InteractionTargetType:
        return InteractionTargetType(self.target_type)

    @target_type_enum.setter
    def target_type_enum(self, value: InteractionTargetType):
        self.target_type = value.value

    @property
    def success_enum(self) -> InteractionActionStatus:
        return InteractionActionStatus(self.success)

    @success_enum.setter
    def success_enum(self, value: InteractionActionStatus):
        self.success = value.value


class ProductSubredditPost(Base):
    """Tracks products that have been published to subreddits."""

    __tablename__ = "product_subreddit_posts"
    id = Column(Integer, primary_key=True)
    product_info_id = Column(
        Integer,
        ForeignKey("product_infos.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One-to-one relationship
        index=True,
    )
    subreddit_name = Column(String(100), nullable=False, index=True)  # e.g., "clouvel"
    reddit_post_id = Column(String(32), nullable=False, index=True)  # Reddit's post ID
    reddit_post_url = Column(Text, nullable=True)  # Full URL to the Reddit post
    reddit_post_title = Column(Text, nullable=True)  # Title of the Reddit post
    submitted_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    dry_run = Column(
        Boolean, default=True, nullable=False
    )  # Whether this was a dry run
    status = Column(
        String(32), default="published", nullable=False, index=True
    )  # published, failed, deleted
    error_message = Column(Text, nullable=True)  # Error message if submission failed
    engagement_data = Column(
        JSON, nullable=True
    )  # Store engagement metrics (upvotes, comments, etc.)

    # Relationships
    product_info = relationship(
        "ProductInfo", back_populates="subreddit_post", uselist=False
    )


class SchedulerConfig(Base):
    """Configuration table for the scheduled commission system."""

    __tablename__ = "scheduler_config"
    id = Column(Integer, primary_key=True)
    enabled = Column(Boolean, default=False, nullable=False, index=True)
    interval_hours = Column(Integer, default=24, nullable=False)  # Hours between runs
    last_run_at = Column(DateTime, nullable=True, index=True)
    next_run_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True,
    )


class CommunityAgentAction(Base):
    """Actions taken by the Clouvel community agent"""

    __tablename__ = "community_agent_actions"
    id = Column(Integer, primary_key=True)
    action_type = Column(
        String(32), nullable=False, index=True
    )  # moderation, engagement, recognition
    target_type = Column(String(32), nullable=True, index=True)  # post, comment, user
    target_id = Column(String(64), nullable=True, index=True)
    content = Column(Text, nullable=True)  # Generated responses
    decision_reasoning = Column(Text, nullable=True)  # LLM reasoning
    clouvel_mood = Column(
        String(32), nullable=True
    )  # happy, excited, thoughtful, creative
    royal_decree_type = Column(
        String(32), nullable=True
    )  # welcome, celebration, recognition
    success_status = Column(String(16), default="pending", nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    subreddit_id = Column(
        Integer, ForeignKey("subreddits.id"), nullable=True, index=True
    )
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    dry_run = Column(
        Boolean, default=True, nullable=False
    )  # Whether this was a dry run

    # Relationships
    subreddit = relationship("Subreddit", backref="community_agent_actions")


class CommunityAgentState(Base):
    """State tracking for the community agent"""

    __tablename__ = "community_agent_state"
    id = Column(Integer, primary_key=True)
    subreddit_name = Column(String(100), nullable=False, unique=True, index=True)
    last_scan_time = Column(DateTime, nullable=True, index=True)
    daily_action_count = Column(JSON, nullable=True)  # Track rate limits by date
    community_knowledge = Column(JSON, nullable=True)  # Remember users, patterns
    welcomed_users = Column(
        JSON, nullable=True
    )  # Track welcomed users to avoid duplicates
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True,
    )
