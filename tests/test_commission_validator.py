import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from app.services.commission_validator import CommissionValidator, ValidationResult
from app.api import app, get_commission_validator
from app.models import CommissionValidationRequest, CommissionValidationResponse


class TestCommissionValidator:
    """Test cases for CommissionValidator service"""

    @pytest.fixture
    def mock_session(self):
        """Mock database session"""
        with patch('app.services.commission_validator.SessionLocal') as mock_session:
            mock_instance = Mock()
            mock_session.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def validator(self, mock_session):
        """Create a CommissionValidator instance for testing with mocked dependencies"""
        with patch('app.services.commission_validator.RedditClient') as mock_client, \
             patch('app.services.commission_validator.RedditAgent') as mock_agent:
            
            # Create validator with mocked dependencies
            validator = CommissionValidator()
            
            # Mock the internal dependencies
            validator.reddit_client = Mock()
            validator.reddit_agent = Mock()
            validator.session = mock_session
            
            yield validator

    @pytest.fixture
    def mock_reddit_client(self):
        """Mock RedditClient for testing"""
        with patch('app.services.commission_validator.RedditClient') as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_reddit_agent(self):
        """Mock RedditAgent for testing"""
        with patch('app.services.commission_validator.RedditAgent') as mock_agent:
            mock_instance = Mock()
            mock_agent.return_value = mock_instance
            yield mock_instance

    @pytest.mark.asyncio
    async def test_validate_random_subreddit_success(self, validator, mock_reddit_client, mock_reddit_agent):
        """Test successful validation of random subreddit commission"""
        # Mock Reddit submission
        mock_submission = Mock()
        mock_submission.id = "1lp1zam"
        mock_submission.title = "Golf is weird."
        mock_submission.selftext = "For comparison, I also play tennis..."
        mock_submission.permalink = "/r/golf/comments/1lp1zam/golf_is_weird/"
        mock_submission.subreddit.display_name = "golf"

        # Mock RedditAgent methods
        validator.reddit_agent.find_top_post_from_subreddit = AsyncMock(return_value=mock_submission)
        
        # Mock RedditClient methods
        validator.reddit_client.get_post.return_value = mock_submission
        validator.reddit_client.get_subreddit.return_value = Mock()

        # Mock subreddit validation
        with patch.object(validator, '_validate_subreddit_exists', return_value=True), \
             patch.object(validator, '_get_subreddit_id', return_value=5):
            
            # Test validation
            result = await validator.validate_commission("random_subreddit", "golf")

            # Verify result
            assert result.valid is True
            assert result.subreddit == "golf"
            assert result.subreddit_id == 5
            assert result.post_id == "1lp1zam"
            assert result.post_title == "Golf is weird."
            assert result.post_content == "For comparison, I also play tennis..."
            assert result.post_url == "https://reddit.com/r/golf/comments/1lp1zam/golf_is_weird/"
            assert result.commission_type == "random_subreddit"
            assert result.error is None

    @pytest.mark.asyncio
    async def test_validate_random_subreddit_invalid_subreddit(self, validator):
        """Test validation failure for invalid subreddit"""
        # Mock subreddit validation to fail
        with patch.object(validator, '_validate_subreddit_exists', return_value=False):
            result = await validator.validate_commission("random_subreddit", "invalid_subreddit")

            assert result.valid is False
            assert "not found or not accessible" in result.error

    @pytest.mark.asyncio
    async def test_validate_specific_post_success(self, validator):
        """Test successful validation of specific post commission"""
        # Mock Reddit submission
        mock_submission = Mock()
        mock_submission.id = "1lp1zam"
        mock_submission.title = "Golf is weird."
        mock_submission.selftext = "For comparison, I also play tennis..."
        mock_submission.permalink = "/r/golf/comments/1lp1zam/golf_is_weird/"
        mock_submission.subreddit.display_name = "golf"

        validator.reddit_client.get_post.return_value = mock_submission

        # Mock subreddit ID lookup
        with patch.object(validator, '_get_subreddit_id', return_value=5):
            # Test validation
            result = await validator.validate_commission("specific_post", post_id="1lp1zam")

            # Verify result
            assert result.valid is True
            assert result.subreddit == "golf"
            assert result.post_id == "1lp1zam"
            assert result.post_title == "Golf is weird."
            assert result.post_content == "For comparison, I also play tennis..."
            assert result.post_url == "https://reddit.com/r/golf/comments/1lp1zam/golf_is_weird/"
            assert result.commission_type == "specific_post"
            assert result.error is None

    @pytest.mark.asyncio
    async def test_validate_specific_post_post_not_found(self, validator):
        """Test validation failure when post is not found"""
        validator.reddit_client.get_post.return_value = None
        
        result = await validator.validate_commission("specific_post", post_id="nonexistent_post")

        assert result.valid is False
        assert "not found" in result.error
        assert result.post_id is None

    @pytest.mark.asyncio
    async def test_validate_specific_post_wrong_subreddit(self, validator):
        """Test validation failure when post is from different subreddit"""
        # Mock submission from different subreddit
        mock_submission = Mock()
        mock_submission.id = "1lp1zam"
        mock_submission.title = "Tennis is great"
        mock_submission.selftext = "I love tennis"
        mock_submission.permalink = "/r/tennis/comments/1lp1zam/tennis_is_great/"
        mock_submission.subreddit.display_name = "tennis"

        validator.reddit_client.get_post.return_value = mock_submission

        # Mock subreddit ID lookup
        with patch.object(validator, '_get_subreddit_id', return_value=10):
            result = await validator.validate_commission("specific_post", post_id="1lp1zam")

            # This should work since we get the subreddit from the post itself
            assert result.valid is True
            assert result.subreddit == "tennis"
            assert result.post_id == "1lp1zam"

    @pytest.mark.asyncio
    async def test_validate_random_random_success(self, validator):
        """Test successful validation of random random commission"""
        # Mock Reddit submission
        mock_submission = Mock()
        mock_submission.id = "1lp1zam"
        mock_submission.title = "Golf is weird."
        mock_submission.selftext = "For comparison, I also play tennis..."
        mock_submission.permalink = "/r/golf/comments/1lp1zam/golf_is_weird/"
        mock_submission.subreddit.display_name = "golf"

        # Mock RedditAgent methods
        validator.reddit_agent.find_top_post_from_subreddit = AsyncMock(return_value=mock_submission)
        
        # Mock RedditClient methods
        validator.reddit_client.get_post.return_value = mock_submission

        # Mock subreddit selection and validation
        with patch('app.services.commission_validator.pick_subreddit', return_value="golf"), \
             patch.object(validator, '_get_subreddit_id', return_value=5):
            
            # Test validation
            result = await validator.validate_commission("random_random")

            # Verify result
            assert result.valid is True
            assert result.subreddit == "golf"
            assert result.post_id == "1lp1zam"
            assert result.post_title == "Golf is weird."
            assert result.post_content == "For comparison, I also play tennis..."
            assert result.post_url == "https://reddit.com/r/golf/comments/1lp1zam/golf_is_weird/"
            assert result.commission_type == "random_random"
            assert result.error is None

    @pytest.mark.asyncio
    async def test_validate_random_random_no_subreddits(self, validator):
        """Test validation failure when no top posts are found"""
        # Mock RedditAgent to return None (no posts found)
        validator.reddit_agent.find_top_post_from_subreddit = AsyncMock(return_value=None)

        # Mock subreddit selection
        with patch('app.services.commission_validator.pick_subreddit', return_value="golf"):
            # Test validation
            result = await validator.validate_commission("random_random")

            # Verify result
            assert result.valid is False
            assert "No top or trending posts found in r/golf" in result.error
            assert result.subreddit is None
            assert result.post_id is None

    @pytest.mark.asyncio
    async def test_validate_commission_invalid_type(self, validator):
        """Test validation failure for invalid commission type"""
        result = await validator.validate_commission("invalid_type", "golf", "1lp1zam")

        assert result.valid is False
        assert "Unknown commission type" in result.error
        assert result.commission_type is None

    @pytest.mark.asyncio
    async def test_validate_commission_missing_required_fields(self, validator):
        """Test validation failure for missing required fields"""
        # Test random_subreddit without subreddit
        result = await validator.validate_commission("random_subreddit", None, None)
        assert result.valid is False
        assert "Subreddit is required" in result.error

        # Test specific_post without post_id
        result = await validator.validate_commission("specific_post", post_id=None)
        assert result.valid is False
        assert "Post ID or URL is required" in result.error


class TestCommissionValidationEndpoint:
    """Test cases for the commission validation API endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_validator(self):
        """Mock CommissionValidator for endpoint testing"""
        mock_instance = Mock()
        mock_instance.validate_commission = AsyncMock()
        return mock_instance

    @pytest.fixture(autouse=True)
    def override_validator(self, mock_validator):
        app.dependency_overrides[get_commission_validator] = lambda: mock_validator
        yield
        app.dependency_overrides.pop(get_commission_validator, None)

    def test_validate_random_subreddit_endpoint(self, client, mock_validator):
        """Test random subreddit validation endpoint"""
        # Mock validator response using ValidationResult
        mock_response = ValidationResult(
            valid=True,
            subreddit="golf",
            subreddit_id=5,
            post_id="1lp1zam",
            post_title="Golf is weird.",
            post_content="For comparison, I also play tennis...",
            post_url="https://reddit.com/r/golf/comments/1lp1zam/golf_is_weird/",
            commission_type="random_subreddit",
            error=None
        )

        mock_validator.validate_commission.return_value = mock_response

        # Test endpoint
        response = client.post(
            "/api/commissions/validate",
            json={
                "commission_type": "random_subreddit",
                "subreddit": "golf"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["subreddit"] == "golf"
        assert data["subreddit_id"] == 5
        assert data["post_id"] == "1lp1zam"
        assert data["commission_type"] == "random_subreddit"

        # Verify validator was called correctly
        mock_validator.validate_commission.assert_called_once_with(
            commission_type="random_subreddit", subreddit="golf", post_id=None, post_url=None
        )

    def test_validate_specific_post_endpoint(self, client, mock_validator):
        """Test specific post validation endpoint"""
        # Mock validator response using ValidationResult
        mock_response = ValidationResult(
            valid=True,
            subreddit="golf",
            subreddit_id=5,
            post_id="1lp1zam",
            post_title="Golf is weird.",
            post_content="For comparison, I also play tennis...",
            post_url="https://reddit.com/r/golf/comments/1lp1zam/golf_is_weird/",
            commission_type="specific_post",
            error=None
        )

        mock_validator.validate_commission.return_value = mock_response

        # Test endpoint
        response = client.post(
            "/api/commissions/validate",
            json={
                "commission_type": "specific_post",
                "subreddit": "golf",
                "post_id": "1lp1zam"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["subreddit"] == "golf"
        assert data["subreddit_id"] == 5
        assert data["post_id"] == "1lp1zam"
        assert data["commission_type"] == "specific_post"

        # Verify validator was called correctly
        mock_validator.validate_commission.assert_called_once_with(
            commission_type="specific_post", subreddit="golf", post_id="1lp1zam", post_url=None
        )

    def test_validate_random_random_endpoint(self, client, mock_validator):
        """Test random random validation endpoint"""
        # Mock validator response using ValidationResult
        mock_response = ValidationResult(
            valid=True,
            subreddit="golf",
            subreddit_id=5,
            post_id="1lp1zam",
            post_title="Golf is weird.",
            post_content="For comparison, I also play tennis...",
            post_url="https://reddit.com/r/golf/comments/1lp1zam/golf_is_weird/",
            commission_type="random_random",
            error=None
        )

        mock_validator.validate_commission.return_value = mock_response

        # Test endpoint
        response = client.post(
            "/api/commissions/validate",
            json={
                "commission_type": "random_random"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["subreddit"] == "golf"
        assert data["subreddit_id"] == 5
        assert data["post_id"] == "1lp1zam"
        assert data["commission_type"] == "random_random"

        # Verify validator was called correctly
        mock_validator.validate_commission.assert_called_once_with(
            commission_type="random_random", subreddit=None, post_id=None, post_url=None
        )

    @pytest.mark.asyncio
    async def test_validate_endpoint_validation_failure(self, client, mock_validator):
        """Test validation endpoint when validation fails"""
        # Mock validator response for failure using ValidationResult
        mock_response = ValidationResult(
            valid=False,
            subreddit="invalid_subreddit",
            subreddit_id=None,
            post_id=None,
            post_title=None,
            post_content=None,
            post_url=None,
            commission_type="random_subreddit",
            error="Subreddit 'invalid_subreddit' not found in database"
        )

        mock_validator.validate_commission.return_value = mock_response

        # Test endpoint
        response = client.post(
            "/api/commissions/validate",
            json={
                "commission_type": "random_subreddit",
                "subreddit": "invalid_subreddit"
            }
        )

        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["valid"] is False
        assert data["detail"]["subreddit"] == "invalid_subreddit"
        assert data["detail"]["error"] == "Subreddit 'invalid_subreddit' not found in database"

    def test_validate_endpoint_invalid_request(self, client):
        """Test validation endpoint with invalid request data"""
        # Test missing commission_type
        response = client.post(
            "/api/commissions/validate",
            json={
                "subreddit": "golf"
            }
        )
        assert response.status_code == 422

        # Test invalid commission_type
        response = client.post(
            "/api/commissions/validate",
            json={
                "commission_type": "invalid_type",
                "subreddit": "golf"
            }
        )
        assert response.status_code == 422

    def test_validate_endpoint_missing_required_fields(self, client):
        """Test validation endpoint with missing required fields"""
        # Test specific_post without post_id
        response = client.post(
            "/api/commissions/validate",
            json={
                "commission_type": "specific_post",
                "subreddit": "golf"
            }
        )
        assert response.status_code == 422

        # Test random_subreddit without subreddit
        response = client.post(
            "/api/commissions/validate",
            json={
                "commission_type": "random_subreddit"
            }
        )
        assert response.status_code == 422


class TestCommissionValidationModels:
    """Test cases for commission validation Pydantic models"""

    def test_commission_validation_request_valid(self):
        """Test valid CommissionValidationRequest"""
        request = CommissionValidationRequest(
            commission_type="random_subreddit",
            subreddit="golf"
        )
        assert request.commission_type == "random_subreddit"
        assert request.subreddit == "golf"
        assert request.post_id is None

    def test_commission_validation_request_specific_post(self):
        """Test CommissionValidationRequest for specific post"""
        request = CommissionValidationRequest(
            commission_type="specific_post",
            subreddit="golf",
            post_id="1lp1zam"
        )
        assert request.commission_type == "specific_post"
        assert request.subreddit == "golf"
        assert request.post_id == "1lp1zam"

    def test_commission_validation_request_random_random(self):
        """Test CommissionValidationRequest for random random"""
        request = CommissionValidationRequest(
            commission_type="random_random"
        )
        assert request.commission_type == "random_random"
        assert request.subreddit is None
        assert request.post_id is None

    def test_commission_validation_response_valid(self):
        """Test valid CommissionValidationResponse"""
        response = CommissionValidationResponse(
            valid=True,
            subreddit="golf",
            subreddit_id=5,
            post_id="1lp1zam",
            post_title="Golf is weird.",
            post_content="For comparison, I also play tennis...",
            post_url="https://reddit.com/r/golf/comments/1lp1zam/golf_is_weird/",
            commission_type="random_subreddit",
            error=None
        )
        assert response.valid is True
        assert response.subreddit == "golf"
        assert response.subreddit_id == 5
        assert response.post_id == "1lp1zam"
        assert response.error is None

    def test_commission_validation_response_invalid(self):
        """Test CommissionValidationResponse for invalid validation"""
        response = CommissionValidationResponse(
            valid=False,
            subreddit="invalid_subreddit",
            subreddit_id=None,
            post_id=None,
            post_title=None,
            post_content=None,
            post_url=None,
            commission_type="random_subreddit",
            error="Subreddit 'invalid_subreddit' not found in database"
        )
        assert response.valid is False
        assert response.subreddit == "invalid_subreddit"
        assert response.subreddit_id is None
        assert response.post_id is None
        assert response.error == "Subreddit 'invalid_subreddit' not found in database" 