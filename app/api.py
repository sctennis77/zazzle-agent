import logging
import os
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

import stripe
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import SessionLocal, get_db, init_db
from app.db.models import PipelineRun, ProductInfo, RedditPost, PipelineRunUsage, Donation
from app.models import (
    GeneratedProductSchema, PipelineRunSchema, PipelineRunUsageSchema,
    DonationRequest, DonationResponse, DonationSchema, DonationSummary, DonationStatus
)
from app.models import ProductInfo as ProductInfoDataClass
from app.models import ProductInfoSchema, RedditContext, RedditPostSchema
from app.pipeline_status import PipelineStatus
from app.services.stripe_service import StripeService
from app.utils.logging_config import setup_logging

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


@app.on_event("startup")
async def startup_event():
    """Initialize the database when the application starts."""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully!")


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

                # Convert ORM models to in-memory models
                reddit_context = RedditContext(
                    post_id=reddit_post.post_id,
                    post_title=reddit_post.title,
                    post_url=reddit_post.url,
                    subreddit=reddit_post.subreddit,
                    post_content=reddit_post.content,
                    permalink=reddit_post.permalink,
                    comments=(
                        [{"text": reddit_post.comment_summary}]
                        if reddit_post.comment_summary
                        else [] or []
                    ),
                )

                product_info_data = ProductInfoDataClass(
                    product_id=str(product_info.id),
                    name=product_info.theme,
                    product_type=product_info.product_type,
                    image_url=product_info.image_url,
                    product_url=product_info.product_url,
                    zazzle_template_id=product_info.template_id,
                    zazzle_tracking_code="",  # This should come from config
                    theme=product_info.theme,
                    model=product_info.model,
                    prompt_version=product_info.prompt_version,
                    reddit_context=reddit_context,
                    design_instructions={
                        "description": product_info.design_description
                    },
                    affiliate_link=product_info.affiliate_link,
                )

                # Convert to Pydantic schemas using model_validate
                try:
                    product_schema = ProductInfoSchema.model_validate(product_info)
                    pipeline_schema = PipelineRunSchema.model_validate(run)
                    reddit_schema = RedditPostSchema.model_validate(reddit_post)
                    
                    # Fetch usage data
                    usage_data = db.query(PipelineRunUsage).filter_by(pipeline_run_id=run.id).first()
                    usage_schema = PipelineRunUsageSchema.model_validate(usage_data) if usage_data else None

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
            except Exception as e:
                logger.error(f"Error processing pipeline run {run.id}: {str(e)}")
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
        List[GeneratedProductSchema]: A list of Pydantic models containing product information,
        pipeline run details, and associated Reddit post data.

    Raises:
        HTTPException: If there is an error fetching the data from the database or
            converting the data to Pydantic models.
    """
    db = SessionLocal()
    try:
        logger.info("Starting get_generated_products request")
        products = fetch_successful_pipeline_runs(db)
        try:
            # Convert ORM models to Pydantic schemas
            result = [
                GeneratedProductSchema.model_validate(product) for product in products
            ]
            logger.info(
                f"Successfully converted {len(result)} products to response format"
            )
            return result
        except Exception as e:
            logger.error(f"Error converting models to Pydantic schemas: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=f"Error converting data to response format: {str(e)}",
            )
    except Exception as e:
        logger.error(f"Error in get_generated_products: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/redirect/{image_name}")
async def redirect_to_product(image_name: str):
    """
    Redirect route for QR codes. Takes an image filename and redirects to the gallery with the product opened.
    
    Args:
        image_name (str): The image filename (e.g., "1juzYyg.png" or "256344169523425346_20250625123345_1024x1024.png")
        
    Returns:
        RedirectResponse: Redirects to the frontend gallery with product opened
    """
    db = SessionLocal()
    try:
        # Clean the image name (remove any path components)
        clean_image_name = image_name.split('/')[-1]
        logger.info(f"Looking for product with image: {clean_image_name}")
        
        # Find the product by image_url containing the filename
        # First try exact match with the clean image name
        product = db.query(ProductInfo).filter(
            ProductInfo.image_url.contains(clean_image_name)
        ).join(
            RedditPost, 
            ProductInfo.reddit_post_id == RedditPost.id
        ).first()
        
        if not product:
            # If not found, try a broader search
            product = db.query(ProductInfo).filter(
                ProductInfo.image_url.contains(clean_image_name.split('.')[0])
            ).join(
                RedditPost, 
                ProductInfo.reddit_post_id == RedditPost.id
            ).first()
        
        if product:
            reddit_post = product.reddit_post
            logger.info(f"Redirecting {image_name} to gallery with product {reddit_post.post_id}")
            
            # Redirect to gallery with query parameter to open the specific product
            frontend_url = f"http://localhost:5175/?product={reddit_post.post_id}"
            return RedirectResponse(url=frontend_url, status_code=302)
        else:
            logger.warning(f"Product not found for image: {clean_image_name}")
            # Fallback to gallery without specific product
            return RedirectResponse(url="http://localhost:5175/", status_code=302)
            
    except Exception as e:
        logger.error(f"Error in redirect: {e}")
        # Fallback to gallery
        return RedirectResponse(url="http://localhost:5175/", status_code=302)
    finally:
        db.close()


@app.get("/api/product/{image_name}")
async def get_product_by_image(image_name: str):
    """
    Get a single product by image filename.
    
    Args:
        image_name (str): The image filename
        
    Returns:
        GeneratedProductSchema: The product data
    """
    db = SessionLocal()
    try:
        # Find the product by image_url containing the filename
        product = db.query(ProductInfo).filter(
            ProductInfo.image_url.contains(image_name)
        ).first()
        
        if not product:
            # Try to find by extracting filename from image_url
            for product_info in db.query(ProductInfo).all():
                if product_info.image_url and image_name in product_info.image_url:
                    product = product_info
                    break
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with image {image_name} not found")
        
        # Get the associated Reddit post and pipeline run
        reddit_post = db.query(RedditPost).filter_by(id=product.reddit_post_id).first()
        pipeline_run = db.query(PipelineRun).filter_by(id=product.pipeline_run_id).first()
        
        if not reddit_post or not pipeline_run:
            raise HTTPException(status_code=404, detail="Associated data not found")
        
        # Convert to schemas
        product_schema = ProductInfoSchema.model_validate(product)
        pipeline_schema = PipelineRunSchema.model_validate(pipeline_run)
        reddit_schema = RedditPostSchema.model_validate(reddit_post)
        
        # Fetch usage data
        usage_data = db.query(PipelineRunUsage).filter_by(pipeline_run_id=pipeline_run.id).first()
        usage_schema = PipelineRunUsageSchema.model_validate(usage_data) if usage_data else None
        
        return GeneratedProductSchema(
            product_info=product_schema,
            pipeline_run=pipeline_schema,
            reddit_post=reddit_schema,
            usage=usage_schema,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product by image: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@app.post("/api/donations/create-payment-intent", response_model=DonationResponse)
async def create_donation_payment_intent(
    donation_request: DonationRequest,
    db: Session = Depends(get_db)
):
    """
    Create a Stripe payment intent for a donation.
    
    Args:
        donation_request: The donation request containing amount and customer info
        db: Database session
        
    Returns:
        DonationResponse: Payment intent data for client-side confirmation
        
    Raises:
        HTTPException: If payment intent creation fails
    """
    try:
        logger.info(f"Creating payment intent for donation: ${donation_request.amount_usd}")
        
        # Create payment intent with Stripe
        payment_intent_data = stripe_service.create_payment_intent(donation_request)
        
        # Save donation record to database
        donation = stripe_service.save_donation_to_db(db, payment_intent_data, donation_request)
        
        logger.info(f"Successfully created payment intent {payment_intent_data['payment_intent_id']} for donation {donation.id}")
        
        return DonationResponse(
            client_secret=payment_intent_data["client_secret"],
            payment_intent_id=payment_intent_data["payment_intent_id"]
        )
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating payment intent: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Payment error: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating payment intent: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/donations/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Stripe webhook events for payment status updates.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        Dict: Webhook response
    """
    try:
        # Get the webhook secret from environment
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        if not webhook_secret:
            logger.error("STRIPE_WEBHOOK_SECRET not configured")
            raise HTTPException(status_code=500, detail="Webhook secret not configured")
        
        # Get the raw body
        body = await request.body()
        
        # Get the signature from headers
        signature = request.headers.get("stripe-signature")
        if not signature:
            logger.error("No Stripe signature found in headers")
            raise HTTPException(status_code=400, detail="No signature found")
        
        try:
            # Verify the webhook
            event = stripe.Webhook.construct_event(
                body, signature, webhook_secret
            )
        except ValueError as e:
            logger.error(f"Invalid payload: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Handle the event
        event_type = event["type"]
        logger.info(f"Received Stripe webhook event: {event_type}")
        
        if event_type == "payment_intent.succeeded":
            payment_intent = event["data"]["object"]
            payment_intent_id = payment_intent["id"]
            
            # Update donation status to succeeded
            donation = stripe_service.update_donation_status(
                db, payment_intent_id, DonationStatus.SUCCEEDED
            )
            
            if donation:
                logger.info(f"Updated donation {donation.id} status to succeeded")
            else:
                logger.warning(f"No donation found for payment intent {payment_intent_id}")
                
        elif event_type == "payment_intent.payment_failed":
            payment_intent = event["data"]["object"]
            payment_intent_id = payment_intent["id"]
            
            # Update donation status to failed
            donation = stripe_service.update_donation_status(
                db, payment_intent_id, DonationStatus.FAILED
            )
            
            if donation:
                logger.info(f"Updated donation {donation.id} status to failed")
            else:
                logger.warning(f"No donation found for payment intent {payment_intent_id}")
                
        elif event_type == "payment_intent.canceled":
            payment_intent = event["data"]["object"]
            payment_intent_id = payment_intent["id"]
            
            # Update donation status to canceled
            donation = stripe_service.update_donation_status(
                db, payment_intent_id, DonationStatus.CANCELED
            )
            
            if donation:
                logger.info(f"Updated donation {donation.id} status to canceled")
            else:
                logger.warning(f"No donation found for payment intent {payment_intent_id}")
        
        else:
            logger.info(f"Unhandled event type: {event_type}")
        
        return {"status": "success"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/donations/summary", response_model=DonationSummary)
async def get_donation_summary(db: Session = Depends(get_db)):
    """
    Get donation summary statistics.
    
    Args:
        db: Database session
        
    Returns:
        DonationSummary: Summary of donation statistics
    """
    try:
        summary_data = stripe_service.get_donation_summary(db)
        
        # Convert donation objects to schemas
        recent_donations = [
            DonationSchema.model_validate(donation) 
            for donation in summary_data["recent_donations"]
        ]
        
        return DonationSummary(
            total_donations=summary_data["total_donations"],
            total_amount_usd=summary_data["total_amount_usd"],
            total_donors=summary_data["total_donors"],
            recent_donations=recent_donations,
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
    Get donation details by Stripe payment intent ID.
    
    Args:
        payment_intent_id: Stripe payment intent ID
        db: Database session
        
    Returns:
        DonationSchema: Donation details
        
    Raises:
        HTTPException: If donation not found
    """
    try:
        donation = stripe_service.get_donation_by_payment_intent(db, payment_intent_id)
        
        if not donation:
            raise HTTPException(status_code=404, detail="Donation not found")
        
        return DonationSchema.model_validate(donation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting donation {payment_intent_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    logger.info("Starting API server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
