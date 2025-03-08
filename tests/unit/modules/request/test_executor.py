import pytest
import aiohttp
from unittest.mock import AsyncMock, patch, MagicMock
from src.modules.request.executor import RequestExecutor
from src.modules.session.session import Session
from src.modules.session.auth import AuthConfig


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
def executor(session):
    return RequestExecutor(session=session)


@pytest.fixture
def auth_executor(auth_session):
    return RequestExecutor(session=auth_session)


class TestRequestExecutor:
    """Test cases for RequestExecutor class."""

    def test_init_with_custom_options(self, session):
        """Test initialization with custom options."""
        executor = RequestExecutor(
            session=session,
            timeout=60,
            verify_ssl=False,
            max_retries=5,
            backoff_factor=1.0
        )
        assert executor.timeout == 60
        assert executor.verify_ssl is False
        assert executor.max_retries == 5
        assert executor.backoff_factor == 1.0

    @pytest.mark.asyncio
    async def test_execute_request_success(self, executor):
        """Test successful request execution."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"message": "success"})
        mock_response.read = AsyncMock()

        mock_session = MagicMock()
        mock_session.request = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            response = await executor.execute_request(
                method="GET",
                endpoint="/test"
            )
            assert response.status == 200
            data = await response.json()
            assert data == {"message": "success"}

    @pytest.mark.asyncio
    async def test_execute_request_with_auth(self, auth_executor):
        """Test request execution with authentication."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"message": "success"})
        mock_response.read = AsyncMock()

        mock_session = MagicMock()
        mock_session.request = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            response = await auth_executor.execute_request(
                method="GET",
                endpoint="/test"
            )
            assert response.status == 200
            data = await response.json()
            assert data == {"message": "success"}

    @pytest.mark.asyncio
    async def test_execute_request_with_custom_headers(self, executor):
        """Test request execution with custom headers."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"message": "success"})
        mock_response.read = AsyncMock()

        mock_session = MagicMock()
        mock_session.request = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        custom_headers = {"X-Custom-Header": "test-value"}

        with patch("aiohttp.ClientSession", return_value=mock_session):
            response = await executor.execute_request(
                method="GET",
                endpoint="/test",
                headers=custom_headers
            )
            assert response.status == 200
            data = await response.json()
            assert data == {"message": "success"}

    @pytest.mark.asyncio
    async def test_execute_request_with_data(self, executor):
        """Test request execution with request body data."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"message": "success"})
        mock_response.read = AsyncMock()

        mock_session = MagicMock()
        mock_session.request = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        request_data = {"key": "value"}

        with patch("aiohttp.ClientSession", return_value=mock_session):
            response = await executor.execute_request(
                method="POST",
                endpoint="/test",
                data=request_data
            )
            assert response.status == 200
            data = await response.json()
            assert data == {"message": "success"}

    @pytest.mark.asyncio
    async def test_execute_request_auth_refresh(self, auth_executor):
        """Test request execution with authentication refresh."""
        # First response with 401
        mock_response_401 = MagicMock()
        mock_response_401.status = 401
        mock_response_401.json = AsyncMock(return_value={"error": "unauthorized"})
        mock_response_401.read = AsyncMock()

        # Second response after refresh
        mock_response_200 = MagicMock()
        mock_response_200.status = 200
        mock_response_200.json = AsyncMock(return_value={"message": "success"})
        mock_response_200.read = AsyncMock()

        mock_session = MagicMock()
        mock_session.request = AsyncMock(side_effect=[mock_response_401, mock_response_200])
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            response = await auth_executor.execute_request(
                method="GET",
                endpoint="/test"
            )
            assert response.status == 200
            data = await response.json()
            assert data == {"message": "success"}

    @pytest.mark.asyncio
    async def test_execute_request_retry_on_server_error(self, executor):
        """Test request retry on server error."""
        # First response with 500
        mock_response_500 = MagicMock()
        mock_response_500.status = 500
        mock_response_500.json = AsyncMock(return_value={"error": "server error"})
        mock_response_500.read = AsyncMock()

        # Second response success
        mock_response_200 = MagicMock()
        mock_response_200.status = 200
        mock_response_200.json = AsyncMock(return_value={"message": "success"})
        mock_response_200.read = AsyncMock()

        mock_session = MagicMock()
        mock_session.request = AsyncMock(side_effect=[mock_response_500, mock_response_200])
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            response = await executor.execute_request(
                method="GET",
                endpoint="/test"
            )
            assert response.status == 200
            data = await response.json()
            assert data == {"message": "success"}
            
    @pytest.mark.asyncio
    async def test_execute_request_url_construction(self, executor):
        """Test proper URL construction from base URL and endpoint."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"message": "success"})
        mock_response.read = AsyncMock()

        mock_session = MagicMock()
        mock_session.request = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            response = await executor.execute_request(
                method="GET",
                endpoint="/test"
            )
            assert response.status == 200
            mock_session.request.assert_called_once_with(
                method="GET",
                url="http://api.example.com/test",
                json=None,
                headers={"Authorization": "Bearer test-token"},
                ssl=True
            ) 