import pytest
from src.modules.session.session import Session
from src.modules.session.auth import AuthConfig


class TestSession:
    """Test cases for Session class."""

    @pytest.fixture
    def base_url(self):
        """Base URL for testing."""
        return "https://api.example.com"

    @pytest.fixture
    def session_name(self):
        """Session name for testing."""
        return "test"

    @pytest.fixture
    def bearer_auth_config(self):
        """Bearer token auth config for testing."""
        return AuthConfig(
            type="bearer",
            credentials={"token": "test-token"}
        )

    @pytest.fixture
    def session_dict_with_auth(self, base_url):
        """Session dictionary with auth for testing."""
        return {
            "base_url": base_url,
            "auth": {
                "type": "bearer",
                "credentials": {"token": "test-token"}
            }
        }

    @pytest.fixture
    def session_dict_without_auth(self, base_url):
        """Session dictionary without auth for testing."""
        return {
            "base_url": base_url,
            "auth": None
        }

    def test_creation_without_auth(self, session_name, base_url):
        """Test creating a session without authentication."""
        session = Session(name=session_name, base_url=base_url)
        assert session.name == session_name
        assert session.base_url == base_url
        assert session.auth_config is None
        assert session.authenticator is None
        assert session.is_authenticated() is True  # No auth means always authenticated

    def test_creation_with_auth(self, session_name, base_url, bearer_auth_config):
        """Test creating a session with authentication config."""
        session = Session(
            name=session_name,
            base_url=base_url,
            auth_config=bearer_auth_config
        )
        assert session.name == session_name
        assert session.auth_config == bearer_auth_config
        assert session.authenticator is not None
        assert session.authenticator.credentials == {"token": "test-token"}

    def test_from_dict_with_auth(self, session_name, session_dict_with_auth):
        """Test creating a session from a dictionary with auth."""
        session = Session.from_dict(session_name, session_dict_with_auth)
        assert session.name == session_name
        assert session.base_url == session_dict_with_auth["base_url"]
        assert session.auth_config is not None
        assert session.auth_config.type == "bearer"
        assert session.auth_config.credentials == {"token": "test-token"}

    def test_from_dict_without_auth(self, session_name, session_dict_without_auth):
        """Test creating a session from a dictionary without auth."""
        session = Session.from_dict(session_name, session_dict_without_auth)
        assert session.name == session_name
        assert session.base_url == session_dict_without_auth["base_url"]
        assert session.auth_config is None

    def test_to_dict_with_auth(self, session_name, base_url, bearer_auth_config, session_dict_with_auth):
        """Test converting a session with auth to a dictionary."""
        session = Session(
            name=session_name,
            base_url=base_url,
            auth_config=bearer_auth_config
        )
        assert session.to_dict() == session_dict_with_auth

    def test_to_dict_without_auth(self, session_name, base_url, session_dict_without_auth):
        """Test converting a session without auth to a dictionary."""
        session = Session(name=session_name, base_url=base_url)
        assert session.to_dict() == session_dict_without_auth

    def test_get_headers_without_auth(self, session_name, base_url):
        """Test getting headers from a session without authentication."""
        session = Session(name=session_name, base_url=base_url)
        headers = session.get_headers()
        assert headers == {}

    def test_get_headers_with_auth(self, session_name, base_url, bearer_auth_config):
        """Test getting headers from a session with authentication."""
        session = Session(
            name=session_name,
            base_url=base_url,
            auth_config=bearer_auth_config
        )
        headers = session.get_headers()
        assert headers == {"Authorization": "Bearer test-token"}

    @pytest.mark.asyncio
    async def test_authenticate_without_auth(self, session_name, base_url):
        """Test authenticate method on session without auth."""
        session = Session(name=session_name, base_url=base_url)
        await session.authenticate()  # Should not raise any error
        assert session.is_authenticated() is True

    @pytest.mark.asyncio
    async def test_refresh_auth_without_auth(self, session_name, base_url):
        """Test refresh_auth method on session without auth."""
        session = Session(name=session_name, base_url=base_url)
        await session.refresh_auth()  # Should not raise any error
        assert session.is_authenticated() is True