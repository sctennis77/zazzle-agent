from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, Numeric
from sqlalchemy.orm import declarative_base, relationship

from app.models import (
    InteractionActionStatus,
    InteractionActionType,
    InteractionTargetType,
)

Base = declarative_base()


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
    pipeline_run_id = Column(Integer, ForeignKey("pipeline_runs.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    idea_model = Column(String(64), nullable=False)
    image_model = Column(String(64), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    image_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Numeric(10, 4), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    pipeline_run = relationship("PipelineRun", backref="usage", uselist=False)


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
    subreddit = Column(String(64), index=True)
    url = Column(Text)
    permalink = Column(Text)
    comment_summary = Column(Text, nullable=True)
    author = Column(String(64), nullable=True, index=True)  # Reddit post author
    score = Column(Integer, nullable=True, index=True)  # Reddit post score (upvotes - downvotes)
    num_comments = Column(Integer, nullable=True, index=True)  # Number of comments on the post

    pipeline_run = relationship("PipelineRun", back_populates="reddit_posts")
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
    image_url = Column(Text)
    product_url = Column(Text)
    affiliate_link = Column(Text)
    template_id = Column(String(64), index=True)
    model = Column(String(64), index=True)
    prompt_version = Column(String(32))
    product_type = Column(String(64), index=True)
    design_description = Column(Text)

    pipeline_run = relationship("PipelineRun", back_populates="products")
    reddit_post = relationship("RedditPost", back_populates="products")
    interaction_actions = relationship(
        "InteractionAgentAction",
        back_populates="product_info",
        cascade="all, delete-orphan",
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
    subreddit = Column(String(64), index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    success = Column(
        String(8), default=InteractionActionStatus.PENDING.value, index=True
    )  # pending, success, failed
    error_message = Column(Text, nullable=True)
    context_data = Column(JSON, nullable=True)  # Additional context data

    product_info = relationship("ProductInfo", back_populates="interaction_actions")
    reddit_post = relationship("RedditPost", back_populates="interaction_actions")

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
