import json
import logging
import os
import traceback
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import stripe
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi import WebSocket
from fastapi import WebSocketDisconnect

from app.db.database import SessionLocal, get_db, init_db
from app.db.models import PipelineRun, ProductInfo, RedditPost, PipelineRunUsage, Donation, SubredditFundraisingGoal, PipelineTask
from app.models import (
    GeneratedProductSchema, PipelineRunSchema, PipelineRunUsageSchema,
    DonationRequest, DonationResponse, DonationSchema, DonationSummary, DonationStatus,
    CheckoutSessionResponse, ProductInfoSchema, RedditContext
)
from app.models import ProductInfo as ProductInfoDataClass
from app.models import RedditPostSchema
from app.pipeline_status import PipelineStatus
from app.services.stripe_service import StripeService
from app.services.commission_validator import CommissionValidator
from app.subreddit_service import get_subreddit_service
from app.subreddit_tier_service import SubredditTierService
from app.task_queue import TaskQueue
from app.utils.logging_config import setup_logging
from app.utils.reddit_utils import extract_post_id
from app.task_manager import TaskManager
from app.websocket_manager import websocket_manager

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
    ],  # Allow all common Vite dev ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Stripe service
stripe_service = StripeService()

# Initialize task manager
task_manager = TaskManager()


@app.on_event("startup")
async def startup_event():
    """Initialize the database and WebSocket manager when the application starts."""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully!")
    
    logger.info("Starting WebSocket manager with Redis integration...")
    await websocket_manager.start()
    logger.info("WebSocket manager started successfully!")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources when the application shuts down."""
    logger.info("Stopping WebSocket manager...")
    await websocket_manager.stop()
    logger.info("WebSocket manager stopped successfully!")


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker and Kubernetes."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


def model_to_dict(obj):
    if obj is None:
        return None
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def fetch_successful_pipeline_runs(db: Session) -> List[GeneratedProductSchema]:
    """
    Fetch all successful pipeline runs and their related data from the database.

    Returns:
        List[GeneratedProductSchema]: A list of Pydantic models containing product information,
        pipeline run details, and associated Reddit post data.
    """
    try:
        logger.info("Fetching successful pipeline runs...")
        pipeline_runs = (
            db.query(PipelineRun).filter_by(status=PipelineStatus.COMPLETED.value).all()
        )
        logger.info(f"Found {len(pipeline_runs)} completed pipeline runs.")
        products = []
        for run in pipeline_runs:
            try:
                logger.info(f"Processing pipeline run {run.id}")
                product_info = (
                    db.query(ProductInfo).filter_by(pipeline_run_id=run.id).first()
                )
                if not product_info:
                    logger.warning(f"No product info found for pipeline run {run.id}")
                    continue
                logger.info(f"Found product info: {product_info.id}")

                reddit_post = run.reddit_posts[0] if run.reddit_posts else None
                if not reddit_post:
                    logger.warning(f"No reddit post found for pipeline run {run.id}")
                    continue
                logger.info(f"Found reddit post: {reddit_post.post_id}")

                # Fetch donation information if available
                donation_info = None
                pipeline_task = db.query(PipelineTask).filter_by(pipeline_run_id=run.id).first()
                if pipeline_task and pipeline_task.donation_id:
                    donation = db.query(Donation).filter_by(id=pipeline_task.donation_id).first()
                    if donation:
                        donation_info = {
                            "reddit_username": donation.reddit_username if not donation.is_anonymous else "Anonymous",
                            "tier_name": donation.tier,
                            "tier_min_amount": float(donation.amount_usd),  # Use actual donation amount
                            "donation_amount": float(donation.amount_usd),
                            "is_anonymous": donation.is_anonymous,
                            "donation_type": donation.donation_type,
                            "commission_type": donation.commission_type
                        }
                
                # Get subreddit name for reddit context
                subreddit_name = reddit_post.subreddit.subreddit_name if reddit_post.subreddit else "unknown"

                # Convert ORM models to in-memory models
                reddit_context = RedditContext(
                    post_id=reddit_post.post_id,
                    post_title=reddit_post.title,
                    post_url=reddit_post.url,
                    subreddit=subreddit_name,
                    post_content=reddit_post.content,
                    permalink=reddit_post.permalink,
                    comments=(
                        [{"text": reddit_post.comment_summary}]
                        if reddit_post.comment_summary
                        else [] or []
                    ),
                )

                # Convert to Pydantic schemas using model_validate
                product_schema = ProductInfoSchema.model_validate(product_info)
                pipeline_schema = PipelineRunSchema.model_validate(run)
                reddit_post_dict = reddit_post.__dict__.copy()
                reddit_post_dict['subreddit'] = reddit_post.subreddit.subreddit_name if reddit_post.subreddit else None
                reddit_schema = RedditPostSchema.model_validate(reddit_post_dict)
                
                # Fetch usage data
                usage_data = db.query(PipelineRunUsage).filter_by(pipeline_run_id=run.id).first()
                usage_schema = PipelineRunUsageSchema.model_validate(usage_data) if usage_data else None

                # Add donation info to the schema if available
                if donation_info:
                    product_schema.donation_info = donation_info

                products.append(
                    GeneratedProductSchema(
                        product_info=product_schema,
                        pipeline_run=pipeline_schema,
                        reddit_post=reddit_schema,
                        usage=usage_schema,
                    )
                )
                logger.info(
                    f"Successfully converted pipeline run {run.id} to schema with usage data"
                )
            except Exception as e:
                logger.error(
                    f"Error converting pipeline run {run.id} to schema: {str(e)}"
                )
                logger.error(traceback.format_exc())
                continue
        logger.info(f"Returning {len(products)} products.")
        return products
    except Exception as e:
        logger.error(f"Error in fetch_successful_pipeline_runs: {str(e)}")
        logger.error(traceback.format_exc())
        raise


@app.get("/api/generated_products", response_model=List[GeneratedProductSchema])
async def get_generated_products():
    """
    API endpoint to retrieve all successful pipeline runs and their related data.
    
    Returns:
        List[GeneratedProductSchema]: A list of generated products with their associated data.
    """
    logger.info("Starting get_generated_products request")
    try:
        db = SessionLocal()
        products = fetch_successful_pipeline_runs(db)
        logger.info(f"Returning {len(products)} products.")
        logger.info("Successfully converted products to response format")
        return products
    except Exception as e:
        logger.error(f"Error in get_generated_products: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@app.get("/redirect/{image_name}")
async def redirect_to_product(image_name: str):
    """
    Redirect to a product based on the image name.
    
    Args:
        image_name: The name of the image file
        
    Returns:
        RedirectResponse: Redirect to the product URL
    """
    try:
        db = SessionLocal()
        
        # Find the product info by image name
        product_info = (
            db.query(ProductInfo)
            .filter(ProductInfo.image_url.like(f"%{image_name}%"))
            .first()
        )
        
        if not product_info:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Redirect to the product URL
        return RedirectResponse(url=product_info.product_url)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error redirecting to product: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@app.get("/api/product/{image_name}")
async def get_product_by_image(image_name: str):
    """
    Get product information by image name.
    
    Args:
        image_name: The name of the image file
        
    Returns:
        Dict: Product information
    """
    try:
        db = SessionLocal()
        
        # Find the product info by image name
        product_info = (
            db.query(ProductInfo)
            .filter(ProductInfo.image_url.like(f"%{image_name}%"))
            .first()
        )
        
        if not product_info:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Get related data
        pipeline_run = product_info.pipeline_run
        reddit_post = product_info.reddit_post
        
        return {
            "product_info": model_to_dict(product_info),
            "pipeline_run": model_to_dict(pipeline_run),
            "reddit_post": model_to_dict(reddit_post),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product by image: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@app.post("/api/donations/create-payment-intent")
async def create_payment_intent(donation_request: DonationRequest):
    """Create a Stripe payment intent for a donation."""
    try:
        # Debug logging
        logger.info(f"Received donation request: reddit_username='{donation_request.reddit_username}', is_anonymous={donation_request.is_anonymous}")
        
        # Extract post ID from subreddit if provided
        post_id = None
        if donation_request.post_id:
            post_id = extract_post_id(donation_request.post_id)
            logger.info(f"Extracted post ID: {post_id} from input: {donation_request.post_id}")
            donation_request.post_id = post_id
        
        # Create payment intent
        result = stripe_service.create_payment_intent(donation_request)
        
        logger.info(f"Created payment intent {result['payment_intent_id']} for donation")
        
        return {
            "client_secret": result["client_secret"],
            "payment_intent_id": result["payment_intent_id"]
        }
    except Exception as e:
        logger.error(f"Error creating payment intent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/donations/summary", response_model=DonationSummary)
async def get_donation_summary(db: Session = Depends(get_db)):
    """
    Get donation summary statistics.
    
    Args:
        db: Database session
        
    Returns:
        DonationSummary: Summary statistics
    """
    try:
        summary_data = stripe_service.get_donation_summary(db)
        
        return DonationSummary(
            total_donations=summary_data["total_donations"],
            total_amount_usd=summary_data["total_amount_usd"],
            total_donors=summary_data["total_donors"],
            recent_donations=[
                DonationSchema(
                    id=donation.id,
                    stripe_payment_intent_id=donation.stripe_payment_intent_id,
                    amount_cents=int(float(donation.amount_usd) * 100),
                    amount_usd=donation.amount_usd,
                    currency="usd",
                    customer_name=donation.customer_name,
                    customer_email=donation.customer_email,
                    message=donation.message,
                    subreddit=donation.subreddit.subreddit_name if donation.subreddit else None,
                    reddit_username=donation.reddit_username,
                    is_anonymous=donation.is_anonymous,
                    status=donation.status,
                    created_at=donation.created_at,
                    updated_at=donation.updated_at,
                )
                for donation in summary_data["recent_donations"]
            ],
        )
        
    except Exception as e:
        logger.error(f"Error getting donation summary: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/donations/{payment_intent_id}", response_model=DonationSchema)
async def get_donation_by_payment_intent(
    payment_intent_id: str,
    db: Session = Depends(get_db)
):
    """
    Get donation by Stripe payment intent ID.
    
    Args:
        payment_intent_id: Stripe payment intent ID
        db: Database session
        
    Returns:
        DonationSchema: The donation data
    """
    try:
        donation = stripe_service.get_donation_by_payment_intent(db, payment_intent_id)
        if not donation:
            raise HTTPException(status_code=404, detail="Donation not found")
        
        # Convert database model to schema manually to handle relationships
        return DonationSchema(
            id=donation.id,
            stripe_payment_intent_id=donation.stripe_payment_intent_id,
            amount_cents=donation.amount_cents,
            amount_usd=donation.amount_usd,
            currency=donation.currency,
            status=donation.status,
            tier=donation.tier,
            customer_email=donation.customer_email,
            customer_name=donation.customer_name,
            message=donation.message,
            subreddit=donation.subreddit.subreddit_name if donation.subreddit else None,
            reddit_username=donation.reddit_username,
            is_anonymous=donation.is_anonymous,
            donation_type=donation.donation_type,
            commission_type=donation.commission_type,
            post_id=donation.post_id,
            commission_message=donation.commission_message,
            created_at=donation.created_at,
            updated_at=donation.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting donation: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/donation-tiers")
async def get_donation_tiers():
    """
    Get all donation tiers with their amounts.
    
    Returns:
        List: Donation tiers
    """
    try:
        from app.models import TIER_AMOUNTS, DonationTier
        
        tiers = []
        for tier in DonationTier:
            tiers.append({
                "name": tier.value,
                "min_amount": float(TIER_AMOUNTS[tier]),
                "display_name": tier.value.title(),
            })
        
        # Sort by amount
        tiers.sort(key=lambda x: x["min_amount"])
        
        return tiers
    except Exception as e:
        logger.error(f"Error getting donation tiers: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/donations")
async def get_donations(db: Session = Depends(get_db)):
    """
    Get all donations with their tier information.
    
    Args:
        db: Database session
        
    Returns:
        List: Donations with related data
    """
    try:
        donations = (
            db.query(Donation)
            .order_by(Donation.created_at.desc())
            .all()
        )
        
        return [
            {
                "id": donation.id,
                "amount_usd": float(donation.amount_usd),
                "customer_name": donation.customer_name,
                "customer_email": donation.customer_email,
                "message": donation.message,
                "subreddit": donation.subreddit.subreddit_name if donation.subreddit else None,
                "reddit_username": donation.reddit_username,
                "is_anonymous": donation.is_anonymous,
                "status": donation.status,
                "tier": donation.tier,
                "donation_type": donation.donation_type,
                "commission_type": donation.commission_type,
                "post_id": donation.post_id,
                "commission_message": donation.commission_message,
                "created_at": donation.created_at.isoformat(),
            }
            for donation in donations
        ]
        
    except Exception as e:
        logger.error(f"Error getting donations: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/subreddit-tiers")
async def get_subreddit_tiers(db: Session = Depends(get_db)):
    """
    Get all subreddit tiers.
    
    Args:
        db: Database session
        
    Returns:
        List: Subreddit tiers
    """
    try:
        tiers = (
            db.query(SubredditTier)
            .join(SubredditTier.subreddit)
            .order_by(SubredditTier.subreddit_id, SubredditTier.tier_level)
            .all()
        )
        
        return [
            {
                "id": tier.id,
                "subreddit": tier.subreddit.subreddit_name,
                "tier_level": tier.tier_level,
                "min_total_donation": float(tier.min_total_donation),
                "status": tier.status,
                "created_at": tier.created_at.isoformat(),
                "completed_at": tier.completed_at.isoformat() if tier.completed_at else None,
            }
            for tier in tiers
        ]
        
    except Exception as e:
        logger.error(f"Error getting subreddit tiers: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/subreddit-fundraising")
async def get_subreddit_fundraising(db: Session = Depends(get_db)):
    """
    Get all subreddit fundraising goals.
    
    Args:
        db: Database session
        
    Returns:
        List: Subreddit fundraising goals
    """
    try:
        goals = (
            db.query(SubredditFundraisingGoal)
            .join(SubredditFundraisingGoal.subreddit)
            .order_by(SubredditFundraisingGoal.created_at.desc())
            .all()
        )
        
        return [
            {
                "id": goal.id,
                "subreddit": goal.subreddit.subreddit_name,
                "goal_amount": float(goal.goal_amount),
                "current_amount": float(goal.current_amount),
                "progress_percentage": float(goal.current_amount / goal.goal_amount * 100) if goal.goal_amount > 0 else 0,
                "deadline": goal.deadline.isoformat() if goal.deadline else None,
                "status": goal.status,
                "created_at": goal.created_at.isoformat(),
                "completed_at": goal.completed_at.isoformat() if goal.completed_at else None,
            }
            for goal in goals
        ]
        
    except Exception as e:
        logger.error(f"Error getting subreddit fundraising: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/tasks")
async def get_tasks(limit: int = 50, db: Session = Depends(get_db)):
    """
    Get all tasks.
    
    Args:
        limit: Maximum number of tasks to return
        db: Database session
        
    Returns:
        List: Tasks with related data
    """
    try:
        tasks = task_manager.list_tasks(limit=limit)
        return tasks
        
    except Exception as e:
        logger.error(f"Error getting tasks: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/tasks/queue")
async def get_queue_status(db: Session = Depends(get_db)):
    """
    Get the current status of the task queue.
    
    Args:
        db: Database session
        
    Returns:
        Dict: Queue status information
    """
    try:
        task_queue = TaskQueue(db)
        return task_queue.get_queue_status()
        
    except Exception as e:
        logger.error(f"Error getting queue status: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/tasks")
async def add_task(
    task_type: str,
    subreddit: str,
    priority: int = 0,
    donation_id: Optional[int] = None,
    scheduled_for: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """
    Add a task to the queue.
    
    Args:
        task_type: Type of task (SUBREDDIT_POST)
        subreddit: Target subreddit (use "all" for front page)
        priority: Task priority (higher number = higher priority)
        donation_id: Associated donation ID
        scheduled_for: When to execute the task
        
    Returns:
        Dict: Task information
    """
    try:
        task_queue = TaskQueue(db)
        
        # Validate task type
        if task_type != "SUBREDDIT_POST":
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid task type: {task_type}. Only SUBREDDIT_POST is supported"
            )
        
        # Validate subreddit
        if not subreddit:
            raise HTTPException(
                status_code=400,
                detail="Subreddit is required"
            )
        
        task = task_queue.add_task_by_name(
            task_type=task_type,
            subreddit_name=subreddit,
            donation_id=donation_id,
            priority=priority,
            scheduled_for=scheduled_for,
        )
        
        return {
            "id": task.id,
            "type": task.type,
            "subreddit": task.subreddit.subreddit_name,
            "priority": task.priority,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding task: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/api/tasks/{task_id}/status")
async def update_task_status(
    task_id: int,
    status: str,
    error_message: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Update task status.
    
    Args:
        task_id: ID of the task
        status: New status
        error_message: Error message if failed (optional)
        db: Database session
        
    Returns:
        Dict: Success response
    """
    try:
        task_queue = TaskQueue(db)
        
        if status == "completed":
            success = task_queue.mark_completed(task_id, error_message)
        elif status == "in_progress":
            success = task_queue.mark_in_progress(task_id)
        else:
            raise HTTPException(status_code=400, detail="Invalid status")
        
        if not success:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {"success": True, "message": f"Task {task_id} status updated to {status}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task status: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/subreddit/{subreddit}/stats")
async def get_subreddit_stats(subreddit: str, db: Session = Depends(get_db)):
    """
    Get comprehensive stats for a subreddit.
    
    Args:
        subreddit: Subreddit name
        db: Database session
        
    Returns:
        Dict: Subreddit statistics
    """
    try:
        tier_service = SubredditTierService(db)
        return tier_service.get_subreddit_stats(subreddit)
    except Exception as e:
        logger.error(f"Error getting subreddit stats: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/subreddit/{subreddit}/tiers")
async def create_subreddit_tiers(
    subreddit: str,
    tier_levels: List[Dict[str, Any]],
    db: Session = Depends(get_db)
):
    """
    Create subreddit tiers for a subreddit.
    
    Args:
        subreddit: Subreddit name
        tier_levels: List of tier configurations
        db: Database session
        
    Returns:
        Dict: Created tiers information
    """
    try:
        tier_service = SubredditTierService(db)
        tiers = tier_service.create_subreddit_tiers(subreddit, tier_levels)
        
        return {
            "subreddit": subreddit,
            "created_tiers": len(tiers),
            "tiers": [
                {
                    "id": tier.id,
                    "level": tier.tier_level,
                    "min_total_donation": float(tier.min_total_donation),
                    "status": tier.status
                }
                for tier in tiers
            ]
        }
    except Exception as e:
        logger.error(f"Error creating subreddit tiers: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/subreddit/{subreddit}/goals")
async def create_fundraising_goal(
    subreddit: str,
    goal_amount: float,
    deadline: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Create a fundraising goal for a subreddit.
    
    Args:
        subreddit: Subreddit name
        goal_amount: Goal amount
        deadline: Optional deadline (ISO format)
        db: Database session
        
    Returns:
        Dict: Created goal information
    """
    try:
        from decimal import Decimal
        from datetime import datetime
        
        tier_service = SubredditTierService(db)
        
        # Parse deadline if provided
        deadline_dt = None
        if deadline:
            try:
                deadline_dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid deadline format")
        
        goal = tier_service.create_fundraising_goal(
            subreddit=subreddit,
            goal_amount=Decimal(str(goal_amount)),
            deadline=deadline_dt,
        )
        
        return {
            "id": goal.id,
            "subreddit": subreddit,
            "goal_amount": float(goal.goal_amount),
            "current_amount": float(goal.current_amount),
            "deadline": goal.deadline.isoformat() if goal.deadline else None,
            "status": goal.status,
            "created_at": goal.created_at.isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error creating fundraising goal: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/subreddit/{subreddit}/tiers/check")
async def check_subreddit_tiers(subreddit: str, db: Session = Depends(get_db)):
    """
    Check subreddit tiers and fundraising goals for a subreddit.
    
    Args:
        subreddit: Subreddit name
        db: Database session
        
    Returns:
        Dict: Tier and goal information
    """
    try:
        tier_service = SubredditTierService(db)
        return tier_service.check_subreddit_tiers(subreddit)
        
    except Exception as e:
        logger.error(f"Error checking subreddit tiers: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/posts/{post_id}/donations")
async def get_post_donations(
    post_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all donations for a specific post.
    
    Args:
        post_id: Reddit post ID
        db: Database session
        
    Returns:
        List: Donations with related data for the post
    """
    try:
        # Find donations for this post
        donations = (
            db.query(Donation)
            .filter_by(post_id=post_id, status=DonationStatus.SUCCEEDED.value)
            .all()
        )
        
        return [
            {
                "id": donation.id,
                "amount_usd": float(donation.amount_usd),
                "customer_name": donation.customer_name,
                "customer_email": donation.customer_email,
                "message": donation.message,
                "subreddit": donation.subreddit.subreddit_name if donation.subreddit else None,
                "reddit_username": donation.reddit_username,
                "is_anonymous": donation.is_anonymous,
                "status": donation.status,
                "tier": donation.tier,
                "donation_type": donation.donation_type,
                "commission_type": donation.commission_type,
                "commission_message": donation.commission_message,
                "created_at": donation.created_at.isoformat(),
            }
            for donation in donations
        ]
        
    except Exception as e:
        logger.error(f"Error getting donations for post {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/products/{pipeline_run_id}/donations")
async def get_product_donations(
    pipeline_run_id: int,
    type: str = Query("all", pattern="^(all|commission|support)$"),
    db: Session = Depends(get_db)
):
    """
    Get donation information for a specific product (pipeline run), including commission and support donations.
    Args:
        pipeline_run_id: Pipeline run ID
        type: Filter for 'commission', 'support', or 'all' (default: all)
        db: Database session
    Returns:
        Dict: Donation information
    """
    try:
        # Get the pipeline task for this run
        pipeline_task = db.query(PipelineTask).filter_by(pipeline_run_id=pipeline_run_id).first()
        if not pipeline_task:
            return {"commission": None, "support": []}

        # Get the associated reddit post
        reddit_post = db.query(RedditPost).filter_by(pipeline_run_id=pipeline_run_id).first()
        
        # Get commission info from donation
        commission_info = None
        
        if pipeline_task.donation_id:
            donation = db.query(Donation).filter_by(id=pipeline_task.donation_id).first()
            if donation and donation.donation_type == "commission":
                commission_info = {
                    "reddit_username": donation.reddit_username if not donation.is_anonymous else "Anonymous",
                    "tier_name": donation.tier,
                    "tier_min_amount": float(donation.amount_usd),
                    "donation_amount": float(donation.amount_usd),
                    "is_anonymous": donation.is_anonymous,
                    "commission_message": donation.commission_message,
                    "commission_type": donation.commission_type,
                }

        # Get support donations
        support_donations = []
        if reddit_post:
            # Find all support donations for this post
            donations = (
                db.query(Donation)
                .filter_by(
                    post_id=reddit_post.post_id, 
                    donation_type="support",
                    status=DonationStatus.SUCCEEDED.value
                )
                .all()
            )
            for donation in donations:
                support_donations.append({
                    "reddit_username": donation.reddit_username if not donation.is_anonymous else "Anonymous",
                    "tier_name": donation.tier,
                    "tier_min_amount": float(donation.amount_usd),
                    "donation_amount": float(donation.amount_usd),
                    "is_anonymous": donation.is_anonymous,
                    "message": donation.message,
                    "created_at": donation.created_at.isoformat(),
                    "donation_id": donation.id,
                })

        # Filter by type param
        if type == "commission":
            return {"commission": commission_info}
        elif type == "support":
            return {"support": support_donations}
        else:
            return {"commission": commission_info, "support": support_donations}

    except Exception as e:
        logger.error(f"Error getting donations for pipeline run {pipeline_run_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/api/donations/payment-intent/{payment_intent_id}/update")
async def update_payment_intent(payment_intent_id: str, donation_request: DonationRequest):
    """Update a Stripe payment intent with new metadata and amount."""
    try:
        # Debug logging
        logger.info(f"Updating payment intent {payment_intent_id} with reddit_username='{donation_request.reddit_username}', is_anonymous={donation_request.is_anonymous}")
        
        # Extract post ID from subreddit if provided
        post_id = None
        if donation_request.post_id:
            post_id = extract_post_id(donation_request.post_id)
            logger.info(f"Extracted post ID: {post_id} from input: {donation_request.post_id}")
        
        # Update the donation request with the extracted post_id
        donation_request.post_id = post_id
        
        # Update payment intent
        result = stripe_service.update_payment_intent(payment_intent_id, donation_request)
        
        logger.info(f"Updated payment intent {payment_intent_id} for donation")
        
        return {
            "client_secret": result["client_secret"],
            "payment_intent_id": result["payment_intent_id"]
        }
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error updating payment intent {payment_intent_id}: {error_message}")
        
        # Return a more specific error response instead of 404
        if "not found" in error_message.lower():
            raise HTTPException(status_code=404, detail=f"Payment intent {payment_intent_id} not found")
        elif "cannot be modified" in error_message.lower():
            raise HTTPException(status_code=400, detail=f"Payment intent {payment_intent_id} cannot be modified")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to update payment intent: {error_message}")


@app.post("/api/donations/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    try:
        body = await request.body()
        sig_header = request.headers.get('stripe-signature')
        
        # For development/testing with Stripe CLI, skip signature verification
        webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET', '')
        if not webhook_secret or os.getenv('STRIPE_CLI_MODE', 'false').lower() == 'true':
            # Parse event without signature verification for development
            import json
            event = json.loads(body)
            logger.info("Skipping webhook signature verification (development mode)")
        else:
            if not sig_header:
                raise HTTPException(status_code=400, detail="Missing stripe-signature header")
            
            # Verify webhook signature
            try:
                event = stripe.Webhook.construct_event(
                    body, sig_header, webhook_secret
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail="Invalid payload")
            except stripe.error.SignatureVerificationError as e:
                raise HTTPException(status_code=400, detail="Invalid signature")
        
        logger.info(f"Received Stripe webhook event: {event['type']}")
        
        # Handle the event
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            await handle_payment_intent_succeeded(payment_intent)
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            await handle_payment_intent_failed(payment_intent)
        else:
            logger.info(f"Unhandled event type: {event['type']}")
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")





async def handle_payment_intent_succeeded(payment_intent):
    """Handle successful payment intent."""
    try:
        logger.info(f"Processing successful payment intent: {payment_intent.id}")
        
        # Get database session
        db = SessionLocal()
        try:
            # Check if this payment intent has already been processed
            existing_donation = db.query(Donation).filter_by(
                stripe_payment_intent_id=payment_intent.id,
                status=DonationStatus.SUCCEEDED.value
            ).first()
            
            if existing_donation:
                logger.info(f"Payment intent {payment_intent.id} already processed for donation {existing_donation.id}, skipping")
                return
            
            # Extract metadata
            metadata = payment_intent.metadata
            
            logger.debug(f"Payment intent metadata: {json.dumps(metadata, indent=2)}")
            
            # Create donation request from metadata
            donation_request = DonationRequest(
                amount_usd=Decimal(payment_intent.amount / 100),
                customer_email=payment_intent.receipt_email,
                customer_name=metadata.get('customer_name'),
                message=metadata.get('message'),
                subreddit=metadata.get('subreddit'),
                reddit_username=metadata.get('reddit_username'),
                is_anonymous=metadata.get('is_anonymous', 'false').lower() == 'true',
                donation_type=metadata.get('donation_type'),
                post_id=metadata.get('post_id') if metadata.get('post_id') else None,
                commission_message=metadata.get('commission_message'),
                commission_type=metadata.get('commission_type'),
            )
            
            logger.debug(f"Extracted donation request: reddit_username='{donation_request.reddit_username}', is_anonymous={donation_request.is_anonymous}")
            
            # Process the donation
            donation = stripe_service.save_donation_to_db(db, {
                "payment_intent_id": payment_intent.id,
                "amount_cents": payment_intent.amount,
                "amount_usd": Decimal(payment_intent.amount / 100),
                "currency": payment_intent.currency,
                "status": payment_intent.status,
                "metadata": payment_intent.metadata,
                "receipt_email": getattr(payment_intent, "receipt_email", None),
                "created": payment_intent.created,
            }, donation_request)
            
            logger.info(
                f"Created donation {donation.id} for payment intent {payment_intent.id} "
                f"(user: {donation.customer_name}, amount: {donation.amount_usd}, type: {donation.donation_type}, tier: {donation.tier})"
            )
            
            # Update donation status to succeeded
            stripe_service.update_donation_status(db, payment_intent.id, DonationStatus.SUCCEEDED)
            
            # Process subreddit tiers if applicable
            stripe_service.process_subreddit_tiers(db, donation)
            
            # Create commission task if this is a commission donation
            if donation.donation_type == "commission":
                # Prepare task data for TaskManager
                task_data = {
                    "donation_id": donation.id,
                    "donation_amount": float(donation.amount_usd),
                    "tier": donation.tier,
                    "customer_name": donation.customer_name,
                    "reddit_username": donation.reddit_username,
                    "is_anonymous": donation.is_anonymous,
                    "donation_type": donation.donation_type,
                    "commission_type": donation.commission_type,
                    "commission_message": donation.commission_message,
                    "post_id": donation.post_id,
                }
                # Create task using TaskManager (this will automatically run in background thread if K8s not available)
                task_id = task_manager.create_commission_task(donation.id, task_data)
                logger.info(
                    f"Commission task {task_id} created for donation {donation.id} "
                    f"(user: {donation.customer_name}, type: {donation.commission_type}, tier: {donation.tier})"
                )
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error handling payment intent success for payment_intent_id={getattr(payment_intent, 'id', None)}: {str(e)}\n{traceback.format_exc()}")
        raise


async def handle_payment_intent_failed(payment_intent):
    """Handle failed payment intent."""
    try:
        logger.info(f"Processing failed payment intent: {payment_intent.id}")
        
        # Get database session
        db = SessionLocal()
        try:
            stripe_service = StripeService()
            stripe_service.update_donation_status(db, payment_intent.id, DonationStatus.FAILED)
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error handling payment intent failure for payment_intent_id={getattr(payment_intent, 'id', None)}: {str(e)}\n{traceback.format_exc()}")
        raise


from app.models import CommissionValidationRequest

def get_commission_validator():
    return CommissionValidator()

@app.post("/api/commissions/validate")
async def validate_commission(
    validation_request: CommissionValidationRequest,
    validator: CommissionValidator = Depends(get_commission_validator),
):
    """
    Validate a commission request and return validated subreddit and post data.
    """
    try:
        logger.info(f"Validating commission: {validation_request.commission_type}")
        # Validate commission
        result = await validator.validate_commission(
            commission_type=validation_request.commission_type,
            subreddit=validation_request.subreddit,
            post_id=validation_request.post_id,
            post_url=None  # Not supported in current model
        )
        logger.info(f"Commission validation result: valid={result.valid}")
        if not result.valid:
            logger.warning(f"Commission validation failed: {result.error}")
            raise HTTPException(status_code=422, detail=result.to_dict())
        return result.to_dict()
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error validating commission: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


@app.post("/api/tasks/commission")
async def create_commission_task(donation_id: int, db: Session = Depends(get_db)):
    """
    Create a commission task for a donation.
    
    Args:
        donation_id: ID of the donation
        db: Database session
        
    Returns:
        Dict: Task information
    """
    try:
        # Get donation
        donation = db.query(Donation).filter_by(id=donation_id).first()
        if not donation:
            logger.error(f"Donation not found for commission task creation (donation_id={donation_id})")
            raise HTTPException(status_code=404, detail="Donation not found")
        
        # Prepare task data for TaskManager
        task_data = {
            "donation_id": donation.id,
            "donation_amount": float(donation.amount_usd),
            "tier": donation.tier,
            "customer_name": donation.customer_name,
            "reddit_username": donation.reddit_username,
            "is_anonymous": donation.is_anonymous,
            "donation_type": donation.donation_type,
            "commission_type": donation.commission_type,
            "commission_message": donation.commission_message,
            "post_id": donation.post_id,
        }
        
        # Create task using TaskManager (this will automatically run in background thread if K8s not available)
        task_id = task_manager.create_commission_task(donation.id, task_data)
        
        logger.info(f"Created commission task: {task_id}")
        
        return {"task_id": task_id}
        
    except Exception as e:
        logger.error(f"Error creating commission task for donation_id={donation_id}: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error creating task: {str(e)}")


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    Get task status.
    Args:
        task_id: ID of the task
    Returns:
        Dict: Task status information
    """
    try:
        status = task_manager.get_task_status(task_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error getting task status: {str(e)}")


@app.websocket("/ws/tasks")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time task updates.
    
    Clients can:
    - Subscribe to specific task updates
    - Receive general task notifications
    - Get real-time progress updates
    """
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message["type"] == "subscribe":
                task_id = message.get("task_id")
                if task_id:
                    await websocket_manager.subscribe_to_task(websocket, task_id)
                    await websocket_manager.send_personal_message(websocket, {
                        "type": "subscribed",
                        "task_id": task_id
                    })
            
            elif message["type"] == "unsubscribe":
                task_id = message.get("task_id")
                if task_id:
                    await websocket_manager.unsubscribe_from_task(websocket, task_id)
                    await websocket_manager.send_personal_message(websocket, {
                        "type": "unsubscribed",
                        "task_id": task_id
                    })
            
            elif message["type"] == "ping":
                await websocket_manager.send_personal_message(websocket, {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
    
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)


@app.get("/api/products/commission/{donation_id}")
async def get_commission_product(donation_id: int, db: Session = Depends(get_db)):
    """
    Get the product created for a specific commission donation.
    
    Args:
        donation_id: ID of the donation
        db: Database session
        
    Returns:
        GeneratedProduct: The product created for this commission
    """
    try:
        # Find the pipeline task for this donation
        pipeline_task = db.query(PipelineTask).filter_by(donation_id=donation_id).first()
        if not pipeline_task:
            raise HTTPException(status_code=404, detail="Commission task not found")
        
        # Get the pipeline run
        pipeline_run = db.query(PipelineRun).filter_by(id=pipeline_task.pipeline_run_id).first()
        if not pipeline_run:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
        
        # Get the product info
        product_info = db.query(ProductInfo).filter_by(pipeline_run_id=pipeline_run.id).first()
        if not product_info:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Get the reddit post
        reddit_post = db.query(RedditPost).filter_by(pipeline_run_id=pipeline_run.id).first()
        if not reddit_post:
            raise HTTPException(status_code=404, detail="Reddit post not found")
        
        # Convert to the expected format
        from app.db.mappers import product_info_from_db, reddit_post_from_db, pipeline_run_from_db
        
        generated_product = GeneratedProduct(
            product_info=product_info_from_db(product_info),
            pipeline_run=pipeline_run_from_db(pipeline_run),
            reddit_post=reddit_post_from_db(reddit_post)
        )
        
        return generated_product
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting commission product: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
