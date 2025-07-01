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

from app.db.models import Donation, SubredditFundraisingGoal
from app.subreddit_service import get_subreddit_service
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

    def get_subreddit_total_donations(self, subreddit_name: str) -> Decimal:
        """
        Get total donations for a subreddit, counting each donation only once.
        
        Args:
            subreddit_name: Subreddit name
            
        Returns:
            Decimal: Total donation amount
        """
        # Get or create subreddit entity
        subreddit_service = get_subreddit_service()
        subreddit = subreddit_service.get_or_create_subreddit(subreddit_name, self.session)
        
        # Query all succeeded donations for this subreddit (direct or via fundraising goal)
        donations = (
            self.session.query(Donation)
            .filter(Donation.subreddit_id == subreddit.id)
            .filter(Donation.status == "succeeded")
            .all()
        )
        # Use a set to ensure uniqueness by donation id
        unique_donations = {d.id: d for d in donations}.values()
        return sum(d.amount_usd for d in unique_donations) if unique_donations else Decimal('0')

    def get_subreddit_tiers(self, subreddit_name: str) -> List[Dict[str, Any]]:
        """
        Get all tiers for a subreddit (placeholder - subreddit tiers removed).
        
        Args:
            subreddit_name: Subreddit name
            
        Returns:
            List[Dict]: Empty list (subreddit tiers no longer supported)
        """
        return []

    def create_subreddit_tiers(self, subreddit_name: str, tier_levels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create subreddit tiers for a subreddit (placeholder - subreddit tiers removed).
        
        Args:
            subreddit_name: Subreddit name
            tier_levels: List of tier configurations with min_total_donation
            
        Returns:
            List[Dict]: Empty list (subreddit tiers no longer supported)
        """
        logger.warning(f"Subreddit tiers no longer supported - ignoring request for {subreddit_name}")
        return []

    def check_and_update_tiers(self, subreddit_name: str) -> List[Dict[str, Any]]:
        """
        Check if any subreddit tiers have been reached and update them (placeholder - subreddit tiers removed).
        
        Args:
            subreddit_name: Subreddit name
            
        Returns:
            List[Dict]: Empty list (subreddit tiers no longer supported)
        """
        logger.warning(f"Subreddit tiers no longer supported - ignoring request for {subreddit_name}")
        return []

    def get_fundraising_goals(self, subreddit_name: Optional[str] = None) -> List[SubredditFundraisingGoal]:
        """
        Get fundraising goals.
        
        Args:
            subreddit_name: Optional subreddit filter
            
        Returns:
            List[SubredditFundraisingGoal]: List of fundraising goals
        """
        query = self.session.query(SubredditFundraisingGoal)
        if subreddit_name:
            # Get or create subreddit entity
            subreddit_service = get_subreddit_service()
            subreddit = subreddit_service.get_or_create_subreddit(subreddit_name, self.session)
            query = query.filter(SubredditFundraisingGoal.subreddit_id == subreddit.id)
        return query.filter(SubredditFundraisingGoal.status == "active").all()

    def create_fundraising_goal(
        self, 
        subreddit_name: str, 
        goal_amount: Decimal, 
        deadline: Optional[datetime] = None
    ) -> SubredditFundraisingGoal:
        """
        Create a fundraising goal for a subreddit.
        
        Args:
            subreddit_name: Subreddit name
            goal_amount: Goal amount
            deadline: Optional deadline
            
        Returns:
            SubredditFundraisingGoal: Created fundraising goal
        """
        try:
            # Get or create subreddit entity
            subreddit_service = get_subreddit_service()
            subreddit = subreddit_service.get_or_create_subreddit(subreddit_name, self.session)
            
            goal = SubredditFundraisingGoal(
                subreddit_id=subreddit.id,
                goal_amount=goal_amount,
                current_amount=Decimal('0'),
                deadline=deadline,
                status="active"
            )
            
            self.session.add(goal)
            self.session.commit()
            
            logger.info(f"Created fundraising goal for {subreddit_name}: ${goal_amount}")
            return goal
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating fundraising goal: {str(e)}")
            raise

    def update_fundraising_progress(self, subreddit_name: str) -> List[SubredditFundraisingGoal]:
        """
        Update fundraising progress for a subreddit.
        
        Args:
            subreddit_name: Subreddit name
            
        Returns:
            List[SubredditFundraisingGoal]: List of completed goals
        """
        try:
            total_donations = self.get_subreddit_total_donations(subreddit_name)
            goals = self.get_fundraising_goals(subreddit_name)
            
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
                        
                        logger.info(f"Fundraising goal completed for {subreddit_name}: "
                                  f"${goal.goal_amount} (actual: ${total_donations})")
            
            if goals:
                self.session.commit()
                logger.info(f"Updated fundraising progress for {subreddit_name}: ${total_donations}")
            
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
            # Get subreddit name for results
            subreddit_name = donation.subreddit.subreddit_name if donation.subreddit else None
            
            results = {
                "subreddit": subreddit_name,
                "amount": donation.amount_usd,
                "completed_tiers": [],
                "completed_goals": [],
                "total_donations": Decimal('0')
            }
            
            if not subreddit_name:
                return results
            
            # Update fundraising progress
            completed_goals = self.update_fundraising_progress(subreddit_name)
            results["completed_goals"] = completed_goals
            
            # Check and update tiers
            completed_tiers = self.check_and_update_tiers(subreddit_name)
            results["completed_tiers"] = completed_tiers
            
            # Get updated total
            results["total_donations"] = self.get_subreddit_total_donations(subreddit_name)
            
            logger.info(f"Processed donation for {subreddit_name}: "
                      f"${donation.amount_usd}, completed {len(completed_tiers)} tiers, "
                      f"{len(completed_goals)} goals")
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing donation: {str(e)}")
            raise

    def get_subreddit_stats(self, subreddit_name: str) -> Dict[str, Any]:
        """
        Get comprehensive stats for a subreddit.
        
        Args:
            subreddit_name: Subreddit name
            
        Returns:
            Dict: Subreddit statistics
        """
        try:
            # Get or create subreddit entity
            subreddit_service = get_subreddit_service()
            subreddit = subreddit_service.get_or_create_subreddit(subreddit_name, self.session)
            
            total_donations = self.get_subreddit_total_donations(subreddit_name)
            tiers = self.get_subreddit_tiers(subreddit_name)
            goals = self.get_fundraising_goals(subreddit_name)
            
            # Count donors
            donor_count = (
                self.session.query(Donation)
                .filter(Donation.subreddit_id == subreddit.id)
                .filter(Donation.status == "succeeded")
                .distinct(Donation.customer_email)
                .count()
            )
            
            # Count active donations (sponsors no longer exist)
            active_donations = (
                self.session.query(Donation)
                .filter(Donation.subreddit_id == subreddit.id)
                .filter(Donation.status == "succeeded")
                .count()
            )
            
            return {
                "subreddit": subreddit_name,
                "total_donations": float(total_donations),
                "donor_count": donor_count,
                "active_donations": active_donations,
                "tiers": [],  # Subreddit tiers no longer supported
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

    def check_subreddit_tiers(self, subreddit_name: str) -> Dict[str, Any]:
        """
        Check subreddit tiers and fundraising goals for a subreddit.
        
        Args:
            subreddit_name: Subreddit name
            
        Returns:
            Dict: Tier and goal information
        """
        try:
            # Get or create subreddit entity
            subreddit_service = get_subreddit_service()
            subreddit = subreddit_service.get_or_create_subreddit(subreddit_name, self.session)
            
            total_donations = self.get_subreddit_total_donations(subreddit_name)
            tiers = self.get_subreddit_tiers(subreddit_name)
            goals = self.get_fundraising_goals(subreddit_name)
            
            return {
                "subreddit": subreddit_name,
                "total_donations": float(total_donations),
                "tiers": [],  # Subreddit tiers no longer supported
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
            logger.error(f"Error checking subreddit tiers: {str(e)}")
            raise 