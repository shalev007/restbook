import pytest
import base64
from src.modules.session.auth.basic import BasicAuthenticator


class TestBasicAuthenticator:
    """Test cases for BasicAuthenticator class."""

    @pytest.fixture
    def username(self):
        """Username for testing."""
        return "test-user"

    @pytest.fixture
    def password(self):
        """Password for testing."""
        return "test-pass"

    @pytest.fixture
    def credentials(self, username, password):
        """Valid credentials for testing."""
        return {
            "username": username,
            "password": password
        }

    @pytest.fixture
    def expected_auth_header(self, username, password):
        """Expected Authorization header value."""
        auth_string = f"{username}:{password}"
        auth_bytes = auth_string.encode('utf-8')
        encoded = base64.b64encode(auth_bytes).decode('utf-8')
        return f"Basic {encoded}"

    def test_init_with_valid_credentials(self, credentials, username, password):
        """Test initialization with valid credentials."""
        auth = BasicAuthenticator(credentials)
        assert auth.username == username
        assert auth.password == password
        assert auth.is_authenticated is True

    def test_init_without_username(self, password):
        """Test initialization without username raises error."""
        with pytest.raises(ValueError, match="Basic authentication requires 'username' and 'password' in credentials"):
            BasicAuthenticator({"password": password})

    def test_init_without_password(self, username):
        """Test initialization without password raises error."""
        with pytest.raises(ValueError, match="Basic authentication requires 'username' and 'password' in credentials"):
            BasicAuthenticator({"username": username})

    @pytest.mark.asyncio
    async def test_authenticate(self, credentials):
        """Test authenticate method (should be no-op for basic auth)."""
        auth = BasicAuthenticator(credentials)
        await auth.authenticate()
        assert auth.is_authenticated is True

    @pytest.mark.asyncio
    async def test_refresh(self, credentials):
        """Test refresh method (should be no-op for basic auth)."""
        auth = BasicAuthenticator(credentials)
        await auth.refresh()
        assert auth.is_authenticated is True

    def test_get_headers(self, credentials, expected_auth_header):
        """Test getting authentication headers."""
        auth = BasicAuthenticator(credentials)
        headers = auth.get_headers()
        assert headers == {"Authorization": expected_auth_header}

    def test_create_auth_header(self, credentials, expected_auth_header):
        """Test creation of auth header string."""
        auth = BasicAuthenticator(credentials)
        assert auth._auth_header == expected_auth_header 