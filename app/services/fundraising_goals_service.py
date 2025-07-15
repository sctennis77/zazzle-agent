"""
Service for managing fundraising goals and progress calculations.

This service handles:
- Overall fundraising goal progress calculation
- Subreddit-specific goal management
- Dynamic progress calculation from donations
- Goal configuration management
"""

import logging
from decimal import Decimal
from typing import List

from sqlalchemy import and_, func
from sqlalchemy.orm import Session, joinedload

from app.db.models import Donation, Subreddit, SubredditFundraisingGoal
from app.models import (
    FundraisingGoalsConfig,
    FundraisingProgress,
    SubredditFundraisingGoalSchema,
)

logger = logging.getLogger(__name__)


class FundraisingGoalsService:
    """Service for managing fundraising goals and progress."""

    def __init__(self, session: Session):
        self.session = session

    def get_config(self) -> FundraisingGoalsConfig:
        """Get fundraising goals configuration."""
        # For now, return default config. In the future, this could be
        # stored in database
        return FundraisingGoalsConfig()

    def calculate_overall_progress(self) -> Decimal:
        """Calculate total amount raised across all subreddits."""
        total = (
            self.session.query(func.coalesce(func.sum(Donation.amount_usd), 0))
            .filter(Donation.status == "succeeded")
            .scalar()
        )

        return Decimal(str(total or 0))

    def get_subreddit_goals_with_progress(
        self,
    ) -> List[SubredditFundraisingGoalSchema]:
        """Get all active subreddit goals with calculated progress."""
        goals = (
            self.session.query(SubredditFundraisingGoal)
            .options(joinedload(SubredditFundraisingGoal.subreddit))
            .filter(SubredditFundraisingGoal.status == "active")
            .all()
        )

        result = []
        for goal in goals:
            # Calculate current progress dynamically
            current_amount = (
                self.session.query(func.coalesce(func.sum(Donation.amount_usd), 0))
                .filter(
                    and_(
                        Donation.subreddit_id == goal.subreddit_id,
                        Donation.status == "succeeded",
                    )
                )
                .scalar()
            )

            result.append(
                SubredditFundraisingGoalSchema(
                    id=goal.id,
                    subreddit_id=goal.subreddit_id,
                    subreddit_name=goal.subreddit.subreddit_name,
                    goal_amount=goal.goal_amount,
                    current_amount=Decimal(str(current_amount or 0)),
                    status=goal.status,
                    created_at=goal.created_at,
                    completed_at=goal.completed_at,
                    deadline=goal.deadline,
                )
            )

        return result

    def ensure_subreddit_goals_exist(self) -> None:
        """Ensure all subreddits have active fundraising goals."""
        config = self.get_config()

        # Get all subreddits that don't have active goals
        subreddits_without_goals = (
            self.session.query(Subreddit)
            .filter(
                ~Subreddit.id.in_(
                    self.session.query(SubredditFundraisingGoal.subreddit_id).filter(
                        SubredditFundraisingGoal.status == "active"
                    )
                )
            )
            .all()
        )

        for subreddit in subreddits_without_goals:
            goal = SubredditFundraisingGoal(
                subreddit_id=subreddit.id,
                goal_amount=config.subreddit_goal_amount,
                status="active",
            )
            self.session.add(goal)
            logger.info(
                f"Created fundraising goal for {subreddit.subreddit_name}: "
                f"${config.subreddit_goal_amount}"
            )

        self.session.commit()

    def get_fundraising_progress(self) -> FundraisingProgress:
        """Get complete fundraising progress information."""
        config = self.get_config()

        # Ensure all subreddits have goals
        self.ensure_subreddit_goals_exist()

        # Calculate overall progress
        overall_raised = self.calculate_overall_progress()
        overall_progress_percentage = min(
            float(overall_raised / config.overall_goal_amount * 100), 100.0
        )

        # Get subreddit goals with progress
        subreddit_goals = self.get_subreddit_goals_with_progress()

        return FundraisingProgress(
            overall_raised=overall_raised,
            overall_goal=config.overall_goal_amount,
            overall_progress_percentage=overall_progress_percentage,
            overall_reward=config.overall_goal_reward,
            subreddit_goals=subreddit_goals,
            subreddit_goal_amount=config.subreddit_goal_amount,
            subreddit_goal_reward=config.subreddit_goal_reward,
        )

    def update_goal_completion_status(
        self,
    ) -> List[SubredditFundraisingGoalSchema]:
        """Check and update completion status for completed goals."""
        completed_goals = []

        goals = (
            self.session.query(SubredditFundraisingGoal)
            .filter(SubredditFundraisingGoal.status == "active")
            .all()
        )

        for goal in goals:
            # Calculate current progress
            current_amount = (
                self.session.query(func.coalesce(func.sum(Donation.amount_usd), 0))
                .filter(
                    and_(
                        Donation.subreddit_id == goal.subreddit_id,
                        Donation.status == "succeeded",
                    )
                )
                .scalar()
            )

            current_amount = Decimal(str(current_amount or 0))

            # Check if goal is completed
            if current_amount >= goal.goal_amount:
                goal.status = "completed"
                goal.completed_at = func.now()
                goal.current_amount = current_amount

                subreddit = self.session.query(Subreddit).get(goal.subreddit_id)
                completed_goals.append(
                    SubredditFundraisingGoalSchema(
                        id=goal.id,
                        subreddit_id=goal.subreddit_id,
                        subreddit_name=subreddit.subreddit_name,
                        goal_amount=goal.goal_amount,
                        current_amount=current_amount,
                        status=goal.status,
                        created_at=goal.created_at,
                        completed_at=goal.completed_at,
                        deadline=goal.deadline,
                    )
                )

                logger.info(
                    f"Fundraising goal completed for "
                    f"{subreddit.subreddit_name}: ${current_amount}"
                )

        self.session.commit()
        return completed_goals
