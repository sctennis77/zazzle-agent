from app.models import ProductIdea, RedditContext
from app.db.models import ProductInfo as ORMProductInfo, RedditPost as ORMRedditPost

def product_idea_to_db(product_idea: ProductIdea, pipeline_run_id: int, reddit_post_id: int) -> ORMProductInfo:
    return ORMProductInfo(
        pipeline_run_id=pipeline_run_id,
        reddit_post_id=reddit_post_id,
        theme=product_idea.theme,
        image_url=product_idea.design_instructions.get('image'),
        product_url=None,  # To be filled after product creation
        affiliate_link=None,  # To be filled after affiliate link generation
        template_id=product_idea.design_instructions.get('template_id'),
        model=product_idea.model,
        prompt_version=product_idea.prompt_version,
        product_type=product_idea.design_instructions.get('product_type', 'sticker'),
        design_description=product_idea.image_description
    )

def db_to_product_idea(orm_product_info: ORMProductInfo, reddit_context: RedditContext) -> ProductIdea:
    return ProductIdea(
        theme=orm_product_info.theme,
        image_description=orm_product_info.design_description,
        design_instructions={
            'image': orm_product_info.image_url,
            'template_id': orm_product_info.template_id,
            'product_type': orm_product_info.product_type
        },
        reddit_context=reddit_context,
        model=orm_product_info.model,
        prompt_version=orm_product_info.prompt_version
    )

def reddit_context_to_db(reddit_context: RedditContext, pipeline_run_id: int) -> ORMRedditPost:
    return ORMRedditPost(
        pipeline_run_id=pipeline_run_id,
        post_id=reddit_context.post_id,
        title=reddit_context.post_title,
        content=getattr(reddit_context, 'post_content', None),
        subreddit=reddit_context.subreddit,
        url=reddit_context.post_url
    )

def db_to_reddit_context(orm_reddit_post: ORMRedditPost) -> RedditContext:
    return RedditContext(
        post_id=orm_reddit_post.post_id,
        post_title=orm_reddit_post.title,
        post_url=orm_reddit_post.url,
        subreddit=orm_reddit_post.subreddit,
        post_content=orm_reddit_post.content,
        comments=[]  # Comments can be loaded separately if needed
    ) 