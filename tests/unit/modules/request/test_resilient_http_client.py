import asyncio
import pytest
import aiohttp
from unittest.mock import AsyncMock, patch, MagicMock
from src.modules.request.resilient_http_client import RequestParams, ResilientHttpClient, ResilientHttpClientConfig
from src.modules.request.circuit_breaker import CircuitBreaker
from src.modules.request.errors import (
    AuthenticationError, RetryExceededError, RetryableError,
    SSLVerificationError, UnknownError
)
from src.modules.session.session import Session
from src.modules.session.auth import AuthConfig
from aiohttp.client_exceptions import ConnectionKey

@pytest.fixture
def session_name():
    return "test_session"


@pytest.fixture
def base_url():
    return "http://api.example.com"


@pytest.fixture
def session(session_name, base_url):
    session = MagicMock(spec=Session)
    session.name = session_name
    session.base_url = base_url
    session.is_authenticated = MagicMock(return_value=True)
    session.get_headers = MagicMock(return_value={"Authorization": "Bearer test-token"})
    return session


@pytest.fixture
def auth_session(session):
    session.is_authenticated = MagicMock(return_value=False)
    session.authenticate = AsyncMock()
    session.refresh_auth = AsyncMock()
    return session


@pytest.fixture
def circuit_breaker():
    return CircuitBreaker(threshold=2, reset_timeout=1)


@pytest.fixture
def config():
    return ResilientHttpClientConfig(
        timeout=30,
        verify_ssl=True,
        max_retries=3,
        backoff_factor=0.5
    )


@pytest.fixture
def mock_aiohttp_session():
    """Fixture to create a properly mocked aiohttp session."""
    mock_session = AsyncMock()
    mock_session.request = AsyncMock()
    mock_session.close = AsyncMock()
    return mock_session


class TestResilientHttpClient:
    """Test cases for ResilientHttpClient class."""

    def test_init_with_custom_config(self, session):
        """Test initialization with custom configuration."""
        config = ResilientHttpClientConfig(
            timeout=60,
            verify_ssl=False,
            max_retries=5,
            backoff_factor=1.0
        )
        executor = ResilientHttpClient(
            session=session,
            config=config,
            logger=MagicMock()
        )
        assert executor.config.timeout == 60
        assert executor.config.verify_ssl is False
        assert executor.config.max_retries == 5
        assert executor.config.backoff_factor == 1.0

    @pytest.mark.asyncio
    async def test_successful_request(self, session, config, mock_aiohttp_session):
        """Test successful request execution."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock()
        mock_aiohttp_session.request.return_value = mock_response

        executor = ResilientHttpClient(
            session=session,
            config=config,
            logger=MagicMock()
        )

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            response = await executor.execute_request(
                RequestParams(
                    method="GET",
                    url="/test"
                )
            )
            assert response.status == 200
            mock_aiohttp_session.request.assert_called_once_with(
                method="GET",
                url="http://api.example.com/test",
                json=None,
                params=None,
                headers={"Authorization": "Bearer test-token"},
                ssl=True
            )

    @pytest.mark.asyncio
    async def test_request_with_custom_headers(self, session, config, mock_aiohttp_session):
        """Test request execution with custom headers."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock()
        mock_aiohttp_session.request.return_value = mock_response

        executor = ResilientHttpClient(
            session=session,
            config=config,
            logger=MagicMock()
        )

        custom_headers = {"X-Custom-Header": "test-value"}

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            response = await executor.execute_request(
                RequestParams(
                    method="GET",
                    url="/test",
                    headers=custom_headers
                )
            )
            assert response.status == 200
            mock_aiohttp_session.request.assert_called_once_with(
                method="GET",
                url="http://api.example.com/test",
                json=None,
                params=None,
                headers={
                    "Authorization": "Bearer test-token",
                    "X-Custom-Header": "test-value"
                },
                ssl=True
            )

    @pytest.mark.asyncio
    async def test_request_with_data(self, session, config, mock_aiohttp_session):
        """Test request execution with request body data."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock()
        mock_aiohttp_session.request.return_value = mock_response

        executor = ResilientHttpClient(
            session=session,
            config=config,
            logger=MagicMock()
        )

        request_data = {"key": "value"}

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            response = await executor.execute_request(
                RequestParams(
                    method="POST",
                    url="/test",
                    data=request_data
                )
            )
            assert response.status == 200
            mock_aiohttp_session.request.assert_called_once_with(
                method="POST",
                url="http://api.example.com/test",
                json=request_data,
                params=None,
                headers={"Authorization": "Bearer test-token"},
                ssl=True
            )

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_threshold(self, session, config, circuit_breaker, mock_aiohttp_session):
        """Test that circuit breaker opens after reaching failure threshold."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.read = AsyncMock()
        mock_aiohttp_session.request.return_value = mock_response

        executor = ResilientHttpClient(
            session=session,
            config=config,
            logger=MagicMock(),
            circuit_breaker=circuit_breaker
        )

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            # First request should fail and record failure
            with pytest.raises(RetryExceededError):
                await executor.execute_request(
                    RequestParams(
                        method="GET",
                        url="/test"
                    )
                )
            
            # Circuit breaker should be open after threshold is reached
            assert circuit_breaker.is_open()

    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_after_timeout(self, session, config, circuit_breaker, mock_aiohttp_session):
        """Test that circuit breaker resets after timeout period."""
        # First response fails
        mock_response_fail = AsyncMock()
        mock_response_fail.status = 500
        mock_response_fail.read = AsyncMock()

        # Second response succeeds
        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        mock_response_success.read = AsyncMock()

        mock_aiohttp_session.request.side_effect = [mock_response_fail, mock_response_success]

        executor = ResilientHttpClient(
            session=session,
            config=config,
            logger=MagicMock(),
            circuit_breaker=circuit_breaker
        )

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            # First request should fail and record failure
            with pytest.raises(RetryExceededError):
                await executor.execute_request(
                    RequestParams(
                        method="GET",
                        url="/test"
                    )
                )
            
            # Circuit breaker should be open
            assert circuit_breaker.is_open()
            
            # Wait for reset timeout
            await asyncio.sleep(1.1)  # Slightly longer than reset_timeout
            
            # Circuit breaker should be closed
            assert not circuit_breaker.is_open()

    @pytest.mark.asyncio
    async def test_ssl_verification_error(self, session, config, mock_aiohttp_session):
        """Test handling of SSL verification errors."""
        mock_aiohttp_session.request.side_effect = aiohttp.ClientSSLError(connection_key=MagicMock(), os_error=MagicMock())

        executor = ResilientHttpClient(
            session=session,
            config=config,
            logger=MagicMock()
        )

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            with pytest.raises(SSLVerificationError):
                await executor.execute_request(
                    RequestParams(
                        method="GET",
                        url="/test"
                    )
                )   

    @pytest.mark.asyncio
    async def test_connection_error_retry(self, session, config, mock_aiohttp_session):
        """Test retry behavior on connection errors."""
        # First attempt fails with connection error
        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        mock_response_success.read = AsyncMock()

        mock_aiohttp_session.request.side_effect = [
            aiohttp.ClientConnectorError(connection_key=MagicMock(), os_error=MagicMock()),
            mock_response_success
        ]

        executor = ResilientHttpClient(
            session=session,
            config=config,
            logger=MagicMock()
        )

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            response = await executor.execute_request(
                RequestParams(
                    method="GET",
                    url="/test"
                )
            )
            assert response.status == 200

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, session, config, mock_aiohttp_session):
        """Test behavior when max retries are exceeded."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.read = AsyncMock()
        mock_aiohttp_session.request.return_value = mock_response

        executor = ResilientHttpClient(
            session=session,
            config=config,
            logger=MagicMock()
        )

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            with pytest.raises(RetryExceededError):
                await executor.execute_request(
                    RequestParams(
                        method="GET",
                        url="/test"
                    )
                )

    @pytest.mark.asyncio
    async def test_session_cleanup(self, session, config, mock_aiohttp_session):
        """Test that session is properly cleaned up."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock()
        mock_aiohttp_session.request.return_value = mock_response

        executor = ResilientHttpClient(
            session=session,
            config=config,
            logger=MagicMock()
        )

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            await executor.execute_request(
                RequestParams(
                    method="GET",
                    url="/test"
                )
            )
            await executor.close()
            # Verify that the session cache was closed
            assert executor.session_cache.client_session is None

    @pytest.mark.asyncio
    async def test_invalid_url_error(self, session, config, mock_aiohttp_session):
        """Test handling of invalid URL errors."""
        mock_aiohttp_session.request.side_effect = aiohttp.InvalidURL("Invalid URL")

        executor = ResilientHttpClient(
            session=session,
            config=config,
            logger=MagicMock()
        )

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            with pytest.raises(UnknownError):
                await executor.execute_request(
                    RequestParams(
                        method="GET",
                        url="/test"
                    )
                )

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, auth_session, config, mock_aiohttp_session):
        """Test handling of authentication errors."""
        # First response with 401
        mock_response_401 = AsyncMock()
        mock_response_401.status = 401
        mock_response_401.read = AsyncMock()

        # Second response after refresh
        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.read = AsyncMock()

        mock_aiohttp_session.request.side_effect = [mock_response_401, mock_response_200]

        # Configure auth session to succeed on refresh
        auth_session.refresh_auth.return_value = True
        auth_session.is_authenticated.return_value = True

        executor = ResilientHttpClient(
            session=auth_session,
            config=config,
            logger=MagicMock()
        )

        with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
            response = await executor.execute_request(
                RequestParams(
                    method="GET",
                    url="/test"
                )
            )
            assert response.status == 200
            # Verify auth flow was called
            auth_session.refresh_auth.assert_called_once() 