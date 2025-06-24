from app.db.models import ProductInfo as ORMProductInfo
from app.db.models import RedditPost as ORMRedditPost
from app.models import ProductIdea, RedditContext


def product_idea_to_db(
    product_idea: ProductIdea, pipeline_run_id: int, reddit_post_id: int
) -> ORMProductInfo:
    return ORMProductInfo(
        pipeline_run_id=pipeline_run_id,
        reddit_post_id=reddit_post_id,
        theme=product_idea.theme,
        image_url=product_idea.design_instructions.get("image"),
        product_url=None,  # To be filled after product creation
        affiliate_link=None,  # To be filled after affiliate link generation
        template_id=product_idea.design_instructions.get("template_id"),
        model=product_idea.model,
        prompt_version=product_idea.prompt_version,
        product_type=product_idea.design_instructions.get("product_type", "sticker"),
        design_description=product_idea.image_description,
    )


def db_to_product_idea(
    orm_product_info: ORMProductInfo, reddit_context: RedditContext
) -> ProductIdea:
    return ProductIdea(
        theme=orm_product_info.theme,
        image_description=orm_product_info.design_description,
        design_instructions={
            "image": orm_product_info.image_url,
            "template_id": orm_product_info.template_id,
            "product_type": orm_product_info.product_type,
        },
        reddit_context=reddit_context,
        model=orm_product_info.model,
        prompt_version=orm_product_info.prompt_version,
    )


def reddit_context_to_db(
    reddit_context: RedditContext, pipeline_run_id: int
) -> ORMRedditPost:
    return ORMRedditPost(
        pipeline_run_id=pipeline_run_id,
        post_id=reddit_context.post_id,
        title=reddit_context.post_title,
        content=getattr(reddit_context, "post_content", None),
        subreddit=reddit_context.subreddit,
        url=reddit_context.post_url,
        permalink=getattr(reddit_context, "permalink", None),
        author=getattr(reddit_context, "author", None),
        score=getattr(reddit_context, "score", None),
        num_comments=getattr(reddit_context, "num_comments", None),
        comment_summary=(
            reddit_context.comments[0]["text"]
            if reddit_context.comments
            and len(reddit_context.comments) > 0
            and "text" in reddit_context.comments[0]
            else None
        ),
    )


def db_to_reddit_context(orm_reddit_post: ORMRedditPost) -> RedditContext:
    return RedditContext(
        post_id=orm_reddit_post.post_id,
        post_title=orm_reddit_post.title,
        post_url=orm_reddit_post.url,
        subreddit=orm_reddit_post.subreddit,
        post_content=orm_reddit_post.content,
        permalink=orm_reddit_post.permalink,
        author=orm_reddit_post.author,
        score=orm_reddit_post.score,
        num_comments=orm_reddit_post.num_comments,
        comments=[],  # Comments can be loaded separately if needed
    )


def product_info_to_db(product_info, pipeline_run_id, reddit_post_id):
    """
    Convert a ProductInfo object to a ProductInfo ORM model.
    """
    from app.db.models import ProductInfo as ProductInfoModel

    return ProductInfoModel(
        pipeline_run_id=pipeline_run_id,
        reddit_post_id=reddit_post_id,
        theme=getattr(product_info, "theme", None),
        image_url=getattr(product_info, "image_url", None),
        product_url=getattr(product_info, "product_url", None),
        affiliate_link=getattr(product_info, "affiliate_link", None),
        template_id=getattr(product_info, "zazzle_template_id", None),
        model=getattr(product_info, "model", None),
        prompt_version=getattr(product_info, "prompt_version", None),
        product_type=getattr(product_info, "product_type", None),
        design_description=(
            product_info.design_instructions.get("text")
            if hasattr(product_info, "design_instructions")
            and isinstance(product_info.design_instructions, dict)
            else str(getattr(product_info, "design_instructions", ""))
        ),
    )
