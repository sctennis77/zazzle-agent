from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class PipelineRun(Base):
    __tablename__ = 'pipeline_runs'
    id = Column(Integer, primary_key=True)
    start_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    end_time = Column(DateTime, nullable=True, index=True)
    status = Column(String(32), default='pending', index=True)  # pending, running, success, failed, cancelled
    summary = Column(Text, nullable=True)
    config = Column(JSON, nullable=True)  # Store pipeline configuration
    metrics = Column(JSON, nullable=True)  # Store runtime metrics
    duration = Column(Integer, nullable=True)  # Duration in seconds
    retry_count = Column(Integer, default=0)  # Number of retry attempts
    last_error = Column(Text, nullable=True)  # Last error message if failed
    version = Column(String(32), nullable=True)  # Pipeline version

    reddit_posts = relationship('RedditPost', back_populates='pipeline_run', cascade='all, delete-orphan')
    products = relationship('ProductInfo', back_populates='pipeline_run', cascade='all, delete-orphan')
    errors = relationship('ErrorLog', back_populates='pipeline_run', cascade='all, delete-orphan')

class RedditPost(Base):
    __tablename__ = 'reddit_posts'
    id = Column(Integer, primary_key=True)
    pipeline_run_id = Column(Integer, ForeignKey('pipeline_runs.id', ondelete='CASCADE'), nullable=False, index=True)
    post_id = Column(String(32), unique=True, index=True)
    title = Column(Text)
    content = Column(Text)
    subreddit = Column(String(64), index=True)
    url = Column(Text)
    permalink = Column(Text)
    comment_summary = Column(Text, nullable=True)

    pipeline_run = relationship('PipelineRun', back_populates='reddit_posts')
    products = relationship('ProductInfo', back_populates='reddit_post', cascade='all, delete-orphan')

class ProductInfo(Base):
    __tablename__ = 'product_infos'
    id = Column(Integer, primary_key=True)
    pipeline_run_id = Column(Integer, ForeignKey('pipeline_runs.id', ondelete='CASCADE'), nullable=False, index=True)
    reddit_post_id = Column(Integer, ForeignKey('reddit_posts.id', ondelete='CASCADE'), index=True)
    theme = Column(String(256), index=True)
    image_url = Column(Text)
    product_url = Column(Text)
    affiliate_link = Column(Text)
    template_id = Column(String(64), index=True)
    model = Column(String(64), index=True)
    prompt_version = Column(String(32))
    product_type = Column(String(64), index=True)
    design_description = Column(Text)

    pipeline_run = relationship('PipelineRun', back_populates='products')
    reddit_post = relationship('RedditPost', back_populates='products')

class ErrorLog(Base):
    __tablename__ = 'error_logs'
    id = Column(Integer, primary_key=True)
    pipeline_run_id = Column(Integer, ForeignKey('pipeline_runs.id', ondelete='CASCADE'), nullable=False, index=True)
    error_message = Column(Text)
    error_type = Column(String(64), index=True)  # Type of error (e.g., 'API_ERROR', 'VALIDATION_ERROR', 'SYSTEM_ERROR')
    component = Column(String(64), index=True)    # Component where error occurred (e.g., 'REDDIT_AGENT', 'IMAGE_GENERATOR')
    stack_trace = Column(Text, nullable=True)  # Full stack trace if available
    context_data = Column(JSON, nullable=True)  # Additional context data as JSON
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    severity = Column(String(16), default='ERROR', index=True)  # ERROR, WARNING, INFO

    pipeline_run = relationship('PipelineRun', back_populates='errors') 