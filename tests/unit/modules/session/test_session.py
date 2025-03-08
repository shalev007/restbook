import pytest
from src.modules.session.session import Session
from src.modules.session.auth import AuthConfig


def test_session_creation_without_auth():
    """Test creating a session without authentication."""
    session = Session(name="test", base_url="https://api.example.com")
    assert session.name == "test"
    assert session.base_url == "https://api.example.com"
    assert session.auth_config is None
    assert session.authenticator is None
    assert session.is_authenticated() is True  # No auth means always authenticated


def test_session_creation_with_auth():
    """Test creating a session with authentication config."""
    auth_config = AuthConfig(
        type="bearer",
        credentials={"token": "test-token"}
    )
    session = Session(name="test", base_url="https://api.example.com", auth_config=auth_config)
    assert session.name == "test"
    assert session.auth_config == auth_config
    assert session.authenticator is not None
    assert session.authenticator.credentials == {"token": "test-token"}


def test_session_from_dict():
    """Test creating a session from a dictionary."""
    data = {
        "base_url": "https://api.example.com",
        "auth": {
            "type": "bearer",
            "credentials": {"token": "test-token"}
        }
    }
    session = Session.from_dict("test", data)
    assert session.name == "test"
    assert session.base_url == "https://api.example.com"
    assert session.auth_config is not None
    assert session.auth_config.type == "bearer"
    assert session.auth_config.credentials == {"token": "test-token"}


def test_session_to_dict():
    """Test converting a session to a dictionary."""
    auth_config = AuthConfig(
        type="bearer",
        credentials={"token": "test-token"}
    )
    session = Session(name="test", base_url="https://api.example.com", auth_config=auth_config)
    data = session.to_dict()
    assert data == {
        "base_url": "https://api.example.com",
        "auth": {
            "type": "bearer",
            "credentials": {"token": "test-token"}
        }
    }


def test_session_to_dict_without_auth():
    """Test converting a session without auth to a dictionary."""
    session = Session(name="test", base_url="https://api.example.com")
    data = session.to_dict()
    assert data == {
        "base_url": "https://api.example.com",
        "auth": None
    }


def test_session_get_headers_without_auth():
    """Test getting headers from a session without authentication."""
    session = Session(name="test", base_url="https://api.example.com")
    headers = session.get_headers()
    assert headers == {} 

def test_session_get_headers_with_auth():
    """Test getting headers from a session with authentication."""
    auth_config = AuthConfig(
        type="bearer",
        credentials={"token": "test-token"}
    )
    session = Session(name="test", base_url="https://api.example.com", auth_config=auth_config)
    headers = session.get_headers()
    assert headers == {"Authorization": "Bearer test-token"}

def test_session_is_authenticated():
    """Test checking if a session is authenticated."""
    session = Session(name="test", base_url="https://api.example.com")
    assert session.is_authenticated() is True  # No auth means always authenticated