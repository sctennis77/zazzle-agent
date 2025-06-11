from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class PipelineRun(Base):
    __tablename__ = 'pipeline_runs'
    id = Column(Integer, primary_key=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(32), default='pending')
    summary = Column(Text, nullable=True)

    reddit_posts = relationship('RedditPost', back_populates='pipeline_run', cascade='all, delete-orphan')
    products = relationship('ProductInfo', back_populates='pipeline_run', cascade='all, delete-orphan')
    errors = relationship('ErrorLog', back_populates='pipeline_run', cascade='all, delete-orphan')

class RedditPost(Base):
    __tablename__ = 'reddit_posts'
    id = Column(Integer, primary_key=True)
    pipeline_run_id = Column(Integer, ForeignKey('pipeline_runs.id', ondelete='CASCADE'), nullable=False)
    post_id = Column(String(32), unique=True)
    title = Column(Text)
    content = Column(Text)
    subreddit = Column(String(64))
    url = Column(Text)

    pipeline_run = relationship('PipelineRun', back_populates='reddit_posts')
    comments = relationship('CommentSummary', back_populates='reddit_post', cascade='all, delete-orphan')
    products = relationship('ProductInfo', back_populates='reddit_post', cascade='all, delete-orphan')

class CommentSummary(Base):
    __tablename__ = 'comment_summaries'
    id = Column(Integer, primary_key=True)
    reddit_post_id = Column(Integer, ForeignKey('reddit_posts.id', ondelete='CASCADE'))
    summary = Column(Text)

    reddit_post = relationship('RedditPost', back_populates='comments')

class ProductInfo(Base):
    __tablename__ = 'product_infos'
    id = Column(Integer, primary_key=True)
    pipeline_run_id = Column(Integer, ForeignKey('pipeline_runs.id', ondelete='CASCADE'), nullable=False)
    reddit_post_id = Column(Integer, ForeignKey('reddit_posts.id', ondelete='CASCADE'))
    theme = Column(String(256))
    image_url = Column(Text)
    product_url = Column(Text)
    affiliate_link = Column(Text)
    template_id = Column(String(64))
    model = Column(String(64))
    prompt_version = Column(String(32))
    product_type = Column(String(64))
    design_description = Column(Text)

    pipeline_run = relationship('PipelineRun', back_populates='products')
    reddit_post = relationship('RedditPost', back_populates='products')

class ErrorLog(Base):
    __tablename__ = 'error_logs'
    id = Column(Integer, primary_key=True)
    pipeline_run_id = Column(Integer, ForeignKey('pipeline_runs.id', ondelete='CASCADE'), nullable=False)
    error_message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    pipeline_run = relationship('PipelineRun', back_populates='errors') 