import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.modules.request.command.request import RequestCommand
from src.modules.session.session import Session
from src.modules.session.session_store import SessionStore
from src.modules.logging.plain import PlainLogger

@pytest.fixture
def logger():
    return PlainLogger()

@pytest.fixture
def session_store():
    return SessionStore()

@pytest.fixture
def session():
    session = MagicMock(spec=Session)
    session.base_url = "http://api.example.com"
    session.is_authenticated = MagicMock(return_value=True)
    session.get_headers = MagicMock(return_value={"Authorization": "Bearer test-token"})
    return session

class TestRequestCommand:
    """Test cases for RequestCommand class."""

    def test_init_with_default_config(self, logger, session_store):
        """Test initialization with default configuration."""
        command = RequestCommand(logger, session_store)
        assert command.timeout == 30
        assert command.verify_ssl is True
        assert command.max_retries == 3
        assert command.backoff_factor == 0.5
        assert command.max_delay is None

    def test_init_with_custom_config(self, logger, session_store):
        """Test initialization with custom configuration."""
        command = RequestCommand(
            logger=logger,
            session_store=session_store,
            timeout=60,
            verify_ssl=False,
            max_retries=5,
            backoff_factor=1.0,
            max_delay=10
        )
        assert command.timeout == 60
        assert command.verify_ssl is False
        assert command.max_retries == 5
        assert command.backoff_factor == 1.0
        assert command.max_delay == 10

    @pytest.mark.asyncio
    async def test_execute_request_with_retry(self, logger, session_store, session):
        """Test request execution with retry configuration."""
        # Create mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock()
        mock_response.json = AsyncMock(return_value={"status": "success"})

        # Create mock session
        mock_aiohttp_session = AsyncMock()
        mock_aiohttp_session.request = AsyncMock(return_value=mock_response)

        command = RequestCommand(
            logger=logger,
            session_store=session_store,
            max_retries=2,
            backoff_factor=0.5,
            max_delay=3
        )

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            response = await command.execute_request(
                session=session,
                method="GET",
                endpoint="/test",
                headers={"X-Custom-Header": "test"}
            )
            assert response.status == 200
            mock_aiohttp_session.request.assert_called_once_with(
                method="GET",
                url="http://api.example.com/test",
                json=None,
                params=None,
                headers={
                    "Authorization": "Bearer test-token",
                    "X-Custom-Header": "test"
                },
                ssl=True
            )

    @pytest.mark.asyncio
    async def test_execute_request_with_retry_on_failure(self, logger, session_store, session):
        """Test request execution with retry on failure."""
        # Create mock responses
        mock_response_fail = AsyncMock()
        mock_response_fail.status = 500
        mock_response_fail.read = AsyncMock()

        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        mock_response_success.read = AsyncMock()
        mock_response_success.json = AsyncMock(return_value={"status": "success"})

        # Create mock session with side effect
        mock_aiohttp_session = AsyncMock()
        mock_aiohttp_session.request = AsyncMock(side_effect=[
            mock_response_fail,
            mock_response_success
        ])

        command = RequestCommand(
            logger=logger,
            session_store=session_store,
            max_retries=1,
            backoff_factor=0.1  # Short delay for testing
        )

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            response = await command.execute_request(
                session=session,
                method="GET",
                endpoint="/test"
            )
            assert response.status == 200
            assert mock_aiohttp_session.request.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_request_with_max_delay(self, logger, session_store, session):
        """Test request execution with max delay configuration."""
        # Create mock responses
        mock_response_fail = AsyncMock()
        mock_response_fail.status = 500
        mock_response_fail.read = AsyncMock()

        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        mock_response_success.read = AsyncMock()
        mock_response_success.json = AsyncMock(return_value={"status": "success"})

        # Create mock session with side effect
        mock_aiohttp_session = AsyncMock()
        mock_aiohttp_session.request = AsyncMock(side_effect=[
            mock_response_fail,
            mock_response_success
        ])

        command = RequestCommand(
            logger=logger,
            session_store=session_store,
            max_retries=1,
            backoff_factor=2.0,
            max_delay=3  # Cap the delay at 3 seconds
        )

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            response = await command.execute_request(
                session=session,
                method="GET",
                endpoint="/test"
            )
            assert response.status == 200
            assert mock_aiohttp_session.request.call_count == 2 