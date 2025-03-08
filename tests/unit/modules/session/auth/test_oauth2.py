import pytest
import aiohttp
from unittest.mock import AsyncMock, patch
from src.modules.session.auth.oauth2 import OAuth2Authenticator


class TestOAuth2Authenticator:
    """Test cases for OAuth2Authenticator class."""

    @pytest.fixture
    def client_id(self):
        """Client ID for testing."""
        return "test-client-id"

    @pytest.fixture
    def client_secret(self):
        """Client secret for testing."""
        return "test-client-secret"

    @pytest.fixture
    def token_url(self):
        """Token URL for testing."""
        return "https://api.example.com/oauth/token"

    @pytest.fixture
    def access_token(self):
        """Access token for testing."""
        return "test-access-token"

    @pytest.fixture
    def refresh_token(self):
        """Refresh token for testing."""
        return "test-refresh-token"

    @pytest.fixture
    def credentials(self, client_id, client_secret, token_url):
        """Valid credentials for testing."""
        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "token_url": token_url
        }

    @pytest.fixture
    def token_response(self, access_token, refresh_token):
        """Mock token response for testing."""
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 3600
        }

    def test_init_with_valid_credentials(self, credentials):
        """Test initialization with valid credentials."""
        auth = OAuth2Authenticator(credentials)
        assert auth.client_id == credentials["client_id"]
        assert auth.client_secret == credentials["client_secret"]
        assert auth.token_url == credentials["token_url"]
        assert auth.is_authenticated is False

    def test_init_missing_required_fields(self, credentials):
        """Test initialization with missing required fields raises error."""
        del credentials["client_id"]
        with pytest.raises(ValueError, match="OAuth2 authentication requires 'client_id' in credentials"):
            OAuth2Authenticator(credentials)
