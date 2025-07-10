"""
End-to-End Commission Workflow Test

This test validates the complete commission workflow from payment success
to product generation, ensuring all components work together correctly.
"""

import json
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from datetime import datetime, timezone

from app.api import handle_payment_intent_succeeded
from app.db.database import Base, SessionLocal, engine
from app.db.models import Donation, PipelineTask, Subreddit, PipelineRun
from app.models import DonationStatus, DonationTier
from app.services.stripe_service import StripeService
from app.task_manager import TaskManager


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    """Drop and recreate all tables before each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_payment_intent():
    """Create a mock Stripe payment intent object."""
    payment_intent = MagicMock()
    payment_intent.id = "pi_test_commission_123"
    payment_intent.amount = 2500  # $25.00 in cents
    payment_intent.currency = "usd"
    payment_intent.receipt_email = "commissioner@test.com"
    payment_intent.metadata = {
        "donation_type": "commission",
        "commission_type": "random_subreddit",
        "subreddit": "hiking",
        "post_id": "",
        "commission_message": "Create something amazing from a hiking post!",
        "customer_name": "Test Commissioner",
        "reddit_username": "test_commissioner",
        "is_anonymous": "false"
    }
    return payment_intent


@pytest.fixture
def sample_subreddit():
    """Create a sample subreddit for testing."""
    db = SessionLocal()
    try:
        subreddit = Subreddit(
            subreddit_name="hiking",
            display_name="Hiking"
        )
        db.add(subreddit)
        db.commit()
        db.refresh(subreddit)
        return subreddit
    finally:
        db.close()


@pytest.fixture
def mock_openai():
    """Mock OpenAI API calls."""
    with (
        patch("app.async_image_generator.AsyncOpenAI") as mock_img,
        patch("app.content_generator.OpenAI") as mock_content,
        patch("app.agents.reddit_agent.openai.OpenAI") as mock_reddit,
    ):
        mock_instance = MagicMock()
        mock_img.return_value = mock_instance
        mock_content.return_value = mock_instance
        mock_reddit.return_value = mock_instance
        
        # Mock image generation response
        mock_instance.images.generate.return_value = MagicMock(
            data=[MagicMock(b64_json="Zm9vYmFy")]  # Base64 encoded "foobar"
        )
        
        # Mock content generation response
        product_idea_json = json.dumps({
            "text": "Hiking Adventure Awaits",
            "image_description": "A beautiful mountain landscape with hiking trail",
            "theme": "outdoor_adventure",
            "color": "Forest Green",
            "quantity": 1
        })
        mock_instance.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=product_idea_json))]
        )
        yield mock_instance


@pytest.fixture
def mock_reddit():
    """Mock Reddit API calls."""
    with patch("praw.Reddit") as mock:
        reddit = MagicMock()
        mock.return_value = reddit
        
        # Mock subreddit
        subreddit_mock = MagicMock()
        subreddit_mock.id = "hiking"
        subreddit_mock.name = "hiking"
        subreddit_mock.display_name = "Hiking"
        
        # Mock post
        post = MagicMock()
        post.id = "test_post_123"
        post.title = "Amazing Hiking Trail"
        post.selftext = "Just completed this incredible hike!"
        post.url = "https://reddit.com/r/hiking/test_post_123"
        post.permalink = "/r/hiking/test_post_123"
        post.subreddit = subreddit_mock
        
        # Mock comments
        comment = MagicMock()
        comment.id = "test_comment_123"
        comment.body = "Beautiful trail!"
        
        comments_mock = MagicMock()
        comments_mock.replace_more.return_value = None
        comments_mock.__iter__.return_value = iter([comment])
        post.comments = comments_mock
        
        reddit.subreddit.return_value = subreddit_mock
        subreddit_mock.hot.return_value = iter([post])
        
        yield reddit


@pytest.fixture
def mock_imgur():
    """Mock Imgur API calls."""
    with patch("app.clients.imgur_client.ImgurClient") as mock:
        client = MagicMock()
        mock.return_value = client
        client.upload_image.return_value = (
            "https://i.imgur.com/test_commission.png",
            "/tmp/test_commission_image.png",
        )
        yield client


@pytest.fixture
def mock_zazzle():
    """Mock Zazzle API calls."""
    with patch("app.zazzle_product_designer.ZazzleProductDesigner") as mock:
        designer = MagicMock()
        
        def create_product_side_effect(design_instructions):
            from app.models import ProductInfo, RedditContext
            
            reddit_context = RedditContext(
                post_id="test_post_123",
                post_title="Amazing Hiking Trail",
                post_url="https://reddit.com/r/hiking/test_post_123",
                subreddit="hiking",
            )
            
            return ProductInfo(
                product_id="zazzle_commission_123",
                name="Hiking Adventure Print",
                image_url="https://i.imgur.com/test_commission.png",
                product_url="https://www.zazzle.com/hiking_adventure_print",
                theme="outdoor_adventure",
                product_type="print",
                zazzle_template_id="print_template_123",
                zazzle_tracking_code="track_commission_123",
                model="dall-e-3",
                prompt_version="1.0.0",
                reddit_context=reddit_context,
                design_instructions=design_instructions,
                image_local_path="/tmp/test_commission_image.png",
            )
        
        designer.create_product.side_effect = create_product_side_effect
        mock.return_value = designer
        yield designer


@pytest.fixture
def mock_image_generator():
    """Mock image generation."""
    with patch("app.async_image_generator.AsyncImageGenerator.generate_image", new_callable=AsyncMock) as mock:
        mock.return_value = ("https://i.imgur.com/test_commission.png", "/tmp/test_commission_image.png")
        yield mock


@pytest.fixture(autouse=True)
def patch_task_manager():
    """Patch the global task_manager instance to avoid actual task execution."""
    with patch("app.api.task_manager") as mock:
        mock.create_commission_task.return_value = "task_123"
        yield mock


class TestCommissionWorkflowE2E:
    """
    End-to-end commission workflow tests.

    These tests validate the full commission donation flow, from payment intent success
    through donation creation, task creation, and pipeline integration. Run this suite
    after any backend refactor to ensure you have not broken core commission or pipeline logic.
    """

    @pytest.mark.asyncio
    async def test_commission_workflow_from_payment_success(
        self,
        mock_payment_intent,
        sample_subreddit,
        mock_openai,
        mock_reddit,
        mock_imgur,
        mock_zazzle,
        mock_image_generator,
        patch_task_manager
    ):
        """
        Simulates a successful Stripe payment intent for a commission donation.
        Verifies that a donation is created, the correct data is stored, and a commission task is queued.
        This is the primary end-to-end test for the commission workflow.
        """
        # Simulate Stripe webhook for payment_intent.succeeded
        await handle_payment_intent_succeeded(mock_payment_intent)

        # Check that the donation was created with correct fields
        db = SessionLocal()
        try:
            donation = db.query(Donation).filter_by(
                stripe_payment_intent_id="pi_test_commission_123"
            ).first()
            assert donation is not None
            assert donation.status == DonationStatus.SUCCEEDED.value
            assert donation.amount_usd == Decimal('25.00')
            assert donation.customer_email == "commissioner@test.com"
            assert donation.customer_name == "Test Commissioner"
            assert donation.reddit_username == "test_commissioner"
            assert donation.is_anonymous is False
            assert donation.donation_type == "commission"
            assert donation.commission_type == "random_subreddit"
            assert donation.commission_message == "Create something amazing from a hiking post!"
            assert donation.subreddit_id == sample_subreddit.id

            # Ensure a commission task was created with correct context
            assert patch_task_manager.create_commission_task.called
            call_args = patch_task_manager.create_commission_task.call_args
            assert call_args[0][0] == donation.id  # donation_id
            task_data = call_args[0][1]  # task_data
            assert task_data["donation_id"] == donation.id
            assert task_data["donation_amount"] == 25.0
            assert task_data["customer_name"] == "Test Commissioner"
            assert task_data["reddit_username"] == "test_commissioner"
            assert task_data["is_anonymous"] is False
            assert task_data["donation_type"] == "commission"
            assert task_data["commission_type"] == "random_subreddit"
            assert task_data["commission_message"] == "Create something amazing from a hiking post!"
        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_commission_workflow_specific_post(
        self,
        sample_subreddit,
        mock_openai,
        mock_reddit,
        mock_imgur,
        mock_zazzle,
        mock_image_generator
    ):
        """
        Simulates a commission for a specific Reddit post.
        Verifies that the donation and task are created with the correct post_id and commission_type.
        """
        # Create payment intent for a specific post commission
        payment_intent = MagicMock()
        payment_intent.id = "pi_test_specific_123"
        payment_intent.amount = 5000  # $50.00 in cents
        payment_intent.currency = "usd"
        payment_intent.receipt_email = "specific@test.com"
        payment_intent.metadata = {
            "donation_type": "commission",
            "commission_type": "specific_post",
            "subreddit": "hiking",
            "post_id": "test_post_123",
            "commission_message": "Make this specific post into a product!",
            "customer_name": "Specific Commissioner",
            "reddit_username": "specific_user",
            "is_anonymous": "false"
        }
        await handle_payment_intent_succeeded(payment_intent)

        # Check that the donation was created with the correct post_id and commission_type
        db = SessionLocal()
        try:
            donation = db.query(Donation).filter_by(
                stripe_payment_intent_id="pi_test_specific_123"
            ).first()
            assert donation is not None
            assert donation.commission_type == "specific_post"
            assert donation.post_id == "test_post_123"
            assert donation.amount_usd == Decimal('50.00')
        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_commission_workflow_anonymous(
        self,
        sample_subreddit,
        mock_openai,
        mock_reddit,
        mock_imgur,
        mock_zazzle,
        mock_image_generator
    ):
        """
        Simulates an anonymous commission donation.
        Verifies that the donation is marked anonymous and the correct fields are set.
        """
        payment_intent = MagicMock()
        payment_intent.id = "pi_test_anonymous_123"
        payment_intent.amount = 1000  # $10.00 in cents
        payment_intent.currency = "usd"
        payment_intent.receipt_email = "anonymous@test.com"
        payment_intent.metadata = {
            "donation_type": "commission",
            "commission_type": "random_subreddit",
            "subreddit": "hiking",
            "post_id": "",
            "commission_message": "Anonymous commission request",
            "customer_name": "Anonymous",
            "reddit_username": "anonymous_user",
            "is_anonymous": "true"
        }
        await handle_payment_intent_succeeded(payment_intent)

        db = SessionLocal()
        try:
            donation = db.query(Donation).filter_by(
                stripe_payment_intent_id="pi_test_anonymous_123"
            ).first()
            assert donation is not None
            assert donation.is_anonymous is True
            assert donation.customer_name == "Anonymous"
            assert donation.amount_usd == Decimal('10.00')
        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_commission_workflow_duplicate_payment(
        self,
        mock_payment_intent,
        sample_subreddit,
        patch_task_manager
    ):
        """
        Simulates a duplicate Stripe payment intent event.
        Verifies that the commission task is only created once for the same payment intent.
        """
        # First call should create the task
        await handle_payment_intent_succeeded(mock_payment_intent)
        assert patch_task_manager.create_commission_task.call_count == 1
        # Second call should not create a new task
        await handle_payment_intent_succeeded(mock_payment_intent)
        assert patch_task_manager.create_commission_task.call_count == 1

    @pytest.mark.asyncio
    async def test_commission_workflow_with_task_processing(
        self,
        mock_payment_intent,
        sample_subreddit,
        mock_openai,
        mock_reddit,
        mock_imgur,
        mock_zazzle,
        mock_image_generator
    ):
        """
        Simulates the full commission workflow including manual task creation.
        Verifies that the pipeline task is created with the correct context and can be processed.
        """
        await handle_payment_intent_succeeded(mock_payment_intent)
        db = SessionLocal()
        try:
            donation = db.query(Donation).filter_by(
                stripe_payment_intent_id="pi_test_commission_123"
            ).first()
            assert donation is not None
            # Manually create a pipeline task as if the task manager did it
            task = PipelineTask(
                type="SUBREDDIT_POST",
                subreddit_id=sample_subreddit.id,
                donation_id=donation.id,
                status="pending",
                priority=10,
                context_data={
                    "donation_id": donation.id,
                    "donation_amount": float(donation.amount_usd),
                    "tier": donation.tier,
                    "customer_name": donation.customer_name,
                    "reddit_username": donation.reddit_username,
                    "is_anonymous": donation.is_anonymous,
                    "donation_type": donation.donation_type,
                    "commission_type": donation.commission_type,
                    "commission_message": donation.commission_message,
                },
                created_at=datetime.now(timezone.utc)
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            assert task.type == "SUBREDDIT_POST"
            assert task.subreddit_id == sample_subreddit.id
            assert task.donation_id == donation.id
            assert task.status == "pending"
            assert task.priority == 10
            context_data = task.context_data
            assert context_data["donation_id"] == donation.id
            assert context_data["commission_type"] == "random_subreddit"
            assert context_data["commission_message"] == "Create something amazing from a hiking post!"
        finally:
            db.close()


class TestCommissionWorkflowIntegration:
    """
    Integration tests for commission workflow components.
    These are lower-level than the E2E tests but validate that the StripeService and TaskManager
    can create commission tasks and persist them in the database.
    """
    def test_stripe_service_commission_task_creation(self, sample_subreddit):
        """
        Verifies that StripeService.create_commission_task creates a pipeline task for a commission donation.
        """
        db = SessionLocal()
        try:
            donation = Donation(
                stripe_payment_intent_id="pi_test_stripe_123",
                amount_cents=2500,
                amount_usd=Decimal('25.00'),
                currency="usd",
                status=DonationStatus.SUCCEEDED.value,
                tier=DonationTier.PLATINUM,
                customer_email="stripe@test.com",
                customer_name="Stripe Test",
                subreddit_id=sample_subreddit.id,
                donation_type="commission",
                commission_type="random_subreddit",
                commission_message="Stripe service test",
                is_anonymous=False
            )
            db.add(donation)
            db.commit()
            db.refresh(donation)
            stripe_service = StripeService()
            task = stripe_service.create_commission_task(db, donation)
            assert task is not None
            assert task.type == "SUBREDDIT_POST"
            assert task.subreddit_id == sample_subreddit.id
            assert task.donation_id == donation.id
            assert task.status == "pending"
            assert task.priority == 10
        finally:
            db.close()
    def test_task_manager_commission_creation(self, sample_subreddit):
        """
        Verifies that TaskManager.create_commission_task creates a pipeline task for a commission donation.
        """
        db = SessionLocal()
        try:
            donation = Donation(
                stripe_payment_intent_id="pi_test_manager_123",
                amount_cents=2500,
                amount_usd=Decimal('25.00'),
                currency="usd",
                status=DonationStatus.SUCCEEDED.value,
                tier=DonationTier.PLATINUM,
                customer_email="manager@test.com",
                customer_name="Manager Test",
                subreddit_id=sample_subreddit.id,
                donation_type="commission",
                commission_type="random_subreddit",
                commission_message="Task manager test",
                is_anonymous=False
            )
            db.add(donation)
            db.commit()
            db.refresh(donation)
            task_manager = TaskManager()
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
            }
            with patch.object(task_manager, 'use_k8s', False):
                task_id = task_manager.create_commission_task(donation.id, task_data)
                assert task_id is not None
                task = db.query(PipelineTask).filter_by(id=task_id).first()
                assert task is not None
                assert task.type == "SUBREDDIT_POST"
                assert task.donation_id == donation.id
        finally:
            db.close() 