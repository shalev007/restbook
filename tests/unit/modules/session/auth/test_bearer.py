import pytest
from src.modules.session.auth.bearer import BearerAuthenticator


class TestBearerAuthenticator:
    """Test cases for BearerAuthenticator class."""

    @pytest.fixture
    def token(self):
        """Bearer token for testing."""
        return "test-token"

    @pytest.fixture
    def credentials(self, token):
        """Valid credentials for testing."""
        return {"token": token}

    def test_init_with_valid_credentials(self, credentials):
        """Test initialization with valid credentials."""
        auth = BearerAuthenticator(credentials)
        assert auth.token == credentials["token"]
        assert auth.is_authenticated is True

    def test_init_without_token(self):
        """Test initialization without token raises error."""
        with pytest.raises(ValueError, match="Bearer authentication requires 'token' in credentials"):
            BearerAuthenticator({})

    @pytest.mark.asyncio
    async def test_authenticate(self, credentials):
        """Test authenticate method (should be no-op for bearer)."""
        auth = BearerAuthenticator(credentials)
        await auth.authenticate()
        assert auth.is_authenticated is True

    @pytest.mark.asyncio
    async def test_refresh(self, credentials):
        """Test refresh method (should be no-op for bearer)."""
        auth = BearerAuthenticator(credentials)
        await auth.refresh()
        assert auth.is_authenticated is True

    def test_get_headers(self, credentials, token):
        """Test getting authentication headers."""
        auth = BearerAuthenticator(credentials)
        headers = auth.get_headers()
        assert headers == {"Authorization": f"Bearer {token}"} 