#!/usr/bin/env python3
"""
Test script to simulate a commission donation flow by directly creating the database records.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Donation, Subreddit, PipelineTask
from app.models import DonationRequest, DonationStatus
from app.services.stripe_service import StripeService
from app.subreddit_service import get_subreddit_service
from app.task_queue import TaskQueue

def test_commission_flow():
    """Test the commission flow by creating a donation and commission task."""
    
    db = SessionLocal()
    try:
        print("Testing commission flow...")
        
        # 1. Create or get subreddit
        subreddit_service = get_subreddit_service()
        subreddit = subreddit_service.get_or_create_subreddit("golf", db)
        print(f"Subreddit: {subreddit.subreddit_name} (ID: {subreddit.id})")
        
        # 2. Create donation request
        donation_request = DonationRequest(
            amount_usd=Decimal('10.00'),
            customer_email="test@example.com",
            customer_name="Test User",
            subreddit="golf",
            reddit_username="testuser",
            is_anonymous=False,
            donation_type="commission",
            commission_message="Please create a new product from a cool golf post!"
        )
        
        # 3. Create donation record
        donation = Donation(
            stripe_payment_intent_id="pi_test_commission_123",
            amount_cents=1000,
            amount_usd=Decimal('10.00'),
            currency="usd",
            status=DonationStatus.SUCCEEDED.value,
            customer_email=donation_request.customer_email,
            customer_name=donation_request.customer_name,
            subreddit_id=subreddit.id,
            reddit_username=donation_request.reddit_username,
            is_anonymous=donation_request.is_anonymous,
            donation_type=donation_request.donation_type,
            commission_message=donation_request.commission_message,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db.add(donation)
        db.commit()
        db.refresh(donation)
        print(f"Created donation: {donation.id}")
        
        # 4. Create commission task
        task_queue = TaskQueue(db)
        task = task_queue.add_task(
            task_type="SUBREDDIT_POST",
            subreddit_id=subreddit.id,
            sponsor_id=None,  # No sponsor for this test
            priority=10,  # High priority for commission
            context_data={
                "donation_id": donation.id,
                "donation_amount": float(donation.amount_usd),
                "customer_name": donation.customer_name,
                "is_anonymous": donation.is_anonymous,
                "donation_type": donation.donation_type,
                "commission_message": donation.commission_message,
                "commission_type": "random_post",
            }
        )
        
        print(f"Created commission task: {task.id}")
        print(f"Task type: {task.type}")
        print(f"Task status: {task.status}")
        print(f"Task priority: {task.priority}")
        print(f"Task context: {task.context_data}")
        
        # 5. Check if task was created successfully
        task_check = db.query(PipelineTask).filter_by(id=task.id).first()
        if task_check:
            print("✅ Commission task created successfully!")
            return True
        else:
            print("❌ Commission task creation failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error in commission flow: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_commission_flow()
    if success:
        print("\n🎉 Commission flow test completed successfully!")
        print("You can now run the task runner to process the commission task.")
    else:
        print("\n💥 Commission flow test failed!") 