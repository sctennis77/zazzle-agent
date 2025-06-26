"""
Subreddit Tier Service for managing community fundraising tiers and goals.

This module provides functionality to:
- Track subreddit fundraising progress
- Manage subreddit tiers based on total donations
- Create tasks when subreddit tiers are reached
- Handle fundraising goal completion
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session

from app.db.models import Donation, SubredditTier, SubredditFundraisingGoal, Sponsor
from app.task_queue import TaskQueue
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class SubredditTierService:
    """Service for managing subreddit tiers and fundraising goals."""

    def __init__(self, session: Session):
        """
        Initialize the subreddit tier service.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.task_queue = TaskQueue(session)

    def get_subreddit_total_donations(self, subreddit: str) -> Decimal:
        """
        Get total donations for a subreddit, counting each donation only once.
        
        Args:
            subreddit: Subreddit name
            
        Returns:
            Decimal: Total donation amount
        """
        # Query all succeeded donations for this subreddit (direct or via fundraising goal)
        donations = (
            self.session.query(Donation)
            .filter(Donation.subreddit == subreddit)
            .filter(Donation.status == "succeeded")
            .all()
        )
        # Use a set to ensure uniqueness by donation id
        unique_donations = {d.id: d for d in donations}.values()
        return sum(d.amount_usd for d in unique_donations) if unique_donations else Decimal('0')

    def get_subreddit_tiers(self, subreddit: str) -> List[SubredditTier]:
        """
        Get all tiers for a subreddit.
        
        Args:
            subreddit: Subreddit name
            
        Returns:
            List[SubredditTier]: List of subreddit tiers
        """
        return (
            self.session.query(SubredditTier)
            .filter(SubredditTier.subreddit == subreddit)
            .order_by(SubredditTier.tier_level)
            .all()
        )

    def create_subreddit_tiers(self, subreddit: str, tier_levels: List[Dict[str, Any]]) -> List[SubredditTier]:
        """
        Create subreddit tiers for a subreddit.
        
        Args:
            subreddit: Subreddit name
            tier_levels: List of tier configurations with min_total_donation
            
        Returns:
            List[SubredditTier]: Created subreddit tiers
        """
        try:
            tiers = []
            for tier_config in tier_levels:
                tier = SubredditTier(
                    subreddit=subreddit,
                    tier_level=tier_config["level"],
                    min_total_donation=tier_config["min_total_donation"],
                    status="pending"
                )
                self.session.add(tier)
                tiers.append(tier)
            
            self.session.commit()
            logger.info(f"Created {len(tiers)} tiers for subreddit {subreddit}")
            return tiers
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating subreddit tiers: {str(e)}")
            raise

    def check_and_update_tiers(self, subreddit: str) -> List[SubredditTier]:
        """
        Check if any subreddit tiers have been reached and update them.
        
        Args:
            subreddit: Subreddit name
            
        Returns:
            List[SubredditTier]: List of newly completed tiers
        """
        try:
            total_donations = self.get_subreddit_total_donations(subreddit)
            tiers = self.get_subreddit_tiers(subreddit)
            
            completed_tiers = []
            for tier in tiers:
                if (tier.status == "pending" and 
                    total_donations >= tier.min_total_donation):
                    
                    # Mark tier as active
                    tier.status = "active"
                    tier.completed_at = datetime.now(timezone.utc)
                    
                    # Add task to queue for this tier
                    self.task_queue.add_subreddit_tier_task(
                        subreddit=subreddit,
                        priority=5  # Medium priority for tier posts
                    )
                    
                    completed_tiers.append(tier)
                    logger.info(f"Subreddit {subreddit} reached tier {tier.tier_level} "
                              f"(${tier.min_total_donation}) - total: ${total_donations}")
            
            if completed_tiers:
                self.session.commit()
                logger.info(f"Updated {len(completed_tiers)} tiers for subreddit {subreddit}")
            
            return completed_tiers
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error checking subreddit tiers: {str(e)}")
            raise

    def get_fundraising_goals(self, subreddit: Optional[str] = None) -> List[SubredditFundraisingGoal]:
        """
        Get fundraising goals.
        
        Args:
            subreddit: Optional subreddit filter
            
        Returns:
            List[SubredditFundraisingGoal]: List of fundraising goals
        """
        query = self.session.query(SubredditFundraisingGoal)
        if subreddit:
            query = query.filter(SubredditFundraisingGoal.subreddit == subreddit)
        return query.filter(SubredditFundraisingGoal.status == "active").all()

    def create_fundraising_goal(
        self, 
        subreddit: str, 
        goal_amount: Decimal, 
        deadline: Optional[datetime] = None
    ) -> SubredditFundraisingGoal:
        """
        Create a fundraising goal for a subreddit.
        
        Args:
            subreddit: Subreddit name
            goal_amount: Goal amount
            deadline: Optional deadline
            
        Returns:
            SubredditFundraisingGoal: Created fundraising goal
        """
        try:
            goal = SubredditFundraisingGoal(
                subreddit=subreddit,
                goal_amount=goal_amount,
                current_amount=Decimal('0'),
                deadline=deadline,
                status="active"
            )
            
            self.session.add(goal)
            self.session.commit()
            
            logger.info(f"Created fundraising goal for {subreddit}: ${goal_amount}")
            return goal
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating fundraising goal: {str(e)}")
            raise

    def update_fundraising_progress(self, subreddit: str) -> List[SubredditFundraisingGoal]:
        """
        Update fundraising progress for a subreddit.
        
        Args:
            subreddit: Subreddit name
            
        Returns:
            List[SubredditFundraisingGoal]: List of completed goals
        """
        try:
            total_donations = self.get_subreddit_total_donations(subreddit)
            goals = self.get_fundraising_goals(subreddit)
            
            completed_goals = []
            for goal in goals:
                if goal.status == "active":
                    # Update current amount
                    goal.current_amount = total_donations
                    
                    # Check if goal is completed
                    if total_donations >= goal.goal_amount:
                        goal.status = "completed"
                        goal.completed_at = datetime.now(timezone.utc)
                        completed_goals.append(goal)
                        
                        logger.info(f"Fundraising goal completed for {subreddit}: "
                                  f"${goal.goal_amount} (actual: ${total_donations})")
            
            if goals:
                self.session.commit()
                logger.info(f"Updated fundraising progress for {subreddit}: ${total_donations}")
            
            return completed_goals
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating fundraising progress: {str(e)}")
            raise

    def process_donation(self, donation: Donation) -> Dict[str, Any]:
        """
        Process a new donation and update related tiers and goals.
        
        Args:
            donation: The donation that was made
            
        Returns:
            Dict: Processing results
        """
        try:
            results = {
                "subreddit": donation.subreddit,
                "amount": donation.amount_usd,
                "completed_tiers": [],
                "completed_goals": [],
                "total_donations": Decimal('0')
            }
            
            if not donation.subreddit:
                return results
            
            # Update fundraising progress
            completed_goals = self.update_fundraising_progress(donation.subreddit)
            results["completed_goals"] = completed_goals
            
            # Check and update tiers
            completed_tiers = self.check_and_update_tiers(donation.subreddit)
            results["completed_tiers"] = completed_tiers
            
            # Get updated total
            results["total_donations"] = self.get_subreddit_total_donations(donation.subreddit)
            
            logger.info(f"Processed donation for {donation.subreddit}: "
                      f"${donation.amount_usd}, completed {len(completed_tiers)} tiers, "
                      f"{len(completed_goals)} goals")
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing donation: {str(e)}")
            raise

    def get_subreddit_stats(self, subreddit: str) -> Dict[str, Any]:
        """
        Get comprehensive stats for a subreddit.
        
        Args:
            subreddit: Subreddit name
            
        Returns:
            Dict: Subreddit statistics
        """
        try:
            total_donations = self.get_subreddit_total_donations(subreddit)
            tiers = self.get_subreddit_tiers(subreddit)
            goals = self.get_fundraising_goals(subreddit)
            
            # Count donors
            donor_count = (
                self.session.query(Donation)
                .filter(Donation.subreddit == subreddit)
                .filter(Donation.status == "succeeded")
                .distinct(Donation.customer_email)
                .count()
            )
            
            # Get active sponsors
            active_sponsors = (
                self.session.query(Sponsor)
                .join(Donation)
                .filter(Donation.subreddit == subreddit)
                .filter(Sponsor.status == "active")
                .filter(Donation.status == "succeeded")
                .count()
            )
            
            return {
                "subreddit": subreddit,
                "total_donations": float(total_donations),
                "donor_count": donor_count,
                "active_sponsors": active_sponsors,
                "tiers": [
                    {
                        "level": tier.tier_level,
                        "min_total_donation": float(tier.min_total_donation),
                        "status": tier.status,
                        "completed_at": tier.completed_at.isoformat() if tier.completed_at else None
                    }
                    for tier in tiers
                ],
                "goals": [
                    {
                        "goal_amount": float(goal.goal_amount),
                        "current_amount": float(goal.current_amount),
                        "progress_percentage": (float(goal.current_amount) / float(goal.goal_amount)) * 100,
                        "status": goal.status,
                        "deadline": goal.deadline.isoformat() if goal.deadline else None
                    }
                    for goal in goals
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting subreddit stats: {str(e)}")
            raise 