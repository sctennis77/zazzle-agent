import pytest

from app.db.mappers import (
    db_to_product_idea,
    db_to_reddit_context,
    product_idea_to_db,
    reddit_context_to_db,
)
from app.db.models import ProductInfo as ORMProductInfo
from app.db.models import RedditPost as ORMRedditPost
from app.models import ProductIdea, RedditContext


def test_reddit_context_to_db_and_back():
    ctx = RedditContext(
        post_id="abc123",
        post_title="A Reddit Post",
        post_url="https://reddit.com/test",
        subreddit="golf",
        post_content="This is a test post.",
        comments=[{"text": "Nice!"}],
    )
    orm_post = reddit_context_to_db(ctx, pipeline_run_id=1)
    assert orm_post.post_id == ctx.post_id
    assert orm_post.title == ctx.post_title
    assert orm_post.content == ctx.post_content
    assert orm_post.subreddit == ctx.subreddit
    assert orm_post.url == ctx.post_url
    # Now back to RedditContext
    ctx2 = db_to_reddit_context(orm_post)
    assert ctx2.post_id == ctx.post_id
    assert ctx2.post_title == ctx.post_title
    assert ctx2.post_url == ctx.post_url
    assert ctx2.subreddit == ctx.subreddit
    assert ctx2.post_content == ctx.post_content
    # Comments are not round-tripped (documented)


def test_product_idea_to_db_and_back():
    ctx = RedditContext(
        post_id="abc123",
        post_title="A Reddit Post",
        post_url="https://reddit.com/test",
        subreddit="golf",
        post_content="This is a test post.",
        comments=[{"text": "Nice!"}],
    )
    idea = ProductIdea(
        theme="Golf Journey",
        image_description="A golfer on a course.",
        design_instructions={
            "image": "https://imgur.com/test.png",
            "template_id": "tmpl123",
            "product_type": "sticker",
        },
        reddit_context=ctx,
        model="dall-e-3",
        prompt_version="1.0.0",
    )
    orm_product = product_idea_to_db(idea, pipeline_run_id=1, reddit_post_id=2)
    assert orm_product.theme == idea.theme
    assert orm_product.image_url == idea.design_instructions["image"]
    assert orm_product.template_id == idea.design_instructions["template_id"]
    assert orm_product.model == idea.model
    assert orm_product.prompt_version == idea.prompt_version
    assert orm_product.product_type == idea.design_instructions["product_type"]
    assert orm_product.design_description == idea.image_description
    # Now back to ProductIdea
    idea2 = db_to_product_idea(orm_product, ctx)
    assert idea2.theme == idea.theme
    assert idea2.image_description == idea.image_description
    assert idea2.design_instructions["image"] == idea.design_instructions["image"]
    assert (
        idea2.design_instructions["template_id"]
        == idea.design_instructions["template_id"]
    )
    assert (
        idea2.design_instructions["product_type"]
        == idea.design_instructions["product_type"]
    )
    assert idea2.model == idea.model
    assert idea2.prompt_version == idea.prompt_version
    assert idea2.reddit_context == idea.reddit_context
